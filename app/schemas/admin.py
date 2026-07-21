# External imports
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

# Local imports
from app.models.user import UserRole
from app.models.order import OrderStatus
from app.models.payment import PaymentStatus


# Admin-specific schemas
class AdminUserResponse(BaseModel):
    """Extended user response for admin view"""
    id: str
    email: str
    full_name: str
    phone: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    business_name: Optional[str] = None
    is_verified: Optional[bool] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "f31d71c9-e9e4-49d8-96be-8248f20d5a8e",
                "email": "wholesaler@example.com",
                "full_name": "Apex Wholesale Ltd",
                "phone": "+2348012345678",
                "role": "wholesaler",
                "is_active": True,
                "created_at": "2026-01-15T10:30:00Z",
                "updated_at": "2026-07-19T14:00:00Z",
                "business_name": "Apex Wholesale Ltd",
                "is_verified": True
            }
        }
    )


class AdminUserListResponse(BaseModel):
    """Paginated user list for admin"""
    users: List[AdminUserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "users": [
                    {
                        "id": "f31d71c9-e9e4-49d8-96be-8248f20d5a8e",
                        "email": "wholesaler@example.com",
                        "full_name": "Apex Wholesale Ltd",
                        "phone": "+2348012345678",
                        "role": "wholesaler",
                        "is_active": True,
                        "created_at": "2026-01-15T10:30:00Z",
                        "updated_at": "2026-07-19T14:00:00Z",
                        "business_name": "Apex Wholesale Ltd",
                        "is_verified": True
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 20,
                "total_pages": 1
            }
        }
    )


class AdminOrderResponse(BaseModel):
    """Extended order response with payment status for admin view"""
    id: UUID
    order_number: str
    wholesaler_id: UUID
    wholesaler_name: Optional[str]
    distributor_id: UUID
    distributor_name: Optional[str]
    total_amount: Decimal
    status: OrderStatus
    payment_status: Optional[PaymentStatus]
    payment_reference: Optional[str]
    notes: Optional[str]
    created_at: datetime
    paid_at: Optional[datetime]
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "a11d71c9-e9e4-49d8-96be-8248f20d5a22",
                "order_number": "ORD-20260719-001",
                "wholesaler_id": "f31d71c9-e9e4-49d8-96be-8248f20d5a8e",
                "wholesaler_name": "Apex Wholesale Ltd",
                "distributor_id": "89ab8ca4-e353-416b-b5b0-643c25aa99a1",
                "distributor_name": "Prime Distribution Hub",
                "total_amount": "150000.00",
                "status": "paid",
                "payment_status": "verified",
                "payment_reference": "PAY-REF-998822",
                "notes": "Handle with care",
                "created_at": "2026-07-19T10:00:00Z",
                "paid_at": "2026-07-19T10:05:00Z"
            }
        }
    )


class AdminOrderListResponse(BaseModel):
    """Paginated order list for admin"""
    orders: List[AdminOrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "orders": [
                    {
                        "id": "a11d71c9-e9e4-49d8-96be-8248f20d5a22",
                        "order_number": "ORD-20260719-001",
                        "wholesaler_id": "f31d71c9-e9e4-49d8-96be-8248f20d5a8e",
                        "wholesaler_name": "Apex Wholesale Ltd",
                        "distributor_id": "89ab8ca4-e353-416b-b5b0-643c25aa99a1",
                        "distributor_name": "Prime Distribution Hub",
                        "total_amount": "150000.00",
                        "status": "paid",
                        "payment_status": "verified",
                        "created_at": "2026-07-19T10:00:00Z"
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 20,
                "total_pages": 1
            }
        }
    )


class OrderStatusOverride(BaseModel):
    """Schema for admin order status override"""
    status: OrderStatus = Field(..., description="Target order status to override")
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for status override")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "completed",
                "reason": "Manual confirmation received from distributor."
            }
        }
    )
