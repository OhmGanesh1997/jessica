from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import Optional, List

from models.calendar import (
    CalendarEvent, EventResponse, EventCreateRequest, EventUpdateRequest,
    AvailabilityRequest, AvailabilityResponse, SmartSchedulingRequest,
    ConflictResolutionRequest, CalendarSyncStatus, EventStatus,
    SchedulingSuggestion, CalendarProvider
)
from utils.auth import get_current_user_id
from utils.database import QueryBuilder, ValidationUtils
from services.calendar_service import CalendarService
from services.credit_service import CreditService

router = APIRouter()

@router.get("/events", response_model=List[EventResponse])
async def get_calendar_events(
    request: Request,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's calendar events with date filtering"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Default date range if not provided
    if not start_date:
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = start_date + timedelta(days=30)
    
    # Build query
    query = QueryBuilder.build_calendar_query(
        user_id=current_user_id,
        start_date=start_date,
        end_date=end_date
    )
    
    # Get events
    skip = (page - 1) * limit
    events = await database.calendar_events.find(query)\
        .sort("start_datetime", 1)\
        .skip(skip)\
        .limit(limit)\
        .to_list(None)
    
    # Convert to response format
    event_responses = []
    for event in events:
        event_data = ValidationUtils.convert_objectid_to_str(event)
        event_responses.append(EventResponse(**event_data))
    
    return event_responses

@router.post("/events", response_model=EventResponse)
async def create_calendar_event(
    event_request: EventCreateRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Create a new calendar event"""
    database: AsyncIOMotorDatabase = request.app.database
    
    try:
        # Initialize calendar service
        calendar_service = CalendarService(database)
        
        # Create event
        event = await calendar_service.create_event(
            user_id=current_user_id,
            event_data=event_request
        )
        
        return EventResponse(**event.dict())
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create calendar event: {str(e)}"
        )

@router.get("/events/{event_id}", response_model=EventResponse)
async def get_calendar_event(
    event_id: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get specific calendar event"""
    database: AsyncIOMotorDatabase = request.app.database
    
    event = await database.calendar_events.find_one({
        "id": event_id,
        "user_id": current_user_id
    })
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar event not found"
        )
    
    event_data = ValidationUtils.convert_objectid_to_str(event)
    return EventResponse(**event_data)

@router.put("/events/{event_id}", response_model=EventResponse)
async def update_calendar_event(
    event_id: str,
    event_update: EventUpdateRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update calendar event"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Check if event exists
    event = await database.calendar_events.find_one({
        "id": event_id,
        "user_id": current_user_id
    })
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar event not found"
        )
    
    try:
        # Initialize calendar service
        calendar_service = CalendarService(database)
        
        # Update event
        updated_event = await calendar_service.update_event(
            user_id=current_user_id,
            event_id=event_id,
            update_data=event_update
        )
        
        return EventResponse(**updated_event.dict())
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update calendar event: {str(e)}"
        )

@router.delete("/events/{event_id}")
async def delete_calendar_event(
    event_id: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Delete calendar event"""
    database: AsyncIOMotorDatabase = request.app.database
    
    try:
        # Initialize calendar service
        calendar_service = CalendarService(database)
        
        # Delete event
        success = await calendar_service.delete_event(current_user_id, event_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Calendar event not found"
            )
        
        return {"message": "Calendar event deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete calendar event: {str(e)}"
        )

@router.post("/availability", response_model=List[AvailabilityResponse])
async def check_availability(
    availability_request: AvailabilityRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Check availability for given date range"""
    database: AsyncIOMotorDatabase = request.app.database
    
    try:
        # Initialize calendar service
        calendar_service = CalendarService(database)
        
        # Check availability
        availability = await calendar_service.check_availability(
            user_id=current_user_id,
            start_date=availability_request.start_date,
            end_date=availability_request.end_date,
            attendee_emails=availability_request.attendee_emails,
            duration_minutes=availability_request.duration_minutes,
            buffer_time_minutes=availability_request.buffer_time_minutes
        )
        
        return availability
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check availability: {str(e)}"
        )

@router.post("/smart-schedule", response_model=List[SchedulingSuggestion])
async def get_smart_scheduling_suggestions(
    scheduling_request: SmartSchedulingRequest,
    request: Request,
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
        # Initialize calendar service
        calendar_service = CalendarService(database)
        
        # Get scheduling suggestions
        suggestions = await calendar_service.get_smart_scheduling_suggestions(
            user_id=current_user_id,
            scheduling_request=scheduling_request
        )
        
        # Deduct credits
        await credit_service.deduct_credits(current_user_id, "smart_scheduling")
        
        return suggestions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate scheduling suggestions: {str(e)}"
        )

@router.post("/resolve-conflict")
async def resolve_scheduling_conflict(
    conflict_request: ConflictResolutionRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Resolve scheduling conflicts with AI suggestions"""
    database: AsyncIOMotorDatabase = request.app.database
    
    try:
        # Initialize calendar service
        calendar_service = CalendarService(database)
        
        # Resolve conflict
        resolution = await calendar_service.resolve_scheduling_conflict(
            user_id=current_user_id,
            event_id=conflict_request.event_id,
            resolution_strategy=conflict_request.resolution_strategy,
            preferred_alternatives=conflict_request.preferred_alternatives
        )
        
        return resolution
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve scheduling conflict: {str(e)}"
        )

@router.get("/conflicts")
async def get_scheduling_conflicts(
    request: Request,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get scheduling conflicts in date range"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Default date range
    if not start_date:
        start_date = datetime.utcnow()
    if not end_date:
        end_date = start_date + timedelta(days=30)
    
    try:
        # Initialize calendar service
        calendar_service = CalendarService(database)
        
        # Find conflicts
        conflicts = await calendar_service.find_scheduling_conflicts(
            user_id=current_user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return {"conflicts": conflicts}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find conflicts: {str(e)}"
        )

@router.post("/sync")
async def sync_calendar(
    request: Request,
    background_tasks: BackgroundTasks,
    provider: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """Sync calendar from external providers"""
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
            detail="No connected calendar providers found"
        )
    
    # Start sync in background
    background_tasks.add_task(
        sync_calendars_from_providers,
        database,
        current_user_id,
        providers_to_sync
    )
    
    return {
        "message": f"Calendar sync started for {', '.join(providers_to_sync)}",
        "providers": providers_to_sync
    }

@router.get("/sync-status", response_model=List[CalendarSyncStatus])
async def get_calendar_sync_status(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get calendar synchronization status"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get sync status for connected providers
    sync_statuses = await database.calendar_sync_status.find({
        "user_id": current_user_id
    }).to_list(None)
    
    status_responses = []
    for sync_status in sync_statuses:
        status_data = ValidationUtils.convert_objectid_to_str(sync_status)
        status_responses.append(CalendarSyncStatus(**status_data))
    
    return status_responses

@router.get("/upcoming")
async def get_upcoming_events(
    request: Request,
    days: int = Query(7, ge=1, le=30),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get upcoming calendar events"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Date range for upcoming events
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=days)
    
    # Get upcoming events
    events = await database.calendar_events.find({
        "user_id": current_user_id,
        "start_datetime": {"$gte": start_date, "$lte": end_date},
        "status": {"$ne": "cancelled"}
    }).sort("start_datetime", 1).to_list(None)
    
    # Group events by date
    events_by_date = {}
    for event in events:
        event_date = event["start_datetime"].date().isoformat()
        if event_date not in events_by_date:
            events_by_date[event_date] = []
        
        event_data = ValidationUtils.convert_objectid_to_str(event)
        events_by_date[event_date].append(EventResponse(**event_data))
    
    return {
        "upcoming_events": events_by_date,
        "total_events": len(events),
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    }

@router.get("/stats/summary")
async def get_calendar_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get calendar statistics and analytics"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Date range for stats
    start_date = datetime.utcnow() - timedelta(days=days)
    end_date = datetime.utcnow() + timedelta(days=30)  # Include future events
    
    # Total events count
    total_events = await database.calendar_events.count_documents({
        "user_id": current_user_id
    })
    
    # Upcoming events count
    upcoming_events = await database.calendar_events.count_documents({
        "user_id": current_user_id,
        "start_datetime": {"$gte": datetime.utcnow()},
        "status": {"$ne": "cancelled"}
    })
    
    # Events by status
    status_stats = await database.calendar_events.aggregate([
        {"$match": {"user_id": current_user_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]).to_list(None)
    
    # Meeting duration analysis
    duration_stats = await database.calendar_events.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "start_datetime": {"$gte": start_date}
            }
        },
        {
            "$addFields": {
                "duration_minutes": {
                    "$divide": [
                        {"$subtract": ["$end_datetime", "$start_datetime"]},
                        60000  # Convert milliseconds to minutes
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": None,
                "avg_duration": {"$avg": "$duration_minutes"},
                "total_meeting_time": {"$sum": "$duration_minutes"},
                "max_duration": {"$max": "$duration_minutes"},
                "min_duration": {"$min": "$duration_minutes"}
            }
        }
    ]).to_list(None)
    
    # Daily event distribution
    daily_stats = await database.calendar_events.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "start_datetime": {"$gte": start_date, "$lte": end_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$start_datetime"
                    }
                },
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]).to_list(None)
    
    # Most frequent attendees
    attendee_stats = await database.calendar_events.aggregate([
        {"$match": {"user_id": current_user_id}},
        {"$unwind": "$attendees"},
        {"$group": {"_id": "$attendees.email", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]).to_list(None)
    
    return {
        "summary": {
            "total_events": total_events,
            "upcoming_events": upcoming_events
        },
        "status_distribution": {stat["_id"]: stat["count"] for stat in status_stats},
        "duration_analysis": duration_stats[0] if duration_stats else {},
        "daily_distribution": daily_stats,
        "frequent_attendees": attendee_stats,
        "period_days": days
    }

# Background task functions
async def sync_calendars_from_providers(
    database: AsyncIOMotorDatabase,
    user_id: str,
    providers: List[str]
):
    """Background task to sync calendars from external providers"""
    try:
        calendar_service = CalendarService(database)
        
        for provider in providers:
            try:
                await calendar_service.sync_calendar_from_provider(user_id, provider)
            except Exception as e:
                print(f"Failed to sync calendar from {provider}: {e}")
                
    except Exception as e:
        print(f"Calendar sync failed: {e}")