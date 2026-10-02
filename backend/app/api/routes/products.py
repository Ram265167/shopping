from fastapi import APIRouter, Query
from ..deps import get_supabase

router = APIRouter(prefix="/products", tags=["products"])

@router.get("")
def list_products(
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    featured: bool = False,
    limit: int = Query(default=24, ge=1, le=100),
):
    client = get_supabase()
    query = client.table("products").select(
        "*, categories(name,slug), brands(name,slug), product_images(image_url,alt_text,sort_order)"
    ).eq("is_active", True)
    if category:
        row = client.table("categories").select("id").eq("slug", category).limit(1).execute()
        if row.data:
            query = query.eq("category_id", row.data[0]["id"])
    if search:
        term = search.replace(",", " ").strip()
        query = query.or_(f"name.ilike.%{term}%,description.ilike.%{term}%,sku.ilike.%{term}%")
    if featured:
        query = query.eq("is_featured", True)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return {"items": result.data or [], "count": len(result.data or [])}
