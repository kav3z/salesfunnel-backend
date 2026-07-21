from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime


class ProductDimensions(BaseModel):
    """Product dimensions in cm"""
    length: float = Field(..., gt=0, description="Length in cm")
    width: float = Field(..., gt=0, description="Width in cm")
    height: float = Field(..., gt=0, description="Height in cm")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "length": 40.0,
                "width": 30.0,
                "height": 25.0
            }
        }
    )


class ProductBase(BaseModel):
    """Base product schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    price_per_case: Decimal = Field(..., gt=0, decimal_places=2, description="Price per case in NGN")
    stock_quantity: int = Field(default=0, ge=0, description="Available stock quantity in cases")
    category: Optional[str] = Field(None, max_length=100, description="Product category name")
    image_url: Optional[str] = Field(None, description="Product image URL")
    is_available: bool = Field(default=True, description="Product availability flag")
    dimensions: Optional[ProductDimensions] = Field(None, description="Product dimensions")
    weight: Optional[int] = Field(None, ge=0, description="Product weight in grams")


class ProductCreate(ProductBase):
    """Schema for creating a new product"""
    sku: str = Field(..., min_length=1, max_length=50, description="Unique Stock Keeping Unit (SKU)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sku": "DRK-ENG-001",
                "name": "Premium Energy Drink (Case of 24)",
                "description": "High-energy 500ml canned drinks packaged in cases of 24.",
                "price_per_case": "15000.00",
                "stock_quantity": 100,
                "category": "Beverages",
                "image_url": "https://res.cloudinary.com/demo/image/upload/sample.jpg",
                "is_available": True,
                "dimensions": {
                    "length": 40.0,
                    "width": 30.0,
                    "height": 25.0
                },
                "weight": 12000
            }
        }
    )


class ProductUpdate(BaseModel):
    """Schema for updating an existing product"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    price_per_case: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    stock_quantity: Optional[int] = Field(None, ge=0)
    category: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = None
    is_available: Optional[bool] = None
    dimensions: Optional[ProductDimensions] = None
    weight: Optional[int] = Field(None, ge=0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "price_per_case": "16500.00",
                "stock_quantity": 150,
                "is_available": True
            }
        }
    )


class ProductResponse(BaseModel):
    """Schema for product response"""
    id: UUID
    sku: str
    name: str
    description: Optional[str]
    price_per_case: Decimal
    stock_quantity: int
    distributor_id: UUID
    category: Optional[str]
    image_url: Optional[str]
    is_available: bool
    dimensions: Optional[dict] = None
    weight: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "c71d71c9-e9e4-49d8-96be-8248f20d5a00",
                "sku": "DRK-ENG-001",
                "name": "Premium Energy Drink (Case of 24)",
                "description": "High-energy 500ml canned drinks packaged in cases of 24.",
                "price_per_case": "15000.00",
                "stock_quantity": 100,
                "distributor_id": "89ab8ca4-e353-416b-b5b0-643c25aa99a1",
                "category": "Beverages",
                "image_url": "https://res.cloudinary.com/demo/image/upload/sample.jpg",
                "is_available": True,
                "dimensions": {
                    "length": 40.0,
                    "width": 30.0,
                    "height": 25.0
                },
                "weight": 12000,
                "created_at": "2026-07-15T09:00:00Z",
                "updated_at": "2026-07-19T12:00:00Z"
            }
        }
    )


class ProductListResponse(BaseModel):
    """Schema for paginated product list response"""
    products: List[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "products": [
                    {
                        "id": "c71d71c9-e9e4-49d8-96be-8248f20d5a00",
                        "sku": "DRK-ENG-001",
                        "name": "Premium Energy Drink (Case of 24)",
                        "price_per_case": "15000.00",
                        "stock_quantity": 100,
                        "distributor_id": "89ab8ca4-e353-416b-b5b0-643c25aa99a1",
                        "category": "Beverages",
                        "is_available": True
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 20,
                "total_pages": 1
            }
        }
    )
