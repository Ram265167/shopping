import hashlib
import hmac
import json

import razorpay
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from app.core.config import settings
from app.api.deps import get_admin_supabase, require_user

router = APIRouter(prefix="/payments", tags=["payments"])

class PaymentOrderIn(BaseModel):
    user_id: str
    shipping_address: dict
    items: list[dict]
    coupon_code: str | None = None

class VerifyPaymentIn(BaseModel):
    user_id: str
    order_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

def payment_client():
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(status_code=503, detail="Online payments are not configured on the server.")
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))

@router.post("/create-order")
def create_payment_order(payload: PaymentOrderIn, authorization: str | None = Header(default=None)):
    current_user = require_user(authorization)
    if payload.user_id != current_user:
        raise HTTPException(status_code=403, detail="You can only pay for your own order.")
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty.")

    client = get_admin_supabase()
    try:
        result = client.rpc("create_online_order", {
            "p_user_id": current_user,
            "p_shipping_address": payload.shipping_address,
            "p_items": payload.items,
            "p_coupon_code": payload.coupon_code,
        }).execute()
    except Exception as exc:
        message = str(exc)
        if any(x in message for x in ("available", "Coupon", "Minimum order", "Cart is empty", "Product is no longer")):
            raise HTTPException(status_code=400, detail=message)
        raise HTTPException(status_code=500, detail="Unable to prepare online order.")

    data = result.data
    if isinstance(data, list):
        data = data[0] if data else None
    if not data:
        raise HTTPException(status_code=500, detail="Unable to prepare online order.")

    try:
        rorder = payment_client().order.create({
            "amount": int(round(float(data["total"]) * 100)),
            "currency": "INR",
            "receipt": str(data["order_id"])[:40],
            "notes": {"seetharam_order_id": str(data["order_id"]), "user_id": current_user},
        })
    except Exception:
        client.table("orders").update({
            "status": "cancelled", "payment_status": "failed"
        }).eq("id", data["order_id"]).eq("user_id", current_user).execute()
        raise HTTPException(status_code=502, detail="Unable to create payment gateway order.")

    client.table("orders").update({
        "payment_status": "pending",
        "payment_provider_order_id": rorder["id"],
    }).eq("id", data["order_id"]).eq("user_id", current_user).execute()

    return {
        "order_id": data["order_id"],
        "amount": int(round(float(data["total"]) * 100)),
        "currency": "INR",
        "razorpay_order_id": rorder["id"],
        "razorpay_key_id": settings.razorpay_key_id,
    }

@router.post("/verify")
def verify_payment(payload: VerifyPaymentIn, authorization: str | None = Header(default=None)):
    current_user = require_user(authorization)
    if payload.user_id != current_user:
        raise HTTPException(status_code=403, detail="You can only verify your own payment.")
    if not settings.razorpay_key_secret:
        raise HTTPException(status_code=503, detail="Online payments are not configured on the server.")

    client = get_admin_supabase()
    existing = client.table("orders").select(
        "id,total,payment_status,user_id,payment_provider_order_id"
    ).eq("id", payload.order_id).eq("user_id", current_user).maybe_single().execute()
    order = existing.data
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    if order.get("payment_provider_order_id") != payload.razorpay_order_id:
        raise HTTPException(status_code=400, detail="Payment gateway order does not match this order.")

    body = f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode()
    expected = hmac.new(settings.razorpay_key_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, payload.razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature.")

    if order.get("payment_status") == "paid":
        return {"ok": True, "order_id": payload.order_id, "payment_status": "paid"}

    updated = client.table("orders").update({
        "payment_status": "paid",
        "payment_provider_payment_id": payload.razorpay_payment_id,
    }).eq("id", payload.order_id).eq("user_id", current_user).eq("payment_status", "pending").execute()

    if updated.data:
        client.table("order_status_history").insert({
            "order_id": payload.order_id,
            "status": "ordered",
            "note": "Online payment verified successfully.",
        }).execute()
        client.table("notifications").insert({
            "user_id": current_user,
            "title": "Payment successful",
            "message": f"Payment received for order #{payload.order_id[:8]}.",
            "type": "order",
            "order_id": payload.order_id,
        }).execute()

    return {"ok": True, "order_id": payload.order_id, "payment_status": "paid"}

@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
):
    if not settings.razorpay_webhook_secret:
        raise HTTPException(status_code=503, detail="Payment webhook is not configured.")

    raw = await request.body()
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing webhook signature.")

    expected = hmac.new(settings.razorpay_webhook_secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    event = json.loads(raw.decode("utf-8"))
    if event.get("event") in {"payment.captured", "order.paid"}:
        payload = event.get("payload", {})
        payment_entity = payload.get("payment", {}).get("entity", {})
        order_entity = payload.get("order", {}).get("entity", {})
        provider_order_id = payment_entity.get("order_id") or order_entity.get("id")
        provider_payment_id = payment_entity.get("id")

        if provider_order_id:
            client = get_admin_supabase()
            rows = client.table("orders").select(
                "id,user_id,payment_status"
            ).eq("payment_provider_order_id", provider_order_id).limit(1).execute()

            if rows.data:
                order = rows.data[0]
                if order.get("payment_status") != "paid":
                    client.table("orders").update({
                        "payment_status": "paid",
                        "payment_provider_payment_id": provider_payment_id,
                    }).eq("id", order["id"]).execute()
                    client.table("notifications").insert({
                        "user_id": order["user_id"],
                        "title": "Payment confirmed",
                        "message": f"Payment confirmed for order #{str(order['id'])[:8]}.",
                        "type": "order",
                        "order_id": order["id"],
                    }).execute()

    return {"received": True}
