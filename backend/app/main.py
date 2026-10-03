from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes.products import router as products_router
from app.api.routes.categories import router as categories_router
from app.api.routes.orders import router as orders_router
from app.api.routes.admin import router as admin_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.coupons import router as coupons_router
from app.api.routes.notifications import router as notifications_router\nfrom app.api.routes.payments import router as payments_router
from supabase import create_client

app = FastAPI(title="Seetharam API", version="0.1.0")

def ensure_storage_buckets():
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    for bucket in ("product-images", "review-images"):
        try:
            client.storage.create_bucket(
                bucket,
                options={
                    "public": True,
                    "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
                    "file_size_limit": 5 * 1024 * 1024,
                },
            )
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                print(f"Storage bucket check failed for {bucket}: {exc}")

ensure_storage_buckets()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(reviews_router, prefix="/api")
app.include_router(coupons_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")\napp.include_router(payments_router, prefix="/api")

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "seetharam-api"}

@app.get("/api/catalog")
def catalog():
    return {
        "store": "Seetharam",
        "business_model": "single-vendor-ready-for-multi-vendor",
        "categories": ["Men", "Women", "Kids", "Sarees", "Footwear", "Accessories"],
    }
