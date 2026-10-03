import os

class Settings:
    database_url = os.getenv("DATABASE_URL", "")
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    cors_origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]\n    razorpay_key_id = os.getenv("RAZORPAY_KEY_ID", "")\n    razorpay_key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")

settings = Settings()
