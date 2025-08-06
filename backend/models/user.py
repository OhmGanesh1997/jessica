from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

class UserPreferences(BaseModel):
    timezone: str = "UTC"
    work_hours_start: str = "09:00"
    work_hours_end: str = "17:00"
    work_days: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    notification_channels: List[str] = ["email", "sms"]
    urgent_keywords: List[str] = ["urgent", "asap", "deadline", "emergency"]
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"

class UserProfile(BaseModel):
    full_name: str
    job_title: Optional[str] = None
    company: Optional[str] = None
    phone_number: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

class CreditBalance(BaseModel):
    total_credits: int = 50  # Free credits on signup
    used_credits: int = 0
    remaining_credits: int = 50
    last_purchase_date: Optional[datetime] = None
    credit_expiry_date: Optional[datetime] = None

class ThirdPartyConnections(BaseModel):
    google_connected: bool = False
    google_refresh_token: Optional[str] = None
    google_access_token: Optional[str] = None
    google_token_expiry: Optional[datetime] = None
    
    microsoft_connected: bool = False
    microsoft_refresh_token: Optional[str] = None
    microsoft_access_token: Optional[str] = None
    microsoft_token_expiry: Optional[datetime] = None
    
    connected_calendars: List[str] = []
    connected_email_accounts: List[str] = []

class UserActivityStats(BaseModel):
    emails_processed: int = 0
    drafts_generated: int = 0
    meetings_scheduled: int = 0
    notifications_sent: int = 0
    last_active: Optional[datetime] = None
    total_time_saved_minutes: int = 0

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    verification_token: Optional[str] = None
    reset_password_token: Optional[str] = None
    reset_password_expires: Optional[datetime] = None
    
    # Profile and preferences
    profile: UserProfile
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    
    # Credits and billing
    credits: CreditBalance = Field(default_factory=CreditBalance)
    stripe_customer_id: Optional[str] = None
    subscription_status: str = "free"  # free, active, cancelled, past_due
    
    # Integrations
    connections: ThirdPartyConnections = Field(default_factory=ThirdPartyConnections)
    
    # Activity tracking
    activity: UserActivityStats = Field(default_factory=UserActivityStats)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Request/Response Models
class UserRegistrationRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2)
    job_title: Optional[str] = None
    company: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    profile: UserProfile
    preferences: UserPreferences
    credits: CreditBalance
    connections: ThirdPartyConnections
    activity: UserActivityStats
    subscription_status: str
    created_at: datetime
    last_login: Optional[datetime]

class UserUpdateRequest(BaseModel):
    profile: Optional[UserProfile] = None
    preferences: Optional[UserPreferences] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse