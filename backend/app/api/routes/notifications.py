from fastapi import APIRouter, HTTPException
from app.core.config import settings
from supabase import create_client

router = APIRouter(prefix="/notifications", tags=["notifications"])

def db():
    if not settings.supabase_service_role_key:
        raise HTTPException(status_code=500, detail="Server service key is not configured.")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

@router.get("/user/{user_id}")
def user_notifications(user_id: str):
    client = db()
    result = client.table("notifications").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(50).execute()
    return {"items": result.data or [], "unread": sum(1 for item in (result.data or []) if not item.get("is_read"))}

@router.patch("/{notification_id}/read")
def mark_read(notification_id: str, user_id: str):
    client = db()
    result = client.table("notifications").update({"is_read": True}).eq("id", notification_id).eq("user_id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return {"notification": result.data[0]}
