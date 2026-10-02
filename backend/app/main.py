from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes.products import router as products_router
from app.api.routes.categories import router as categories_router
from app.api.routes.orders import router as orders_router
from app.api.routes.admin import router as admin_router
from app.api.routes.reviews import router as reviews_router

app = FastAPI(title="Seetharam API", version="0.1.0")

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
