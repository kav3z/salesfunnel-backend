from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class PaymentInfoResponse(BaseModel):
    """Payment information response"""
    order_number: str
    wholesaler_name: str
    amount: Decimal
    date: str
    time: str
    reference_number: str
    status: PaymentStatus

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "order_number": "ORD-20260719-001",
                "wholesaler_name": "Apex Wholesale Ltd",
                "amount": "150000.00",
                "date": "2026-07-19",
                "time": "14:30:00",
                "reference_number": "PAY-REF-998822",
                "status": "completed"
            }
        }
    )


class PaymentListResponse(BaseModel):
    """Paginated payment list response"""
    payments: List[PaymentInfoResponse]
    total: int = Field(..., description="Total number of payments")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "payments": [
                    {
                        "order_number": "ORD-20260719-001",
                        "wholesaler_name": "Apex Wholesale Ltd",
                        "amount": "150000.00",
                        "date": "2026-07-19",
                        "time": "14:30:00",
                        "reference_number": "PAY-REF-998822",
                        "status": "completed"
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 20,
                "total_pages": 1
            }
        }
    )
