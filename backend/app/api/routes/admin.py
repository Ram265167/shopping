from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from supabase import create_client
from app.core.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])

def admin_client(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Admin sign-in required.")
    token = authorization.removeprefix("Bearer ").strip()
    auth_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    user = auth_client.auth.get_user(token)
    if not user or not user.user:
        raise HTTPException(status_code=401, detail="Invalid session.")
    profile = auth_client.table("profiles").select("role").eq("id", user.user.id).limit(1).execute()
    if not profile.data or profile.data[0]["role"] not in ("admin", "staff"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    if not settings.supabase_service_role_key:
        raise HTTPException(status_code=500, detail="SUPABASE_SERVICE_ROLE_KEY is not configured on the server.")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

class ProductUpdate(BaseModel):
    name: str | None = None
    price: float | None = Field(default=None, ge=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

@router.get("/stats")
def stats(authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    products = client.table("products").select("id", count="exact").execute()
    orders = client.table("orders").select("id", count="exact").execute()
    customers = client.table("profiles").select("id", count="exact").eq("role", "customer").execute()
    revenue = client.table("orders").select("total").in_("status", ["ordered","packed","shipped","out_for_delivery","delivered"]).execute()
    total = sum(float(row.get("total") or 0) for row in (revenue.data or []))
    return {"products": products.count or 0, "orders": orders.count or 0, "customers": customers.count or 0, "revenue": total}

@router.get("/products")
def products(authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("products").select("*, categories(name), brands(name)").order("created_at", desc=True).execute()
    return {"items": result.data or []}

@router.patch("/products/{product_id}")
def update_product(product_id: str, payload: ProductUpdate, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    values = payload.model_dump(exclude_none=True)
    if not values:
        raise HTTPException(status_code=400, detail="No changes supplied.")
    result = client.table("products").update(values).eq("id", product_id).execute()
    return {"product": result.data[0] if result.data else None}

@router.get("/orders")
def admin_orders(authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("orders").select("*").order("created_at", desc=True).limit(100).execute()
    return {"items": result.data or []}

@router.patch("/orders/{order_id}/status")
def update_order_status(order_id: str, status: str, authorization: str | None = Header(default=None)):
    allowed = {"ordered","packed","shipped","out_for_delivery","delivered","cancelled","return_requested","returned","refunded"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid order status.")
    client = admin_client(authorization)
    result = client.table("orders").update({"status": status}).eq("id", order_id).execute()
    client.table("order_status_history").insert({"order_id": order_id, "status": status, "note": "Updated by admin"}).execute()
    return {"order": result.data[0] if result.data else None}
