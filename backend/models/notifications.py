from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from enum import Enum

class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    IN_APP = "in_app"

class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"

class NotificationType(str, Enum):
    URGENT_EMAIL = "urgent_email"
    MEETING_REMINDER = "meeting_reminder"
    CALENDAR_CONFLICT = "calendar_conflict"
    CREDIT_LOW = "credit_low"
    SYSTEM_UPDATE = "system_update"
    INTEGRATION_ERROR = "integration_error"
    DAILY_SUMMARY = "daily_summary"

class DeliveryAttempt(BaseModel):
    channel: NotificationChannel
    attempted_at: datetime
    status: NotificationStatus
    error_message: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None

class NotificationContent(BaseModel):
    title: str
    message: str
    html_content: Optional[str] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    metadata: Dict[str, Any] = {}

class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    
    # Notification details
    type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    content: NotificationContent
    
    # Delivery configuration
    preferred_channels: List[NotificationChannel]
    fallback_channels: List[NotificationChannel] = []
    
    # Scheduling
    scheduled_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    # Status tracking
    status: NotificationStatus = NotificationStatus.PENDING
    delivery_attempts: List[DeliveryAttempt] = []
    
    # Related entities
    related_email_id: Optional[str] = None
    related_event_id: Optional[str] = None
    related_user_action: Optional[str] = None
    
    # Rate limiting
    rate_limit_group: Optional[str] = None
    respect_quiet_hours: bool = True
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class NotificationTemplate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: NotificationType
    template_name: str
    
    # Template content
    title_template: str
    message_template: str
    html_template: Optional[str] = None
    
    # Template variables
    required_variables: List[str] = []
    optional_variables: List[str] = []
    
    # Delivery settings
    default_channels: List[NotificationChannel]
    default_priority: NotificationPriority = NotificationPriority.NORMAL
    
    # Personalization
    supports_personalization: bool = True
    language_variants: Dict[str, Dict[str, str]] = {}
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserNotificationPreferences(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    
    # Channel preferences by type
    channel_preferences: Dict[NotificationType, List[NotificationChannel]] = {}
    
    # Quiet hours
    quiet_hours_enabled: bool = True
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    quiet_hours_timezone: str = "UTC"
    
    # Rate limiting preferences
    max_notifications_per_hour: Dict[NotificationChannel, int] = {
        NotificationChannel.EMAIL: 10,
        NotificationChannel.SMS: 5,
        NotificationChannel.WHATSAPP: 5
    }
    
    # Priority overrides
    urgent_override_quiet_hours: bool = True
    high_priority_channels: List[NotificationChannel] = [NotificationChannel.SMS]
    
    # Batching preferences
    enable_batching: bool = True
    batch_delay_minutes: int = 15
    batch_types: List[NotificationType] = [NotificationType.DAILY_SUMMARY]
    
    # Personalization
    preferred_language: str = "en"
    timezone: str = "UTC"
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Request/Response Models
class SendNotificationRequest(BaseModel):
    user_id: str
    type: NotificationType
    title: str
    message: str
    channels: List[NotificationChannel]
    priority: NotificationPriority = NotificationPriority.NORMAL
    scheduled_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}
    related_email_id: Optional[str] = None
    related_event_id: Optional[str] = None

class NotificationResponse(BaseModel):
    id: str
    type: NotificationType
    priority: NotificationPriority
    content: NotificationContent
    status: NotificationStatus
    preferred_channels: List[NotificationChannel]
    scheduled_at: datetime
    created_at: datetime
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]

class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total_count: int
    unread_count: int
    page: int
    limit: int

class NotificationPreferencesResponse(BaseModel):
    id: str
    user_id: str
    channel_preferences: Dict[NotificationType, List[NotificationChannel]]
    quiet_hours_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str
    max_notifications_per_hour: Dict[NotificationChannel, int]
    urgent_override_quiet_hours: bool
    enable_batching: bool
    preferred_language: str
    timezone: str

class UpdateNotificationPreferencesRequest(BaseModel):
    channel_preferences: Optional[Dict[NotificationType, List[NotificationChannel]]] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    max_notifications_per_hour: Optional[Dict[NotificationChannel, int]] = None
    urgent_override_quiet_hours: Optional[bool] = None
    enable_batching: Optional[bool] = None
    preferred_language: Optional[str] = None
    timezone: Optional[str] = None

class NotificationStatsResponse(BaseModel):
    total_sent: int
    total_delivered: int
    total_failed: int
    channel_stats: Dict[NotificationChannel, Dict[str, int]]
    type_stats: Dict[NotificationType, Dict[str, int]]
    recent_activity: List[NotificationResponse]