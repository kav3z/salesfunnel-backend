from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime


class CartItemAdd(BaseModel):
    """Schema for adding a product to cart"""
    product_id: UUID = Field(..., description="Product UUID to add to cart")
    quantity: int = Field(..., gt=0, description="Quantity to add")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_id": "c71d71c9-e9e4-49d8-96be-8248f20d5a00",
                "quantity": 5
            }
        }
    )


class CartItemUpdate(BaseModel):
    """Schema for updating cart item quantity"""
    product_id: UUID = Field(..., description="Product UUID to update")
    quantity: int = Field(..., gt=0, description="New quantity")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_id": "c71d71c9-e9e4-49d8-96be-8248f20d5a00",
                "quantity": 10
            }
        }
    )


class CartItemRemove(BaseModel):
    """Schema for removing a product from cart"""
    product_id: UUID = Field(..., description="Product UUID to remove")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_id": "c71d71c9-e9e4-49d8-96be-8248f20d5a00"
            }
        }
    )


class CartItemResponse(BaseModel):
    """Schema for cart item response"""
    cart_item_id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    product_image_url: Optional[str]
    distributor_id: UUID
    unit_price: Decimal
    quantity: int
    subtotal: Decimal
    added_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "cart_item_id": "f81d71c9-e9e4-49d8-96be-8248f20d5a99",
                "product_id": "c71d71c9-e9e4-49d8-96be-8248f20d5a00",
                "product_name": "Premium Energy Drink (Case of 24)",
                "product_sku": "DRK-ENG-001",
                "product_image_url": "https://res.cloudinary.com/demo/image/upload/sample.jpg",
                "distributor_id": "89ab8ca4-e353-416b-b5b0-643c25aa99a1",
                "unit_price": "15000.00",
                "quantity": 5,
                "subtotal": "75000.00",
                "added_at": "2026-07-19T11:00:00Z"
            }
        }
    )


class CartResponse(BaseModel):
    """Schema for full cart response"""
    id: UUID
    wholesaler_id: UUID
    items: List[CartItemResponse]
    total_items: int
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "b11d71c9-e9e4-49d8-96be-8248f20d5a77",
                "wholesaler_id": "f31d71c9-e9e4-49d8-96be-8248f20d5a8e",
                "items": [
                    {
                        "cart_item_id": "f81d71c9-e9e4-49d8-96be-8248f20d5a99",
                        "product_id": "c71d71c9-e9e4-49d8-96be-8248f20d5a00",
                        "product_name": "Premium Energy Drink (Case of 24)",
                        "product_sku": "DRK-ENG-001",
                        "distributor_id": "89ab8ca4-e353-416b-b5b0-643c25aa99a1",
                        "unit_price": "15000.00",
                        "quantity": 5,
                        "subtotal": "75000.00"
                    }
                ],
                "total_items": 5,
                "total_amount": "75000.00",
                "created_at": "2026-07-19T10:00:00Z",
                "updated_at": "2026-07-19T11:00:00Z"
            }
        }
    )
