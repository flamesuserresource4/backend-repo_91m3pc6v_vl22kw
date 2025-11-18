import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="StyleAura API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProductFilter(BaseModel):
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    size: Optional[str] = None
    color: Optional[str] = None
    q: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "StyleAura backend is running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

# Seed sample products for prototype
@app.post("/seed")
def seed_products():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    sample_products = [
        {
            "title": "Men's Classic Denim Jacket",
            "description": "Timeless denim with a modern fit.",
            "price": 79.99,
            "category": "Men",
            "images": [
                "https://images.unsplash.com/photo-1520975916090-3105956dac38?q=80&w=1200&auto=format&fit=crop",
            ],
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Blue"],
            "rating": 4.6,
            "discount_percent": 10,
            "in_stock": True,
            "tags": ["jacket", "denim", "men"]
        },
        {
            "title": "Women's Linen Summer Dress",
            "description": "Breathable, elegant, and perfect for warm days.",
            "price": 64.50,
            "category": "Women",
            "images": [
                "https://images.unsplash.com/photo-1519238263530-99bdd11df2ea?q=80&w=1200&auto=format&fit=crop",
            ],
            "sizes": ["XS", "S", "M", "L"],
            "colors": ["Beige", "Olive"],
            "rating": 4.7,
            "discount_percent": 0,
            "in_stock": True,
            "tags": ["dress", "linen", "women"]
        },
        {
            "title": "Unisex Oversized Hoodie",
            "description": "Cozy fleece-lined hoodie for everyday comfort.",
            "price": 49.00,
            "category": "Accessories",
            "images": [
                "https://images.unsplash.com/photo-1516826957135-700dedea698c?q=80&w=1200&auto=format&fit=crop",
            ],
            "sizes": ["S", "M", "L", "XL"],
            "colors": ["Black", "Grey"],
            "rating": 4.4,
            "discount_percent": 15,
            "in_stock": True,
            "tags": ["hoodie", "unisex"]
        }
    ]

    inserted_ids = []
    for p in sample_products:
        _id = create_document("clothingproduct", p)
        inserted_ids.append(_id)
    return {"inserted": inserted_ids}

# Products listing with filters and search
@app.get("/products")
def list_products(
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    size: Optional[str] = None,
    color: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200)
):
    if db is None:
        return []

    query: dict = {}
    if category:
        query["category"] = category
    if min_price is not None or max_price is not None:
        price_filter = {}
        if min_price is not None:
            price_filter["$gte"] = min_price
        if max_price is not None:
            price_filter["$lte"] = max_price
        query["price"] = price_filter
    if size:
        query["sizes"] = {"$in": [size]}
    if color:
        query["colors"] = {"$in": [color]}
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"tags": {"$regex": q, "$options": "i"}},
        ]

    docs = get_documents("clothingproduct", query, limit)
    # Convert ObjectId to string
    for d in docs:
        if d.get("_id"):
            d["_id"] = str(d["_id"])
    return docs

# Single product details
@app.get("/products/{product_id}")
def get_product(product_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")
    doc = db["clothingproduct"].find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    doc["_id"] = str(doc["_id"]) 
    return doc

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
