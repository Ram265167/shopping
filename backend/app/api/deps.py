from fastapi import Header, HTTPException
from functools import lru_cache
from supabase import Client, create_client
from app.core.config import settings

@lru_cache
def get_supabase() -> Client:
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise RuntimeError("Supabase configuration is missing.")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def require_user(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign-in required.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Sign-in required.")
    try:
        client = get_supabase()
        result = client.auth.get_user(token)
        if not result.user:
            raise HTTPException(status_code=401, detail="Invalid session.")
        return str(result.user.id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
