from functools import lru_cache
from supabase import Client, create_client
from app.core.config import settings

@lru_cache
def get_supabase() -> Client:
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise RuntimeError("Supabase configuration is missing.")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
