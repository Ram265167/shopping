from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from ..deps import get_admin_supabase, get_supabase, require_user

router = APIRouter(prefix="/orders", tags=["orders"])

class OrderItemIn(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)

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

    client = get_admin_supabase()
    try:
        result = client.rpc(
            "create_cod_order",
            {
                "p_user_id": current_user,
                "p_shipping_address": payload.shipping_address,
                "p_items": [item.model_dump() for item in payload.items],
                "p_coupon_code": payload.coupon_code,
            },
        ).execute()
    except Exception as exc:
        message = str(exc)
        if "Only " in message and "available" in message:
            raise HTTPException(status_code=400, detail=message)
        if "Coupon" in message or "Minimum order value" in message:
            raise HTTPException(status_code=400, detail=message)
        if "Cart is empty" in message or "Invalid cart item" in message:
            raise HTTPException(status_code=400, detail=message)
        if "Product is no longer available" in message:
            raise HTTPException(status_code=400, detail=message)
        raise HTTPException(status_code=500, detail="Unable to create order.")

    if not result.data:
        raise HTTPException(status_code=500, detail="Unable to create order.")
    return result.data

@router.get("/user/{user_id}")
def user_orders(user_id: str, authorization: str | None = Header(default=None)):
    current_user = require_user(authorization)
    if user_id != current_user:
        raise HTTPException(status_code=403, detail="You can only view your own orders.")
    client = get_supabase()
    result = client.table("orders").select("*, order_items(*)").eq("user_id", user_id).order("created_at", desc=True).execute()
    return {"items": result.data or []}

@router.get("/{order_id}/tracking")
def order_tracking(order_id: str, user_id: str, authorization: str | None = Header(default=None)):
    current_user = require_user(authorization)
    if user_id != current_user:
        raise HTTPException(status_code=403, detail="You can only track your own orders.")
    client = get_supabase()
    order = client.table("orders").select("id,status,created_at,shipping_address,total,discount,coupon_code").eq("id", order_id).eq("user_id", user_id).limit(1).execute()
    if not order.data:
        raise HTTPException(status_code=404, detail="Order not found.")
    history = client.table("order_status_history").select("*").eq("order_id", order_id).order("created_at").execute()
    return {"order": order.data[0], "history": history.data or []}

@router.post("/{order_id}/cancel")
def cancel_order(order_id: str, user_id: str, authorization: str | None = Header(default=None)):
    current_user = require_user(authorization)
    if user_id != current_user:
        raise HTTPException(status_code=403, detail="You can only cancel your own orders.")
    client = get_supabase()
    found = client.table("orders").select("id,status,user_id").eq("id", order_id).eq("user_id", user_id).limit(1).execute()
    if not found.data:
        raise HTTPException(status_code=404, detail="Order not found.")
    if found.data[0]["status"] not in ("ordered", "packed"):
        raise HTTPException(status_code=400, detail="This order can no longer be cancelled.")
    result = client.table("orders").update({"status": "cancelled"}).eq("id", order_id).eq("user_id", user_id).execute()
    client.table("order_status_history").insert({"order_id": order_id, "status": "cancelled", "note": "Cancellation requested by customer"}).execute()
    return {"order": result.data[0] if result.data else None}

@router.post("/{order_id}/return-request")
def return_request(order_id: str, user_id: str, authorization: str | None = Header(default=None)):
    current_user = require_user(authorization)
    if user_id != current_user:
        raise HTTPException(status_code=403, detail="You can only request returns for your own orders.")
    client = get_supabase()
    found = client.table("orders").select("id,status,user_id").eq("id", order_id).eq("user_id", user_id).limit(1).execute()
    if not found.data:
        raise HTTPException(status_code=404, detail="Order not found.")
    if found.data[0]["status"] != "delivered":
        raise HTTPException(status_code=400, detail="Returns can be requested only after delivery.")
    result = client.table("orders").update({"status": "return_requested"}).eq("id", order_id).eq("user_id", user_id).execute()
    client.table("order_status_history").insert({"order_id": order_id, "status": "return_requested", "note": "Return requested by customer"}).execute()
    return {"order": result.data[0] if result.data else None}
