from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from supabase import create_client
from app.core.config import settings

router = APIRouter(prefix="/reviews", tags=["reviews"])

class ReviewCreate(BaseModel):
    product_id: str
    order_id: str
    rating: int = Field(ge=1, le=5)
    title: str | None = None
    body: str = Field(min_length=3, max_length=3000)

def user_from_token(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign-in required.")
    token = authorization.removeprefix("Bearer ").strip()
    auth_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    result = auth_client.auth.get_user(token)
    if not result or not result.user:
        raise HTTPException(status_code=401, detail="Invalid session.")
    if not settings.supabase_service_role_key:
        raise HTTPException(status_code=500, detail="Server service key is not configured.")
    return result.user, create_client(settings.supabase_url, settings.supabase_service_role_key)

@router.get("/product/{product_id}")
def product_reviews(product_id: str):
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    result = client.table("reviews").select("id,rating,title,body,is_verified_buyer,helpful_count,created_at,profiles(full_name)").eq("product_id", product_id).eq("is_approved", True).order("created_at", desc=True).execute()
    return {"items": result.data or []}

@router.post("")
def create_review(payload: ReviewCreate, authorization: str | None = Header(default=None)):
    user, client = user_from_token(authorization)
    order = client.table("orders").select("id,status,user_id").eq("id", payload.order_id).eq("user_id", user.id).limit(1).execute()
    if not order.data or order.data[0]["status"] != "delivered":
        raise HTTPException(status_code=400, detail="You can review a product after its order is delivered.")
    item = client.table("order_items").select("id").eq("order_id", payload.order_id).eq("product_id", payload.product_id).limit(1).execute()
    if not item.data:
        raise HTTPException(status_code=400, detail="This product is not part of that order.")
    existing = client.table("reviews").select("id").eq("product_id", payload.product_id).eq("user_id", user.id).eq("order_id", payload.order_id).limit(1).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="You have already reviewed this purchase.")
    result = client.table("reviews").insert({**payload.model_dump(), "user_id": user.id, "is_verified_buyer": True, "is_approved": True}).execute()
    rows = client.table("reviews").select("rating").eq("product_id", payload.product_id).eq("is_approved", True).execute().data or []
    count = len(rows)
    average = round(sum(float(x["rating"]) for x in rows) / count, 1) if count else 0
    client.table("products").update({"rating": average, "review_count": count}).eq("id", payload.product_id).execute()
    return {"review": result.data[0] if result.data else None}

@router.post("/{review_id}/helpful")
def helpful(review_id: str):
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    review = client.table("reviews").select("helpful_count").eq("id", review_id).limit(1).execute()
    if not review.data:
        raise HTTPException(status_code=404, detail="Review not found.")
    count = int(review.data[0].get("helpful_count") or 0) + 1
    client.table("reviews").update({"helpful_count": count}).eq("id", review_id).execute()
    return {"helpful_count": count}
