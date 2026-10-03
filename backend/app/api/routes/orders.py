from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..deps import get_supabase
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
def create_order(payload: CreateOrderIn):
    if payload.payment_method != "cod":
        raise HTTPException(status_code=400, detail="Only COD is enabled in this milestone.")
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty.")
    client = get_supabase()
    subtotal = sum(i.unit_price * i.quantity for i in payload.items)
    discount = 0.0
    coupon = None
    if payload.coupon_code:
        admin = create_client(settings.supabase_url, settings.supabase_service_role_key)
        found = admin.table("coupons").select("*").eq("code", payload.coupon_code.strip().upper()).limit(1).execute()
        if not found.data: raise HTTPException(status_code=400, detail="Coupon not found.")
        coupon = found.data[0]
        now = datetime.now(timezone.utc)
        if not coupon.get("is_active"): raise HTTPException(status_code=400, detail="Coupon is inactive.")
        if coupon.get("expires_at") and now > datetime.fromisoformat(coupon["expires_at"].replace("Z","+00:00")): raise HTTPException(status_code=400, detail="Coupon has expired.")
        if coupon.get("usage_limit") is not None and int(coupon.get("used_count") or 0) >= int(coupon["usage_limit"]): raise HTTPException(status_code=400, detail="Coupon usage limit reached.")
        if subtotal < float(coupon.get("minimum_order_value") or 0): raise HTTPException(status_code=400, detail="Minimum order value not reached.")
        discount = subtotal * float(coupon["discount_value"]) / 100 if coupon["discount_type"] == "percent" else float(coupon["discount_value"])
        if coupon.get("max_discount") is not None: discount = min(discount, float(coupon["max_discount"]))
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
    rows = [{"order_id": order_id, "product_id": i.product_id, "product_name": i.product_name,
             "quantity": i.quantity, "unit_price": i.unit_price, "total_price": i.unit_price*i.quantity} for i in payload.items]
    client.table("order_items").insert(rows).execute()
    client.table("order_status_history").insert({"order_id": order_id, "status": "ordered", "note": "Order placed"}).execute()
    return {"order": order.data[0]}

@router.get("/user/{user_id}")
def user_orders(user_id: str):
    client = get_supabase()
    result = client.table("orders").select("*, order_items(*)").eq("user_id", user_id).order("created_at", desc=True).execute()
    return {"items": result.data or []}
