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

class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=220)
    description: str | None = None
    sku: str | None = None
    category_id: str | None = None
    brand_id: str | None = None
    price: float = Field(ge=0)
    compare_at_price: float | None = Field(default=None, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    is_featured: bool = False
    is_new_arrival: bool = False
    is_best_seller: bool = False
    is_active: bool = True

class ProductUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    sku: str | None = None
    category_id: str | None = None
    brand_id: str | None = None
    price: float | None = Field(default=None, ge=0)
    compare_at_price: float | None = Field(default=None, ge=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    is_featured: bool | None = None
    is_new_arrival: bool | None = None
    is_best_seller: bool | None = None
    is_active: bool | None = None

class ImageCreate(BaseModel):
    image_url: str = Field(min_length=5)
    alt_text: str | None = None
    sort_order: int = Field(default=0, ge=0)

class VariantCreate(BaseModel):
    size: str | None = None
    color: str | None = None
    sku: str | None = None
    price: float | None = Field(default=None, ge=0)
    stock_quantity: int = Field(default=0, ge=0)

class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=120)
    image_url: str | None = None
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True

class BrandCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=120)
    logo_url: str | None = None
    is_active: bool = True

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

@router.post("/products")
def create_product(payload: ProductCreate, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    values = payload.model_dump()
    result = client.table("products").insert(values).execute()
    return {"product": result.data[0] if result.data else None}

@router.patch("/products/{product_id}")
def update_product(product_id: str, payload: ProductUpdate, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    values = payload.model_dump(exclude_none=True)
    if not values:
        raise HTTPException(status_code=400, detail="No changes supplied.")
    result = client.table("products").update(values).eq("id", product_id).execute()
    return {"product": result.data[0] if result.data else None}

@router.delete("/products/{product_id}")
def delete_product(product_id: str, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("products").update({"is_active": False}).eq("id", product_id).execute()
    return {"product": result.data[0] if result.data else None}

from fastapi import File, UploadFile
import uuid

@router.post("/products/{product_id}/images/upload")
async def upload_product_image(product_id: str, file: UploadFile = File(...), authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, and WebP images are allowed.")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be 5 MB or smaller.")
    ext = {"image/jpeg":"jpg","image/png":"png","image/webp":"webp"}[file.content_type]
    path = f"products/{product_id}/{uuid.uuid4()}.{ext}"
    try:
        client.storage.from_("product-images").upload(path, data, {"content-type": file.content_type, "upsert": False})
        public_url = client.storage.from_("product-images").get_public_url(path)
        existing = client.table("product_images").select("id").eq("product_id", product_id).execute()
        result = client.table("product_images").insert({"product_id":product_id,"image_url":public_url,"alt_text":file.filename or "Product image","sort_order":len(existing.data or [])}).execute()
        return {"image": result.data[0] if result.data else None, "url": public_url}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {exc}")

@router.get("/products/{product_id}/images")
def product_images(product_id: str, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("product_images").select("*").eq("product_id", product_id).order("sort_order").execute()
    return {"items": result.data or []}

@router.post("/products/{product_id}/images")
def add_product_image(product_id: str, payload: ImageCreate, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("product_images").insert({"product_id": product_id, **payload.model_dump()}).execute()
    return {"image": result.data[0] if result.data else None}

@router.delete("/products/{product_id}/images/{image_id}")
def delete_product_image(product_id: str, image_id: str, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("product_images").delete().eq("id", image_id).eq("product_id", product_id).execute()
    return {"deleted": bool(result.data)}

@router.get("/products/{product_id}/variants")
def product_variants(product_id: str, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("product_variants").select("*").eq("product_id", product_id).order("size").execute()
    return {"items": result.data or []}

@router.post("/products/{product_id}/variants")
def add_product_variant(product_id: str, payload: VariantCreate, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("product_variants").insert({"product_id": product_id, **payload.model_dump()}).execute()
    return {"variant": result.data[0] if result.data else None}

@router.delete("/products/{product_id}/variants/{variant_id}")
def delete_product_variant(product_id: str, variant_id: str, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("product_variants").delete().eq("id", variant_id).eq("product_id", product_id).execute()
    return {"deleted": bool(result.data)}

@router.get("/categories")
def admin_categories(authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("categories").select("*").order("sort_order").execute()
    return {"items": result.data or []}

@router.post("/categories")
def create_category(payload: CategoryCreate, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("categories").insert(payload.model_dump()).execute()
    return {"category": result.data[0] if result.data else None}

@router.patch("/categories/{category_id}")
def update_category(category_id: str, payload: CategoryCreate, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("categories").update(payload.model_dump()).eq("id", category_id).execute()
    return {"category": result.data[0] if result.data else None}

@router.get("/brands")
def admin_brands(authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("brands").select("*").order("name").execute()
    return {"items": result.data or []}

@router.post("/brands")
def create_brand(payload: BrandCreate, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("brands").insert(payload.model_dump()).execute()
    return {"brand": result.data[0] if result.data else None}

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
    updated = result.data[0] if result.data else None
    if updated and updated.get("user_id") and settings.supabase_service_role_key:
        messages = {"packed":"Your order has been packed.","shipped":"Your order has shipped.","out_for_delivery":"Your order is out for delivery.","delivered":"Your order has been delivered.","cancelled":"Your order was cancelled.","return_requested":"Your return request is being reviewed.","returned":"Your return has been received.","refunded":"Your refund has been processed.","ordered":"Your order is confirmed."}
        client.table("notifications").insert({"user_id": updated["user_id"], "title": "Order " + status.replace("_", " "), "message": messages.get(status, "Your order status was updated.") + " Order #" + str(order_id)[:8] + ".", "type": "order", "order_id": order_id}).execute()
    return {"order": updated}

@router.get("/reviews")
def reviews(authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("reviews").select("*,products(name),profiles(full_name)").order("created_at", desc=True).limit(200).execute()
    return {"items": result.data or []}

@router.patch("/reviews/{review_id}")
def moderate_review(review_id: str, approved: bool, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("reviews").update({"is_approved": approved}).eq("id", review_id).execute()
    return {"review": result.data[0] if result.data else None}

class CouponCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    description: str | None = None
    discount_type: str
    discount_value: float = Field(gt=0)
    minimum_order_value: float = Field(default=0, ge=0)
    max_discount: float | None = Field(default=None, ge=0)
    usage_limit: int | None = Field(default=None, ge=1)
    starts_at: str | None = None
    expires_at: str | None = None
    is_active: bool = True

@router.get("/coupons")
def coupons(authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    result = client.table("coupons").select("*").order("is_active", desc=True).order("expires_at").execute()
    return {"items": result.data or []}

@router.post("/coupons")
def create_coupon(payload: CouponCreate, authorization: str | None = Header(default=None)):
    client = admin_client(authorization)
    if payload.discount_type not in ("percent","fixed"):
        raise HTTPException(status_code=400, detail="Discount type must be percent or fixed.")
    if payload.discount_type == "percent" and payload.discount_value > 100:
        raise HTTPException(status_code=400, detail="Percentage discount cannot exceed 100.")
    values=payload.model_dump()
    values["code"]=payload.code.strip().upper()
    result=client.table("coupons").insert(values).execute()
    return {"coupon": result.data[0] if result.data else None}

@router.patch("/coupons/{coupon_id}")
def update_coupon(coupon_id: str, payload: dict, authorization: str | None = Header(default=None)):
    client=admin_client(authorization)
    allowed={"description","discount_type","discount_value","minimum_order_value","max_discount","usage_limit","starts_at","expires_at","is_active"}
    values={k:v for k,v in payload.items() if k in allowed}
    if values.get("discount_type")=="percent" and float(values.get("discount_value",0))>100: raise HTTPException(status_code=400,detail="Percentage discount cannot exceed 100.")
    result=client.table("coupons").update(values).eq("id",coupon_id).execute()
    return {"coupon": result.data[0] if result.data else None}
