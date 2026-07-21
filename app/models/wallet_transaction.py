import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field

class TransactionType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"

class TransactionPurpose(str, Enum):
    FUNDING = "funding"        # Wholesaler funding wallet
    PAYMENT = "payment"        # Pay for order / Receive order payment
    WITHDRAWAL = "withdrawal"  # Distributor payout to bank
    REFUND = "refund"          # Cancelled order refund

class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class WalletTransaction(SQLModel, table=True):
    __tablename__ = "wallet_transactions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    wallet_id: uuid.UUID = Field(foreign_key="wallets.id", index=True, nullable=False)
    amount: Decimal = Field(decimal_places=2, max_digits=16, nullable=False)
    type: TransactionType = Field(nullable=False)
    purpose: TransactionPurpose = Field(nullable=False)
    status: TransactionStatus = Field(default=TransactionStatus.PENDING, nullable=False)
    reference: str = Field(unique=True, index=True, nullable=False)  # Paystack ref or custom ref
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    available_at: datetime = Field(default_factory=datetime.utcnow)  # Used for the 24-hour clearance lock
