from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import openai
from decouple import config

from models.email import Email, AIAnalysis, EmailPriority
from models.calendar import CalendarEvent, AISchedulingAnalysis
from models.guidelines import UserGuidelines, PriorityLevel
from models.notifications import Notification, NotificationType, NotificationPriority
from utils.auth import get_current_user_id
from utils.database import ValidationUtils
from services.ai_service import AIService
from services.credit_service import CreditService

router = APIRouter()

# Initialize OpenAI
openai.api_key = config('OPENAI_API_KEY', default='placeholder-openai-api-key')

@router.post("/analyze-email")
async def analyze_email(
    email_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id)
):
    """Analyze email content using AI for classification and insights"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get email
    email = await database.emails.find_one({"id": email_id, "user_id": current_user_id})
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    # Check if already processed
    if email.get("processing_status") == "completed":
        return {"message": "Email already analyzed", "analysis": email.get("ai_analysis")}
    
    # Check credits
    credit_service = CreditService(database)
    if not await credit_service.has_sufficient_credits(current_user_id, "email_processing"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits for email analysis"
        )
    
    # Update processing status
    await database.emails.update_one(
        {"id": email_id},
        {"$set": {"processing_status": "processing"}}
    )
    
    try:
        # Get user guidelines
        guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
        
        # Initialize AI service
        ai_service = AIService()
        
        # Perform AI analysis
        analysis_result = await ai_service.analyze_email_content(
            subject=email["subject"],
            body_text=email.get("body_text", ""),
            sender_email=email["sender"]["email"],
            sender_name=email["sender"].get("name"),
            user_guidelines=guidelines
        )
        
        # Create AI analysis object
        ai_analysis = AIAnalysis(**analysis_result)
        
        # Determine priority based on analysis
        priority = EmailPriority.NORMAL
        if ai_analysis.urgency_score >= 0.8:
            priority = EmailPriority.URGENT
        elif ai_analysis.urgency_score >= 0.6:
            priority = EmailPriority.HIGH
        elif ai_analysis.urgency_score <= 0.3:
            priority = EmailPriority.LOW
        
        # Update email with analysis
        await database.emails.update_one(
            {"id": email_id},
            {
                "$set": {
                    "ai_analysis": ai_analysis.dict(),
                    "priority": priority,
                    "processing_status": "completed",
                    "processed_at": datetime.utcnow()
                }
            }
        )
        
        # Deduct credits
        await credit_service.deduct_credits(current_user_id, "email_processing")
        
        # Check if notification is needed
        if priority in [EmailPriority.URGENT, EmailPriority.HIGH] and ai_analysis.action_required:
            background_tasks.add_task(
                send_urgent_email_notification,
                database,
                current_user_id,
                email_id,
                ai_analysis.dict()
            )
        
        return {
            "message": "Email analysis completed",
            "analysis": ai_analysis.dict(),
            "priority": priority,
            "credits_used": 1
        }
        
    except Exception as e:
        # Update processing status to failed
        await database.emails.update_one(
            {"id": email_id},
            {"$set": {"processing_status": "failed"}}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze email: {str(e)}"
        )

@router.post("/generate-draft")
async def generate_email_draft(
    email_id: str,
    tone: str = "professional",
    length: str = "medium",
    custom_instructions: Optional[str] = None,
    request: Request = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """Generate AI-powered email draft response"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get original email
    email = await database.emails.find_one({"id": email_id, "user_id": current_user_id})
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    # Check credits
    credit_service = CreditService(database)
    if not await credit_service.has_sufficient_credits(current_user_id, "draft_generation"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits for draft generation"
        )
    
    try:
        # Get user guidelines and communication style
        guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
        user_profile = await database.users.find_one({"id": current_user_id})
        
        # Initialize AI service
        ai_service = AIService()
        
        # Generate draft
        draft_content = await ai_service.generate_email_draft(
            original_email=email,
            user_guidelines=guidelines,
            user_profile=user_profile,
            tone=tone,
            length=length,
            custom_instructions=custom_instructions
        )
        
        # Create draft record
        from models.email import EmailDraft, EmailRecipient
        
        draft = EmailDraft(
            user_id=current_user_id,
            original_email_id=email_id,
            to=[EmailRecipient(email=email["sender"]["email"], name=email["sender"].get("name"))],
            subject=f"Re: {email['subject']}",
            body_text=draft_content["body_text"],
            body_html=draft_content["body_html"],
            is_reply=True,
            provider=email["provider"],
            generated_by_ai=True,
            ai_confidence=draft_content["confidence"],
            generation_prompt=draft_content.get("prompt_used")
        )
        
        # Save draft
        await database.email_drafts.insert_one(draft.dict())
        
        # Deduct credits
        await credit_service.deduct_credits(current_user_id, "draft_generation")
        
        return {
            "draft_id": draft.id,
            "subject": draft.subject,
            "body_text": draft.body_text,
            "body_html": draft.body_html,
            "confidence": draft.ai_confidence,
            "credits_used": 2
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate draft: {str(e)}"
        )

@router.post("/analyze-calendar-event")
async def analyze_calendar_event(
    event_id: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Analyze calendar event for scheduling optimization"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get calendar event
    event = await database.calendar_events.find_one({"id": event_id, "user_id": current_user_id})
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar event not found"
        )
    
    # Check credits
    credit_service = CreditService(database)
    if not await credit_service.has_sufficient_credits(current_user_id, "calendar_analysis"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits for calendar analysis"
        )
    
    try:
        # Get user guidelines and preferences
        guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
        
        # Get user's other calendar events for context
        user_events = await database.calendar_events.find({
            "user_id": current_user_id,
            "start_datetime": {
                "$gte": datetime.utcnow(),
                "$lte": event["end_datetime"]
            }
        }).to_list(None)
        
        # Initialize AI service
        ai_service = AIService()
        
        # Perform scheduling analysis
        analysis_result = await ai_service.analyze_calendar_event(
            event=event,
            context_events=user_events,
            user_guidelines=guidelines
        )
        
        # Create scheduling analysis object
        scheduling_analysis = AISchedulingAnalysis(**analysis_result)
        
        # Update event with analysis
        await database.calendar_events.update_one(
            {"id": event_id},
            {
                "$set": {
                    "ai_analysis": scheduling_analysis.dict(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Deduct credits
        await credit_service.deduct_credits(current_user_id, "calendar_analysis")
        
        return {
            "message": "Calendar event analysis completed",
            "analysis": scheduling_analysis.dict(),
            "credits_used": 1
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze calendar event: {str(e)}"
        )

@router.post("/smart-scheduling")
async def smart_scheduling_suggestions(
    title: str,
    duration_minutes: int,
    attendee_emails: List[str],
    preferred_times: Optional[List[str]] = None,
    date_range_days: int = 7,
    request: Request = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get AI-powered scheduling suggestions"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Check credits
    credit_service = CreditService(database)
    if not await credit_service.has_sufficient_credits(current_user_id, "smart_scheduling"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits for smart scheduling"
        )
    
    try:
        # Get user's calendar events and preferences
        start_date = datetime.utcnow()
        end_date = datetime.utcnow().replace(hour=23, minute=59) + timedelta(days=date_range_days)
        
        user_events = await database.calendar_events.find({
            "user_id": current_user_id,
            "start_datetime": {"$gte": start_date},
            "end_datetime": {"$lte": end_date}
        }).to_list(None)
        
        # Get user guidelines
        guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
        
        # Initialize AI service
        ai_service = AIService()
        
        # Generate scheduling suggestions
        suggestions = await ai_service.generate_scheduling_suggestions(
            title=title,
            duration_minutes=duration_minutes,
            attendee_emails=attendee_emails,
            existing_events=user_events,
            user_guidelines=guidelines,
            preferred_times=preferred_times,
            date_range_start=start_date,
            date_range_end=end_date
        )
        
        # Deduct credits
        await credit_service.deduct_credits(current_user_id, "smart_scheduling")
        
        return {
            "suggestions": suggestions,
            "credits_used": 1
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate scheduling suggestions: {str(e)}"
        )

@router.post("/process-inbox")
async def process_inbox_batch(
    background_tasks: BackgroundTasks,
    force_reprocess: bool = False,
    limit: int = 50,
    request: Request = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """Process a batch of emails in user's inbox with AI"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get unprocessed emails
    query = {"user_id": current_user_id}
    if not force_reprocess:
        query["processing_status"] = {"$in": ["pending", "failed"]}
    
    emails = await database.emails.find(query).limit(limit).to_list(None)
    
    if not emails:
        return {"message": "No emails to process", "processed_count": 0}
    
    # Check credits for batch processing
    credit_service = CreditService(database)
    total_credits_needed = len(emails)
    
    user = await database.users.find_one({"id": current_user_id})
    remaining_credits = user.get("credits", {}).get("remaining_credits", 0)
    
    if remaining_credits < total_credits_needed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Need {total_credits_needed}, have {remaining_credits}"
        )
    
    # Process emails in background
    background_tasks.add_task(
        process_emails_batch,
        database,
        current_user_id,
        [email["id"] for email in emails]
    )
    
    return {
        "message": f"Processing {len(emails)} emails",
        "processing_count": len(emails),
        "estimated_credits": total_credits_needed
    }

@router.get("/processing-status")
async def get_processing_status(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get AI processing status for user's emails and events"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Email processing stats
    email_stats = await database.emails.aggregate([
        {"$match": {"user_id": current_user_id}},
        {"$group": {
            "_id": "$processing_status",
            "count": {"$sum": 1}
        }}
    ]).to_list(None)
    
    # Calendar events with AI analysis
    calendar_stats = await database.calendar_events.aggregate([
        {"$match": {"user_id": current_user_id}},
        {"$group": {
            "_id": {"$cond": [{"$exists": ["$ai_analysis", True]}, "analyzed", "not_analyzed"]},
            "count": {"$sum": 1}
        }}
    ]).to_list(None)
    
    # Recent AI activities
    recent_activities = await database.emails.find(
        {
            "user_id": current_user_id,
            "processing_status": "completed",
            "processed_at": {"$exists": True}
        },
        {"subject": 1, "processed_at": 1, "ai_analysis.urgency_score": 1, "priority": 1}
    ).sort("processed_at", -1).limit(10).to_list(None)
    
    return {
        "email_processing_stats": {stat["_id"]: stat["count"] for stat in email_stats},
        "calendar_analysis_stats": {stat["_id"]: stat["count"] for stat in calendar_stats},
        "recent_activities": recent_activities,
        "total_processed": sum(stat["count"] for stat in email_stats if stat["_id"] == "completed")
    }

# Background task functions
async def send_urgent_email_notification(
    database: AsyncIOMotorDatabase,
    user_id: str,
    email_id: str,
    ai_analysis: Dict[str, Any]
):
    """Send urgent email notification"""
    try:
        from services.notification_service import NotificationService
        
        notification_service = NotificationService(database)
        
        # Get email details
        email = await database.emails.find_one({"id": email_id})
        
        await notification_service.send_urgent_email_notification(
            user_id=user_id,
            email=email,
            ai_analysis=ai_analysis
        )
    except Exception as e:
        print(f"Failed to send urgent email notification: {e}")

async def process_emails_batch(
    database: AsyncIOMotorDatabase,
    user_id: str,
    email_ids: List[str]
):
    """Background task to process a batch of emails"""
    try:
        ai_service = AIService()
        credit_service = CreditService(database)
        
        # Get user guidelines
        guidelines = await database.user_guidelines.find_one({"user_id": user_id})
        
        for email_id in email_ids:
            try:
                # Get email
                email = await database.emails.find_one({"id": email_id})
                if not email:
                    continue
                
                # Update processing status
                await database.emails.update_one(
                    {"id": email_id},
                    {"$set": {"processing_status": "processing"}}
                )
                
                # Analyze email
                analysis_result = await ai_service.analyze_email_content(
                    subject=email["subject"],
                    body_text=email.get("body_text", ""),
                    sender_email=email["sender"]["email"],
                    sender_name=email["sender"].get("name"),
                    user_guidelines=guidelines
                )
                
                # Determine priority
                priority = EmailPriority.NORMAL
                urgency_score = analysis_result.get("urgency_score", 0.5)
                if urgency_score >= 0.8:
                    priority = EmailPriority.URGENT
                elif urgency_score >= 0.6:
                    priority = EmailPriority.HIGH
                elif urgency_score <= 0.3:
                    priority = EmailPriority.LOW
                
                # Update email
                await database.emails.update_one(
                    {"id": email_id},
                    {
                        "$set": {
                            "ai_analysis": analysis_result,
                            "priority": priority,
                            "processing_status": "completed",
                            "processed_at": datetime.utcnow()
                        }
                    }
                )
                
                # Deduct credits
                await credit_service.deduct_credits(user_id, "email_processing")
                
            except Exception as e:
                print(f"Failed to process email {email_id}: {e}")
                await database.emails.update_one(
                    {"id": email_id},
                    {"$set": {"processing_status": "failed"}}
                )
                
    except Exception as e:
        print(f"Failed to process email batch: {e}")

@router.post("/train-model")
async def train_personalization_model(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Train user-specific AI model based on feedback and behavior"""
    database: AsyncIOMotorDatabase = request.app.database
    
    try:
        # Get user's feedback data
        feedback_data = await database.guideline_feedback.find(
            {"user_id": current_user_id}
        ).to_list(None)
        
        # Get user's email interactions
        email_interactions = await database.emails.find(
            {
                "user_id": current_user_id,
                "processing_status": "completed"
            }
        ).to_list(None)
        
        # Initialize AI service
        ai_service = AIService()
        
        # Train personalization model
        training_result = await ai_service.train_user_model(
            user_id=current_user_id,
            feedback_data=feedback_data,
            email_interactions=email_interactions
        )
        
        # Update user's learning timestamp
        await database.user_guidelines.update_one(
            {"user_id": current_user_id},
            {"$set": {"last_learning_update": datetime.utcnow()}}
        )
        
        return {
            "message": "Model training completed",
            "training_stats": training_result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to train model: {str(e)}"
        )