from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from enum import Enum

class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELED = "canceled"

class CreditPackage(str, Enum):
    STARTER = "starter"  # 500 credits for $9.99
    PROFESSIONAL = "professional"  # 2,000 credits for $29.99
    ENTERPRISE = "enterprise"  # 10,000 credits for $99.99

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    PAUSED = "paused"

class CreditTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    
    # Transaction details
    transaction_type: str  # "purchase", "usage", "refund", "bonus"
    credits_amount: int
    cost_usd: float = 0.0
    description: str
    
    # Related payment
    payment_intent_id: Optional[str] = None
    stripe_payment_id: Optional[str] = None
    
    # Usage tracking (for usage transactions)
    action_type: Optional[str] = None  # "email_process", "draft_generate", etc.
    related_resource_id: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = {}
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Payment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    
    # Payment details
    stripe_payment_intent_id: str
    amount_usd: float
    currency: str = "usd"
    status: PaymentStatus = PaymentStatus.PENDING
    
    # Package information
    package_type: CreditPackage
    credits_purchased: int
    
    # Stripe metadata
    stripe_customer_id: str
    payment_method_id: Optional[str] = None
    invoice_id: Optional[str] = None
    
    # Failure information
    failure_reason: Optional[str] = None
    failure_code: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    paid_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Subscription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    
    # Stripe subscription details
    stripe_subscription_id: str
    stripe_customer_id: str
    stripe_price_id: str
    
    # Subscription configuration
    plan_name: str
    credits_per_period: int
    amount_usd: float
    billing_period: str = "month"  # month, year
    
    # Status and timing
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    
    # Usage tracking
    credits_used_this_period: int = 0
    credits_remaining: int = 0
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Invoice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    
    # Stripe invoice details
    stripe_invoice_id: str
    stripe_customer_id: str
    
    # Invoice details
    invoice_number: str
    amount_due: float
    amount_paid: float
    currency: str = "usd"
    status: str  # draft, open, paid, void, uncollectible
    
    # Billing period
    period_start: datetime
    period_end: datetime
    due_date: datetime
    
    # Line items
    credits_purchased: int
    package_type: Optional[CreditPackage] = None
    
    # URLs
    invoice_pdf_url: Optional[str] = None
    hosted_invoice_url: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    paid_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Request/Response Models
class CreatePaymentIntentRequest(BaseModel):
    package_type: CreditPackage
    return_url: Optional[str] = None

class PaymentIntentResponse(BaseModel):
    payment_intent_id: str
    client_secret: str
    amount: float
    credits: int
    status: PaymentStatus

class CreditPackageInfo(BaseModel):
    package_type: CreditPackage
    credits: int
    price_usd: float
    price_per_credit: float
    description: str
    features: List[str] = []

class PaymentHistoryResponse(BaseModel):
    payments: List[Payment]
    transactions: List[CreditTransaction]
    total_count: int
    page: int
    limit: int

class SubscriptionResponse(BaseModel):
    id: str
    plan_name: str
    status: SubscriptionStatus
    credits_per_period: int
    credits_used_this_period: int
    credits_remaining: int
    amount_usd: float
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool

class CreateSubscriptionRequest(BaseModel):
    price_id: str
    payment_method_id: str

class UpdateSubscriptionRequest(BaseModel):
    cancel_at_period_end: Optional[bool] = None
    new_price_id: Optional[str] = None

class UsageStatsResponse(BaseModel):
    total_credits_purchased: int
    total_credits_used: int
    credits_remaining: int
    usage_by_action: Dict[str, int]
    usage_by_month: Dict[str, int]
    average_daily_usage: float
    projected_monthly_usage: int

class CreditBalanceResponse(BaseModel):
    total_credits: int
    used_credits: int
    remaining_credits: int
    last_purchase_date: Optional[datetime]
    credit_expiry_date: Optional[datetime]
    low_credit_threshold: int = 50
    needs_refill: bool

# Credit consumption tracking
CREDIT_COSTS = {
    "email_processing": 1,
    "draft_generation": 2,
    "calendar_analysis": 1,
    "urgent_notification": 0.5,
    "smart_scheduling": 1,
    "ai_analysis": 1,
    "auto_reply": 2,
    "meeting_scheduling": 1
}