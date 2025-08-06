from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
from enum import Enum

class CalendarProvider(str, Enum):
    GOOGLE = "google"
    OUTLOOK = "outlook"

class EventStatus(str, Enum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

class AttendeeStatus(str, Enum):
    NEEDS_ACTION = "needsAction"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    TENTATIVE = "tentative"

class RecurrenceFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

class ConflictType(str, Enum):
    HARD = "hard"  # Direct time overlap
    SOFT = "soft"  # Buffer time violation
    TRAVEL = "travel"  # Insufficient travel time

class EventAttendee(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    status: AttendeeStatus = AttendeeStatus.NEEDS_ACTION
    is_organizer: bool = False
    is_required: bool = True

class EventLocation(BaseModel):
    name: str
    address: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None  # lat, lng
    meeting_room_id: Optional[str] = None
    virtual_link: Optional[str] = None
    is_virtual: bool = False

class RecurrenceRule(BaseModel):
    frequency: RecurrenceFrequency
    interval: int = 1
    count: Optional[int] = None
    until: Optional[datetime] = None
    by_day: List[str] = []  # ["MO", "WE", "FR"]
    by_month_day: List[int] = []

class ConflictInfo(BaseModel):
    conflict_type: ConflictType
    conflicting_event_id: str
    conflicting_event_title: str
    overlap_duration_minutes: int
    suggested_resolution: Optional[str] = None

class AISchedulingAnalysis(BaseModel):
    optimal_time_score: float  # 0.0 to 1.0
    productivity_impact: str  # low, medium, high
    meeting_type_classification: str
    estimated_preparation_time: int = 15
    recommended_buffer_time: int = 15
    energy_level_match: str  # high, medium, low
    conflicts_detected: List[ConflictInfo] = []
    scheduling_suggestions: List[str] = []

class CalendarEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    provider: CalendarProvider
    
    # Event basic info
    title: str
    description: Optional[str] = None
    location: Optional[EventLocation] = None
    
    # Timing
    start_datetime: datetime
    end_datetime: datetime
    all_day: bool = False
    timezone: str = "UTC"
    
    # Attendees
    attendees: List[EventAttendee] = []
    organizer: EventAttendee
    
    # Event properties
    status: EventStatus = EventStatus.CONFIRMED
    visibility: str = "default"  # default, public, private
    importance: str = "normal"  # low, normal, high
    
    # Recurrence
    is_recurring: bool = False
    recurrence_rule: Optional[RecurrenceRule] = None
    recurrence_id: Optional[str] = None  # For recurring event instances
    
    # Provider metadata
    provider_event_id: str
    provider_calendar_id: str
    provider_metadata: Dict[str, Any] = {}
    
    # AI Analysis
    ai_analysis: Optional[AISchedulingAnalysis] = None
    created_by_ai: bool = False
    
    # Related data
    source_email_id: Optional[str] = None  # If created from email
    meeting_link: Optional[str] = None
    meeting_notes: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_modified_by: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AvailabilitySlot(BaseModel):
    start_datetime: datetime
    end_datetime: datetime
    is_busy: bool = False
    event_title: Optional[str] = None
    event_id: Optional[str] = None
    buffer_time_needed: bool = False

class SchedulingSuggestion(BaseModel):
    suggested_datetime: datetime
    duration_minutes: int
    confidence_score: float
    reasons: List[str] = []
    attendee_availability: Dict[str, bool] = {}
    optimal_score: float = 0.0

class MeetingTemplate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    template_name: str
    default_duration_minutes: int = 30
    default_attendees: List[str] = []
    default_location: Optional[EventLocation] = None
    default_description: str = ""
    buffer_time_minutes: int = 15
    preferred_times: List[str] = []  # Time slots like "09:00-12:00"
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Request/Response Models
class AvailabilityRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    attendee_emails: Optional[List[str]] = None
    duration_minutes: int = 30
    buffer_time_minutes: int = 15

class AvailabilityResponse(BaseModel):
    date: str
    slots: List[AvailabilitySlot]
    suggestions: List[SchedulingSuggestion]

class EventCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    attendee_emails: List[str] = []
    location: Optional[EventLocation] = None
    is_recurring: bool = False
    recurrence_rule: Optional[RecurrenceRule] = None
    calendar_id: Optional[str] = None

class EventUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    attendee_emails: Optional[List[str]] = None
    location: Optional[EventLocation] = None
    status: Optional[EventStatus] = None

class EventResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    start_datetime: datetime
    end_datetime: datetime
    location: Optional[EventLocation]
    attendees: List[EventAttendee]
    status: EventStatus
    is_recurring: bool
    ai_analysis: Optional[AISchedulingAnalysis]
    created_by_ai: bool
    created_at: datetime

class SmartSchedulingRequest(BaseModel):
    title: str
    duration_minutes: int = 30
    attendee_emails: List[str]
    preferred_times: Optional[List[str]] = None  # ["morning", "afternoon"]
    date_range_start: datetime
    date_range_end: datetime
    meeting_type: Optional[str] = None
    location_preference: Optional[str] = None  # "virtual", "in-person", "any"
    buffer_time_minutes: int = 15

class ConflictResolutionRequest(BaseModel):
    event_id: str
    resolution_strategy: str  # "reschedule", "shorten", "cancel"
    preferred_alternatives: Optional[List[datetime]] = None

class CalendarSyncStatus(BaseModel):
    provider: CalendarProvider
    calendar_id: str
    calendar_name: str
    last_sync: datetime
    sync_status: str  # "active", "error", "paused"
    event_count: int
    next_sync: Optional[datetime] = None