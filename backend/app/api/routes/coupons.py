from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from supabase import create_client
from app.core.config import settings

router = APIRouter(prefix="/coupons", tags=["coupons"])

def db():
    if not settings.supabase_service_role_key:
        raise HTTPException(status_code=500, detail="Server service key is not configured.")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

class CouponCheck(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    subtotal: float = Field(ge=0)

def calculate(coupon: dict, subtotal: float):
    if not coupon.get("is_active"): raise ValueError("This coupon is inactive.")
    now=datetime.now(timezone.utc)
    starts=coupon.get("starts_at"); expires=coupon.get("expires_at")
    if starts and now < datetime.fromisoformat(starts.replace("Z","+00:00")): raise ValueError("This coupon is not active yet.")
    if expires and now > datetime.fromisoformat(expires.replace("Z","+00:00")): raise ValueError("This coupon has expired.")
    if coupon.get("usage_limit") is not None and int(coupon.get("used_count") or 0) >= int(coupon["usage_limit"]): raise ValueError("This coupon has reached its usage limit.")
    minimum=float(coupon.get("minimum_order_value") or 0)
    if subtotal < minimum: raise ValueError(f"Minimum order value is ₹{minimum:,.0f}.")
    value=float(coupon["discount_value"])
    discount=subtotal*value/100 if coupon["discount_type"]=="percent" else value
    if coupon.get("max_discount") is not None: discount=min(discount,float(coupon["max_discount"]))
    discount=min(discount,subtotal)
    return round(discount,2)

@router.post("/validate")
def validate(payload: CouponCheck):
    client=db()
    result=client.table("coupons").select("*").eq("code",payload.code.strip().upper()).limit(1).execute()
    if not result.data: raise HTTPException(status_code=404, detail="Coupon not found.")
    try: discount=calculate(result.data[0],payload.subtotal)
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc))
    return {"valid":True,"code":result.data[0]["code"],"discount":discount,"total":round(payload.subtotal-discount,2),"description":result.data[0].get("description")}

