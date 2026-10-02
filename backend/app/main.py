from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(title="Seetharam API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "seetharam-api"}

@app.get("/api/catalog")
def catalog():
    return {"categories": ["Men", "Women", "Kids", "Sarees", "Footwear", "Accessories"]}
