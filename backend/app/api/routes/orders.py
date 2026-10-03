from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from ..deps import get_supabase, require_user
from app.core.config import settings
from supabase import create_client
from datetime import datetime, timezone

router = APIRouter(prefix="/orders", tags=["orders"])

class OrderItemIn(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)
    product_name: str
    unit_price: float = Field(ge=0)

class CreateOrderIn(BaseModel):
    user_id: str
    shipping_address: dict
    items: list[OrderItemIn]
    payment_method: str = "cod"
    coupon_code: str | None = None

@router.post("")
def create_order(payload: CreateOrderIn, authorization: str | None = Header(default=None)):
    current_user = require_user(authorization)
    if payload.user_id != current_user:
        raise HTTPException(status_code=403, detail="You can only create orders for your account.")
    if payload.payment_method != "cod":
        raise HTTPException(status_code=400, detail="Only COD is enabled in this milestone.")
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty.")

    client = get_supabase()
    product_ids = list(dict.fromkeys(i.product_id for i in payload.items))
    products_result = client.table("products").select("id,name,price,stock_quantity,is_active").in_("id", product_ids).execute()
    products = {str(p["id"]): p for p in (products_result.data or [])}
    if len(products) != len(product_ids):
        raise HTTPException(status_code=400, detail="One or more products are no longer available.")

    verified_items = []
    subtotal = 0.0
    for item in payload.items:
        product = products.get(str(item.product_id))
        if not product or not product.get("is_active"):
            raise HTTPException(status_code=400, detail=f"{item.product_name} is no longer available.")
        stock = int(product.get("stock_quantity") or 0)
        if item.quantity > stock:
            raise HTTPException(status_code=400, detail=f"Only {stock} unit(s) of {product['name']} are available.")
        price = float(product["price"])
        subtotal += price * item.quantity
        verified_items.append({
            "product_id": item.product_id,
            "product_name": product["name"],
            "quantity": item.quantity,
            "unit_price": price,
            "total_price": price * item.quantity,
        })

    discount = 0.0
    coupon = None
    if payload.coupon_code:
        if not settings.supabase_service_role_key:
            raise HTTPException(status_code=500, detail="Coupon service is not configured.")
        admin = create_client(settings.supabase_url, settings.supabase_service_role_key)
        found = admin.table("coupons").select("*").eq("code", payload.coupon_code.strip().upper()).limit(1).execute()
        if not found.data:
            raise HTTPException(status_code=400, detail="Coupon not found.")
        coupon = found.data[0]
        now = datetime.now(timezone.utc)
        if not coupon.get("is_active"):
            raise HTTPException(status_code=400, detail="Coupon is inactive.")
        if coupon.get("starts_at") and now < datetime.fromisoformat(coupon["starts_at"].replace("Z","+00:00")):
            raise HTTPException(status_code=400, detail="Coupon is not active yet.")
        if coupon.get("expires_at") and now > datetime.fromisoformat(coupon["expires_at"].replace("Z","+00:00")):
            raise HTTPException(status_code=400, detail="Coupon has expired.")
        if coupon.get("usage_limit") is not None and int(coupon.get("used_count") or 0) >= int(coupon["usage_limit"]):
            raise HTTPException(status_code=400, detail="Coupon usage limit reached.")
        if subtotal < float(coupon.get("minimum_order_value") or 0):
            raise HTTPException(status_code=400, detail="Minimum order value not reached.")
        discount = subtotal * float(coupon["discount_value"]) / 100 if coupon["discount_type"] == "percent" else float(coupon["discount_value"])
        if coupon.get("max_discount") is not None:
            discount = min(discount, float(coupon["max_discount"]))
        discount = min(discount, subtotal)

    total = max(0, subtotal - discount)
    order = client.table("orders").insert({
        "user_id": payload.user_id,
        "status": "ordered",
        "payment_method": "cod",
        "payment_status": "pending",
        "subtotal": subtotal,
        "discount": discount,
        "shipping_fee": 0,
        "total": total,
        "shipping_address": payload.shipping_address,
        "coupon_code": coupon["code"] if coupon else None,
    }).execute()
    if not order.data:
        raise HTTPException(status_code=500, detail="Unable to create order.")

    order_id = order.data[0]["id"]
    client.table("order_items").insert([
        {"order_id": order_id, **item} for item in verified_items
    ]).execute()
    client.table("order_status_history").insert({"order_id": order_id, "status": "ordered", "note": "Order placed"}).execute()

    if settings.supabase_service_role_key:
        notify = create_client(settings.supabase_url, settings.supabase_service_role_key)
        notify.table("notifications").insert({
            "user_id": payload.user_id,
            "title": "Order placed",
            "message": f"Your Seetharam order #{str(order_id)[:8]} has been placed.",
            "type": "order",
            "order_id": order_id,
        }).execute()

    if coupon:
        client.table("coupons").update({"used_count": int(coupon.get("used_count") or 0) + 1}).eq("id", coupon["id"]).execute()

    return {"order": order.data[0]}

@router.get("/user/{user_id}")
def user_orders(user_id: str, authorization: str | None = Header(default=None)):
    current_user = require_user(authorization)
    if user_id != current_user: raise HTTPException(status_code=403, detail="You can only view your own orders.")
    client = get_supabase()
    result = client.table("orders").select("*, order_items(*)").eq("user_id", user_id).order("created_at", desc=True).execute()
    return {"items": result.data or []}

@router.get("/{order_id}/tracking")
def order_tracking(order_id: str, user_id: str, authorization: str | None = Header(default=None)):
    current_user = require_user(authorization)
    if user_id != current_user: raise HTTPException(status_code=403, detail="You can only track your own orders.")
    client = get_supabase()
    order = client.table("orders").select("id,status,created_at,shipping_address,total,discount,coupon_code").eq("id",order_id).eq("user_id",user_id).limit(1).execute()
    if not order.data: raise HTTPException(status_code=404, detail="Order not found.")
    history = client.table("order_status_history").select("*").eq("order_id",order_id).order("created_at").execute()
    return {"order": order.data[0], "history": history.data or []}


@router.post("/{order_id}/cancel")
def cancel_order(order_id: str, user_id: str, authorization: str | None = Header(default=None)):
    current_user = require_user(authorization)
    if user_id != current_user: raise HTTPException(status_code=403, detail="You can only cancel your own orders.")
    client = get_supabase()
    found = client.table("orders").select("id,status,user_id").eq("id", order_id).eq("user_id", user_id).limit(1).execute()
    if not found.data: raise HTTPException(status_code=404, detail="Order not found.")
    if found.data[0]["status"] not in ("ordered", "packed"): raise HTTPException(status_code=400, detail="This order can no longer be cancelled.")
    result = client.table("orders").update({"status": "cancelled"}).eq("id", order_id).eq("user_id", user_id).execute()
    client.table("order_status_history").insert({"order_id": order_id, "status": "cancelled", "note": "Cancellation requested by customer"}).execute()
    if settings.supabase_service_role_key:
        notify = create_client(settings.supabase_url, settings.supabase_service_role_key)
        notify.table("notifications").insert({"user_id": user_id, "title": "Order cancelled", "message": f"Your Seetharam order #{str(order_id)[:8]} was cancelled.", "type": "order", "order_id": order_id}).execute()
    return {"order": result.data[0] if result.data else None}

@router.post("/{order_id}/return-request")
def return_request(order_id: str, user_id: str, authorization: str | None = Header(default=None)):
    current_user = require_user(authorization)
    if user_id != current_user: raise HTTPException(status_code=403, detail="You can only request returns for your own orders.")
    client = get_supabase()
    found = client.table("orders").select("id,status,user_id").eq("id", order_id).eq("user_id", user_id).limit(1).execute()
    if not found.data: raise HTTPException(status_code=404, detail="Order not found.")
    if found.data[0]["status"] != "delivered": raise HTTPException(status_code=400, detail="Returns can be requested only after delivery.")
    result = client.table("orders").update({"status": "return_requested"}).eq("id", order_id).eq("user_id", user_id).execute()
    client.table("order_status_history").insert({"order_id": order_id, "status": "return_requested", "note": "Return requested by customer"}).execute()
    if settings.supabase_service_role_key:
        notify = create_client(settings.supabase_url, settings.supabase_service_role_key)
        notify.table("notifications").insert({"user_id": user_id, "title": "Return requested", "message": f"Your return request for order #{str(order_id)[:8]} was submitted.", "type": "return", "order_id": order_id}).execute()
    return {"order": result.data[0] if result.data else None}
