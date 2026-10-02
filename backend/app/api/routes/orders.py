from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..deps import get_supabase

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

@router.post("")
def create_order(payload: CreateOrderIn):
    if payload.payment_method != "cod":
        raise HTTPException(status_code=400, detail="Only COD is enabled in this milestone.")
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty.")
    client = get_supabase()
    subtotal = sum(i.unit_price * i.quantity for i in payload.items)
    order = client.table("orders").insert({
        "user_id": payload.user_id,
        "status": "ordered",
        "payment_method": "cod",
        "payment_status": "pending",
        "subtotal": subtotal,
        "discount": 0,
        "shipping_fee": 0,
        "total": subtotal,
        "shipping_address": payload.shipping_address,
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
