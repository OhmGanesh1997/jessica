from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import Optional, List

from models.email import (
    Email, EmailResponse, EmailListResponse, EmailSearchRequest,
    EmailDraft, DraftResponse, DraftGenerationRequest,
    EmailPriority, EmailStatus, ProcessingStatus
)
from utils.auth import get_current_user_id
from utils.database import QueryBuilder, ValidationUtils, PaginationHelper
from services.email_service import EmailService
from services.credit_service import CreditService

router = APIRouter()

@router.get("/", response_model=EmailListResponse)
async def get_emails(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[EmailStatus] = None,
    priority: Optional[EmailPriority] = None,
    unread_only: bool = False,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's emails with filtering and pagination"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Build query
    query = {"user_id": current_user_id}
    
    if status:
        query["status"] = status
    if priority:
        query["priority"] = priority
    if unread_only:
        query["status"] = "unread"
    
    # Get total count
    total_count = await database.emails.count_documents(query)
    unread_count = await database.emails.count_documents({
        "user_id": current_user_id,
        "status": "unread"
    })
    
    # Get paginated emails
    skip = (page - 1) * limit
    emails = await database.emails.find(query)\
        .sort("received_at", -1)\
        .skip(skip)\
        .limit(limit)\
        .to_list(None)
    
    # Convert to response format
    email_responses = []
    for email in emails:
        email_data = ValidationUtils.convert_objectid_to_str(email)
        email_responses.append(EmailResponse(**email_data))
    
    return EmailListResponse(
        emails=email_responses,
        total_count=total_count,
        unread_count=unread_count,
        page=page,
        limit=limit
    )

@router.post("/search", response_model=EmailListResponse)
async def search_emails(
    search_request: EmailSearchRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Search emails with advanced filtering"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Build search query
    query = QueryBuilder.build_email_search_query(
        user_id=current_user_id,
        query=search_request.query,
        sender=search_request.sender,
        date_from=search_request.date_from,
        date_to=search_request.date_to,
        priority=search_request.priority,
        status=search_request.status,
        has_attachments=search_request.has_attachments
    )
    
    # Get total count
    total_count = await database.emails.count_documents(query)
    unread_count = await database.emails.count_documents({
        "user_id": current_user_id,
        "status": "unread"
    })
    
    # Get paginated results
    skip = (search_request.page - 1) * search_request.limit
    emails = await database.emails.find(query)\
        .sort("received_at", -1)\
        .skip(skip)\
        .limit(search_request.limit)\
        .to_list(None)
    
    # Convert to response format
    email_responses = []
    for email in emails:
        email_data = ValidationUtils.convert_objectid_to_str(email)
        email_responses.append(EmailResponse(**email_data))
    
    return EmailListResponse(
        emails=email_responses,
        total_count=total_count,
        unread_count=unread_count,
        page=search_request.page,
        limit=search_request.limit
    )

@router.get("/{email_id}", response_model=EmailResponse)
async def get_email(
    email_id: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get specific email details"""
    database: AsyncIOMotorDatabase = request.app.database
    
    email = await database.emails.find_one({
        "id": email_id,
        "user_id": current_user_id
    })
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    # Mark as read if unread
    if email.get("status") == "unread":
        await database.emails.update_one(
            {"id": email_id},
            {"$set": {"status": "read", "updated_at": datetime.utcnow()}}
        )
        email["status"] = "read"
    
    email_data = ValidationUtils.convert_objectid_to_str(email)
    return EmailResponse(**email_data)

@router.patch("/{email_id}/status")
async def update_email_status(
    email_id: str,
    status: EmailStatus,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update email status"""
    database: AsyncIOMotorDatabase = request.app.database
    
    result = await database.emails.update_one(
        {"id": email_id, "user_id": current_user_id},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    return {"message": f"Email status updated to {status}"}

@router.patch("/{email_id}/priority")
async def update_email_priority(
    email_id: str,
    priority: EmailPriority,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update email priority"""
    database: AsyncIOMotorDatabase = request.app.database
    
    result = await database.emails.update_one(
        {"id": email_id, "user_id": current_user_id},
        {"$set": {"priority": priority, "updated_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    return {"message": f"Email priority updated to {priority}"}

@router.post("/{email_id}/generate-draft", response_model=DraftResponse)
async def generate_draft_for_email(
    email_id: str,
    draft_request: DraftGenerationRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Generate AI draft response for email"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get original email
    email = await database.emails.find_one({
        "id": email_id,
        "user_id": current_user_id
    })
    
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
        # Initialize email service
        email_service = EmailService(database)
        
        # Generate draft
        draft = await email_service.generate_ai_draft(
            user_id=current_user_id,
            original_email=email,
            tone=draft_request.tone,
            length=draft_request.length,
            custom_instructions=draft_request.custom_instructions
        )
        
        # Deduct credits
        await credit_service.deduct_credits(current_user_id, "draft_generation")
        
        return DraftResponse(**draft.dict())
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate draft: {str(e)}"
        )

@router.get("/drafts/", response_model=List[DraftResponse])
async def get_email_drafts(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's email drafts"""
    database: AsyncIOMotorDatabase = request.app.database
    
    skip = (page - 1) * limit
    drafts = await database.email_drafts.find({"user_id": current_user_id})\
        .sort("created_at", -1)\
        .skip(skip)\
        .limit(limit)\
        .to_list(None)
    
    draft_responses = []
    for draft in drafts:
        draft_data = ValidationUtils.convert_objectid_to_str(draft)
        draft_responses.append(DraftResponse(**draft_data))
    
    return draft_responses

@router.get("/drafts/{draft_id}", response_model=DraftResponse)
async def get_email_draft(
    draft_id: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get specific email draft"""
    database: AsyncIOMotorDatabase = request.app.database
    
    draft = await database.email_drafts.find_one({
        "id": draft_id,
        "user_id": current_user_id
    })
    
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )
    
    draft_data = ValidationUtils.convert_objectid_to_str(draft)
    return DraftResponse(**draft_data)

@router.put("/drafts/{draft_id}")
async def update_email_draft(
    draft_id: str,
    subject: Optional[str] = None,
    body_text: Optional[str] = None,
    body_html: Optional[str] = None,
    request: Request = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update email draft content"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Build update fields
    update_fields = {"updated_at": datetime.utcnow()}
    user_modifications = []
    
    if subject is not None:
        update_fields["subject"] = subject
        user_modifications.append("subject")
    
    if body_text is not None:
        update_fields["body_text"] = body_text
        user_modifications.append("body_text")
    
    if body_html is not None:
        update_fields["body_html"] = body_html
        user_modifications.append("body_html")
    
    if user_modifications:
        # Get existing modifications
        draft = await database.email_drafts.find_one({"id": draft_id})
        if draft:
            existing_mods = draft.get("user_modifications", [])
            update_fields["user_modifications"] = list(set(existing_mods + user_modifications))
    
    result = await database.email_drafts.update_one(
        {"id": draft_id, "user_id": current_user_id},
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )
    
    return {"message": "Draft updated successfully"}

@router.post("/drafts/{draft_id}/send")
async def send_email_draft(
    draft_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id)
):
    """Send email draft"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get draft
    draft = await database.email_drafts.find_one({
        "id": draft_id,
        "user_id": current_user_id
    })
    
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )
    
    if draft.get("is_sent"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft already sent"
        )
    
    try:
        # Initialize email service
        email_service = EmailService(database)
        
        # Send email through appropriate provider
        result = await email_service.send_draft_email(current_user_id, draft)
        
        # Update draft status
        await database.email_drafts.update_one(
            {"id": draft_id},
            {
                "$set": {
                    "is_sent": True,
                    "sent_at": datetime.utcnow(),
                    "provider_message_id": result.get("message_id")
                }
            }
        )
        
        # Update original email status if this is a reply
        if draft.get("original_email_id"):
            await database.emails.update_one(
                {"id": draft["original_email_id"]},
                {"$set": {"status": "replied"}}
            )
        
        return {
            "message": "Email sent successfully",
            "message_id": result.get("message_id")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )

@router.delete("/drafts/{draft_id}")
async def delete_email_draft(
    draft_id: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Delete email draft"""
    database: AsyncIOMotorDatabase = request.app.database
    
    result = await database.email_drafts.delete_one({
        "id": draft_id,
        "user_id": current_user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )
    
    return {"message": "Draft deleted successfully"}

@router.post("/sync")
async def sync_emails(
    request: Request,
    background_tasks: BackgroundTasks,
    provider: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """Sync emails from external providers"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get user's connections
    user = await database.users.find_one({"id": current_user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    connections = user.get("connections", {})
    
    # Determine which providers to sync
    providers_to_sync = []
    if provider:
        if provider == "google" and connections.get("google_connected"):
            providers_to_sync.append("google")
        elif provider == "microsoft" and connections.get("microsoft_connected"):
            providers_to_sync.append("microsoft")
    else:
        if connections.get("google_connected"):
            providers_to_sync.append("google")
        if connections.get("microsoft_connected"):
            providers_to_sync.append("microsoft")
    
    if not providers_to_sync:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No connected email providers found"
        )
    
    # Start sync in background
    background_tasks.add_task(
        sync_emails_from_providers,
        database,
        current_user_id,
        providers_to_sync
    )
    
    return {
        "message": f"Email sync started for {', '.join(providers_to_sync)}",
        "providers": providers_to_sync
    }

@router.get("/stats/summary")
async def get_email_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get email statistics and analytics"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Date range for stats
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Basic email counts
    total_emails = await database.emails.count_documents({"user_id": current_user_id})
    unread_emails = await database.emails.count_documents({
        "user_id": current_user_id,
        "status": "unread"
    })
    
    # Priority distribution
    priority_stats = await database.emails.aggregate([
        {"$match": {"user_id": current_user_id}},
        {"$group": {"_id": "$priority", "count": {"$sum": 1}}}
    ]).to_list(None)
    
    # Recent email trends
    daily_stats = await database.emails.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "received_at": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$received_at"
                    }
                },
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]).to_list(None)
    
    # Top senders
    top_senders = await database.emails.aggregate([
        {"$match": {"user_id": current_user_id}},
        {"$group": {"_id": "$sender.email", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]).to_list(None)
    
    # Processing stats
    processing_stats = await database.emails.aggregate([
        {"$match": {"user_id": current_user_id}},
        {"$group": {"_id": "$processing_status", "count": {"$sum": 1}}}
    ]).to_list(None)
    
    return {
        "summary": {
            "total_emails": total_emails,
            "unread_emails": unread_emails,
            "read_percentage": (total_emails - unread_emails) / total_emails * 100 if total_emails > 0 else 0
        },
        "priority_distribution": {stat["_id"]: stat["count"] for stat in priority_stats},
        "daily_trends": daily_stats,
        "top_senders": top_senders,
        "processing_stats": {stat["_id"]: stat["count"] for stat in processing_stats},
        "period_days": days
    }

# Background task functions
async def sync_emails_from_providers(
    database: AsyncIOMotorDatabase,
    user_id: str,
    providers: List[str]
):
    """Background task to sync emails from external providers"""
    try:
        email_service = EmailService(database)
        
        for provider in providers:
            try:
                await email_service.sync_emails_from_provider(user_id, provider)
            except Exception as e:
                print(f"Failed to sync emails from {provider}: {e}")
                
    except Exception as e:
        print(f"Email sync failed: {e}")