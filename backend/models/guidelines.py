from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import uuid
from enum import Enum

class GuidelineCategory(str, Enum):
    EMAIL_MANAGEMENT = "email_management"
    CALENDAR_SCHEDULING = "calendar_scheduling"
    NOTIFICATION_PREFERENCES = "notification_preferences"
    COMMUNICATION_STYLE = "communication_style"
    AUTOMATION_RULES = "automation_rules"

class PriorityLevel(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class ResponseTone(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    FRIENDLY = "friendly"
    FORMAL = "formal"
    CONCISE = "concise"

class EmailClassificationRule(BaseModel):
    sender_patterns: List[str] = []  # Email patterns or domains
    subject_keywords: List[str] = []
    content_keywords: List[str] = []
    priority_level: PriorityLevel = PriorityLevel.NORMAL
    auto_reply: bool = False
    notification_required: bool = True
    folder_assignment: Optional[str] = None

class SchedulingPreference(BaseModel):
    meeting_types: List[str] = []  # e.g., "standup", "review", "1on1"
    preferred_duration_minutes: int = 30
    buffer_time_minutes: int = 15
    optimal_time_slots: List[str] = []  # e.g., "09:00-11:00", "14:00-16:00"
    avoid_time_slots: List[str] = []
    max_consecutive_meetings: int = 3
    require_location: bool = False
    auto_decline_conflicts: bool = False

class NotificationRule(BaseModel):
    trigger_conditions: List[str] = []  # Keywords or patterns
    channels: List[str] = ["email"]  # email, sms, whatsapp
    urgency_threshold: PriorityLevel = PriorityLevel.HIGH
    quiet_hours_respect: bool = True
    escalation_delay_minutes: int = 60
    max_notifications_per_hour: int = 5

class CommunicationStyleGuide(BaseModel):
    default_tone: ResponseTone = ResponseTone.PROFESSIONAL
    signature: Optional[str] = None
    greeting_style: str = "formal"  # formal, casual, none
    closing_style: str = "formal"  # formal, casual, none
    preferred_response_length: str = "medium"  # brief, medium, detailed
    include_context: bool = True
    cc_behavior: str = "preserve"  # preserve, remove, selective

class AutomationRule(BaseModel):
    rule_name: str
    description: str
    conditions: Dict[str, Any] = {}
    actions: List[Dict[str, Any]] = []
    is_active: bool = True
    confidence_threshold: float = 0.7
    learning_enabled: bool = True

class GuidelineVersion(BaseModel):
    version_number: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    changes_summary: str = "Initial version"
    is_active: bool = True

class UserGuidelines(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    
    # Core guideline categories
    email_classification_rules: List[EmailClassificationRule] = []
    scheduling_preferences: List[SchedulingPreference] = []
    notification_rules: List[NotificationRule] = []
    communication_style: CommunicationStyleGuide = Field(default_factory=CommunicationStyleGuide)
    automation_rules: List[AutomationRule] = []
    
    # Learning and adaptation
    learning_enabled: bool = True
    adaptation_aggressiveness: str = "moderate"  # conservative, moderate, aggressive
    feedback_weight: float = 0.8
    
    # Version control
    current_version: GuidelineVersion = Field(default_factory=GuidelineVersion)
    version_history: List[GuidelineVersion] = []
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_learning_update: Optional[datetime] = None
    
    # Custom user-defined guidelines (free text)
    custom_instructions: str = ""
    special_contacts: Dict[str, Dict[str, Any]] = {}  # email -> special handling rules
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Request/Response models
class GuidelinesUpdateRequest(BaseModel):
    email_classification_rules: Optional[List[EmailClassificationRule]] = None
    scheduling_preferences: Optional[List[SchedulingPreference]] = None
    notification_rules: Optional[List[NotificationRule]] = None
    communication_style: Optional[CommunicationStyleGuide] = None
    automation_rules: Optional[List[AutomationRule]] = None
    custom_instructions: Optional[str] = None
    special_contacts: Optional[Dict[str, Dict[str, Any]]] = None

class GuidelinesFeedback(BaseModel):
    guideline_id: str
    action_id: str  # ID of the action that was taken
    feedback_type: str  # "positive", "negative", "modification"
    feedback_details: Optional[str] = None
    suggested_improvement: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class GuidelinesResponse(BaseModel):
    id: str
    user_id: str
    email_classification_rules: List[EmailClassificationRule]
    scheduling_preferences: List[SchedulingPreference]
    notification_rules: List[NotificationRule]
    communication_style: CommunicationStyleGuide
    automation_rules: List[AutomationRule]
    learning_enabled: bool
    current_version: GuidelineVersion
    custom_instructions: str
    created_at: datetime
    updated_at: datetime
    last_learning_update: Optional[datetime]