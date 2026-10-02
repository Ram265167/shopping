from fastapi import APIRouter
from ..deps import get_supabase

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("")
def list_categories():
    result = get_supabase().table("categories").select("*").eq("is_active", True).order("sort_order").execute()
    return {"items": result.data or []}
