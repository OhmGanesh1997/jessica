from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from enum import Enum

class EmailProvider(str, Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"

class EmailPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class EmailStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    REPLIED = "replied"
    FORWARDED = "forwarded"
    ARCHIVED = "archived"
    DELETED = "deleted"
    DRAFTED = "drafted"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class EmailAttachment(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    attachment_id: str

class EmailRecipient(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    type: str  # "to", "cc", "bcc"

class EmailThread(BaseModel):
    thread_id: str
    subject: str
    participant_emails: List[str]
    message_count: int
    last_message_date: datetime

class AIAnalysis(BaseModel):
    sentiment: str  # positive, negative, neutral
    urgency_score: float  # 0.0 to 1.0
    topics: List[str] = []
    action_required: bool = False
    suggested_actions: List[str] = []
    key_entities: List[str] = []  # People, places, organizations mentioned
    deadline_mentioned: Optional[datetime] = None
    meeting_request: bool = False
    confidence_score: float = 0.0

class EmailMetadata(BaseModel):
    provider_message_id: str
    provider_thread_id: Optional[str] = None
    labels: List[str] = []
    folder: Optional[str] = None
    importance: Optional[str] = None  # Provider-specific importance
    provider_flags: Dict[str, Any] = {}

class Email(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    provider: EmailProvider
    
    # Email content
    subject: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    sender: EmailRecipient
    recipients: List[EmailRecipient] = []
    
    # Email properties
    priority: EmailPriority = EmailPriority.NORMAL
    status: EmailStatus = EmailStatus.UNREAD
    received_at: datetime
    sent_at: Optional[datetime] = None
    
    # Thread information
    thread: Optional[EmailThread] = None
    in_reply_to: Optional[str] = None  # Message ID being replied to
    references: List[str] = []  # Related message IDs
    
    # Attachments
    attachments: List[EmailAttachment] = []
    has_attachments: bool = False
    
    # AI Processing
    ai_analysis: Optional[AIAnalysis] = None
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    classification_confidence: float = 0.0
    
    # Provider-specific metadata
    metadata: EmailMetadata
    
    # Automation flags
    auto_reply_sent: bool = False
    notification_sent: bool = False
    calendar_event_created: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class EmailDraft(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    original_email_id: Optional[str] = None  # If replying to an email
    
    # Draft content
    to: List[EmailRecipient]
    cc: List[EmailRecipient] = []
    bcc: List[EmailRecipient] = []
    subject: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    
    # Draft properties
    is_reply: bool = False
    is_forward: bool = False
    provider: EmailProvider
    
    # AI Generation info
    generated_by_ai: bool = False
    ai_confidence: float = 0.0
    user_modifications: List[str] = []  # Track what user changed
    generation_prompt: Optional[str] = None
    
    # Status
    is_sent: bool = False
    sent_at: Optional[datetime] = None
    provider_draft_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Request/Response Models
class EmailProcessingRequest(BaseModel):
    email_ids: List[str]
    force_reprocess: bool = False

class EmailResponse(BaseModel):
    id: str
    subject: str
    sender: EmailRecipient
    recipients: List[EmailRecipient]
    priority: EmailPriority
    status: EmailStatus
    received_at: datetime
    has_attachments: bool
    ai_analysis: Optional[AIAnalysis]
    processing_status: ProcessingStatus
    thread: Optional[EmailThread]

class EmailListResponse(BaseModel):
    emails: List[EmailResponse]
    total_count: int
    unread_count: int
    page: int
    limit: int

class DraftGenerationRequest(BaseModel):
    original_email_id: str
    response_type: str = "reply"  # reply, forward, new
    tone: str = "professional"
    length: str = "medium"  # brief, medium, detailed
    custom_instructions: Optional[str] = None

class DraftResponse(BaseModel):
    id: str
    to: List[EmailRecipient]
    subject: str
    body_html: str
    body_text: str
    generated_by_ai: bool
    ai_confidence: float
    created_at: datetime

class EmailSearchRequest(BaseModel):
    query: Optional[str] = None
    sender: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    priority: Optional[EmailPriority] = None
    status: Optional[EmailStatus] = None
    has_attachments: Optional[bool] = None
    page: int = 1
    limit: int = 50