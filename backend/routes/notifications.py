from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import Optional, List

from models.notifications import (
    Notification, NotificationResponse, NotificationListResponse,
    SendNotificationRequest, NotificationPreferencesResponse,
    UpdateNotificationPreferencesRequest, NotificationStatsResponse,
    NotificationChannel, NotificationType, NotificationPriority,
    NotificationStatus, UserNotificationPreferences
)
from utils.auth import get_current_user_id
from utils.database import QueryBuilder, ValidationUtils
from services.notification_service import NotificationService
from services.twilio_service import TwilioService

router = APIRouter()

@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[NotificationStatus] = None,
    type: Optional[NotificationType] = None,
    unread_only: bool = False,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's notifications with filtering and pagination"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Build query
    query = {"user_id": current_user_id}
    
    if status:
        query["status"] = status
    if type:
        query["type"] = type
    if unread_only:
        query["read_at"] = {"$exists": False}
    
    # Get total count
    total_count = await database.notifications.count_documents(query)
    unread_count = await database.notifications.count_documents({
        "user_id": current_user_id,
        "read_at": {"$exists": False}
    })
    
    # Get paginated notifications
    skip = (page - 1) * limit
    notifications = await database.notifications.find(query)\
        .sort("created_at", -1)\
        .skip(skip)\
        .limit(limit)\
        .to_list(None)
    
    # Convert to response format
    notification_responses = []
    for notification in notifications:
        notification_data = ValidationUtils.convert_objectid_to_str(notification)
        notification_responses.append(NotificationResponse(**notification_data))
    
    return NotificationListResponse(
        notifications=notification_responses,
        total_count=total_count,
        unread_count=unread_count,
        page=page,
        limit=limit
    )

@router.post("/send", response_model=NotificationResponse)
async def send_notification(
    send_request: SendNotificationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id)
):
    """Send a notification to user"""
    database: AsyncIOMotorDatabase = request.app.database
    
    try:
        # Initialize notification service
        notification_service = NotificationService(database)
        
        # Send notification
        notification = await notification_service.send_notification(
            user_id=send_request.user_id or current_user_id,
            notification_type=send_request.type,
            title=send_request.title,
            message=send_request.message,
            channels=send_request.channels,
            priority=send_request.priority,
            scheduled_at=send_request.scheduled_at,
            metadata=send_request.metadata,
            related_email_id=send_request.related_email_id,
            related_event_id=send_request.related_event_id
        )
        
        return NotificationResponse(**notification.dict())
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}"
        )

@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get specific notification"""
    database: AsyncIOMotorDatabase = request.app.database
    
    notification = await database.notifications.find_one({
        "id": notification_id,
        "user_id": current_user_id
    })
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # Mark as read if unread
    if not notification.get("read_at"):
        await database.notifications.update_one(
            {"id": notification_id},
            {"$set": {"read_at": datetime.utcnow()}}
        )
        notification["read_at"] = datetime.utcnow()
    
    notification_data = ValidationUtils.convert_objectid_to_str(notification)
    return NotificationResponse(**notification_data)

@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Mark notification as read"""
    database: AsyncIOMotorDatabase = request.app.database
    
    result = await database.notifications.update_one(
        {"id": notification_id, "user_id": current_user_id},
        {"$set": {"read_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {"message": "Notification marked as read"}

@router.patch("/mark-all-read")
async def mark_all_notifications_read(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Mark all notifications as read"""
    database: AsyncIOMotorDatabase = request.app.database
    
    result = await database.notifications.update_many(
        {
            "user_id": current_user_id,
            "read_at": {"$exists": False}
        },
        {"$set": {"read_at": datetime.utcnow()}}
    )
    
    return {"message": f"Marked {result.modified_count} notifications as read"}

@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Delete notification"""
    database: AsyncIOMotorDatabase = request.app.database
    
    result = await database.notifications.delete_one({
        "id": notification_id,
        "user_id": current_user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {"message": "Notification deleted successfully"}

@router.get("/preferences/", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's notification preferences"""
    database: AsyncIOMotorDatabase = request.app.database
    
    preferences = await database.notification_preferences.find_one({
        "user_id": current_user_id
    })
    
    if not preferences:
        # Create default preferences
        default_prefs = UserNotificationPreferences(user_id=current_user_id)
        await database.notification_preferences.insert_one(default_prefs.dict())
        preferences = default_prefs.dict()
    
    preferences_data = ValidationUtils.convert_objectid_to_str(preferences)
    return NotificationPreferencesResponse(**preferences_data)

@router.put("/preferences/", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    preferences_update: UpdateNotificationPreferencesRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update user's notification preferences"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Build update fields
    update_fields = {"updated_at": datetime.utcnow()}
    
    if preferences_update.channel_preferences is not None:
        update_fields["channel_preferences"] = preferences_update.channel_preferences
    
    if preferences_update.quiet_hours_enabled is not None:
        update_fields["quiet_hours_enabled"] = preferences_update.quiet_hours_enabled
    
    if preferences_update.quiet_hours_start is not None:
        update_fields["quiet_hours_start"] = preferences_update.quiet_hours_start
    
    if preferences_update.quiet_hours_end is not None:
        update_fields["quiet_hours_end"] = preferences_update.quiet_hours_end
    
    if preferences_update.max_notifications_per_hour is not None:
        update_fields["max_notifications_per_hour"] = preferences_update.max_notifications_per_hour
    
    if preferences_update.urgent_override_quiet_hours is not None:
        update_fields["urgent_override_quiet_hours"] = preferences_update.urgent_override_quiet_hours
    
    if preferences_update.enable_batching is not None:
        update_fields["enable_batching"] = preferences_update.enable_batching
    
    if preferences_update.preferred_language is not None:
        update_fields["preferred_language"] = preferences_update.preferred_language
    
    if preferences_update.timezone is not None:
        update_fields["timezone"] = preferences_update.timezone
    
    # Update preferences
    await database.notification_preferences.update_one(
        {"user_id": current_user_id},
        {"$set": update_fields},
        upsert=True
    )
    
    # Get updated preferences
    updated_preferences = await database.notification_preferences.find_one({
        "user_id": current_user_id
    })
    
    preferences_data = ValidationUtils.convert_objectid_to_str(updated_preferences)
    return NotificationPreferencesResponse(**preferences_data)

@router.post("/test")
async def send_test_notification(
    channel: NotificationChannel,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id)
):
    """Send test notification to verify settings"""
    database: AsyncIOMotorDatabase = request.app.database
    
    try:
        # Initialize notification service
        notification_service = NotificationService(database)
        
        # Send test notification
        test_message = f"This is a test notification via {channel.value}"
        
        notification = await notification_service.send_notification(
            user_id=current_user_id,
            notification_type=NotificationType.SYSTEM_UPDATE,
            title="Test Notification",
            message=test_message,
            channels=[channel],
            priority=NotificationPriority.NORMAL
        )
        
        return {
            "message": f"Test notification sent via {channel.value}",
            "notification_id": notification.id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test notification: {str(e)}"
        )

@router.get("/stats/", response_model=NotificationStatsResponse)
async def get_notification_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get notification statistics"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Date range for stats
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total counts
    total_sent = await database.notifications.count_documents({
        "user_id": current_user_id,
        "status": "sent"
    })
    
    total_delivered = await database.notifications.count_documents({
        "user_id": current_user_id,
        "status": "delivered"
    })
    
    total_failed = await database.notifications.count_documents({
        "user_id": current_user_id,
        "status": "failed"
    })
    
    # Channel stats
    channel_stats = {}
    for channel in NotificationChannel:
        channel_data = await database.notifications.aggregate([
            {
                "$match": {
                    "user_id": current_user_id,
                    "preferred_channels": channel.value,
                    "created_at": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]).to_list(None)
        
        channel_stats[channel] = {stat["_id"]: stat["count"] for stat in channel_data}
    
    # Type stats
    type_stats = {}
    for notification_type in NotificationType:
        type_data = await database.notifications.aggregate([
            {
                "$match": {
                    "user_id": current_user_id,
                    "type": notification_type.value,
                    "created_at": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]).to_list(None)
        
        type_stats[notification_type] = {stat["_id"]: stat["count"] for stat in type_data}
    
    # Recent activity
    recent_notifications = await database.notifications.find(
        {
            "user_id": current_user_id,
            "created_at": {"$gte": start_date}
        }
    ).sort("created_at", -1).limit(10).to_list(None)
    
    recent_activity = []
    for notification in recent_notifications:
        notification_data = ValidationUtils.convert_objectid_to_str(notification)
        recent_activity.append(NotificationResponse(**notification_data))
    
    return NotificationStatsResponse(
        total_sent=total_sent,
        total_delivered=total_delivered,
        total_failed=total_failed,
        channel_stats=channel_stats,
        type_stats=type_stats,
        recent_activity=recent_activity
    )

@router.get("/pending/")
async def get_pending_notifications(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get pending notifications that haven't been sent yet"""
    database: AsyncIOMotorDatabase = request.app.database
    
    pending_notifications = await database.notifications.find({
        "user_id": current_user_id,
        "status": "pending",
        "scheduled_at": {"$lte": datetime.utcnow()}
    }).sort("scheduled_at", 1).to_list(None)
    
    notification_responses = []
    for notification in pending_notifications:
        notification_data = ValidationUtils.convert_objectid_to_str(notification)
        notification_responses.append(NotificationResponse(**notification_data))
    
    return {
        "pending_notifications": notification_responses,
        "count": len(notification_responses)
    }

@router.post("/process-pending")
async def process_pending_notifications(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id)
):
    """Process pending notifications for user"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get pending notifications
    pending_notifications = await database.notifications.find({
        "user_id": current_user_id,
        "status": "pending",
        "scheduled_at": {"$lte": datetime.utcnow()}
    }).to_list(None)
    
    if not pending_notifications:
        return {"message": "No pending notifications to process", "count": 0}
    
    # Process in background
    background_tasks.add_task(
        process_notifications_batch,
        database,
        [notification["id"] for notification in pending_notifications]
    )
    
    return {
        "message": f"Processing {len(pending_notifications)} pending notifications",
        "count": len(pending_notifications)
    }

@router.get("/channels/test")
async def test_notification_channels(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Test all configured notification channels"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get user info
    user = await database.users.find_one({"id": current_user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Test results
    test_results = {}
    
    # Test email (always available)
    test_results["email"] = {"available": True, "configured": True}
    
    # Test SMS
    phone_number = user.get("profile", {}).get("phone_number")
    test_results["sms"] = {
        "available": bool(phone_number),
        "configured": bool(phone_number)
    }
    
    # Test WhatsApp (same as SMS for now)
    test_results["whatsapp"] = {
        "available": bool(phone_number),
        "configured": bool(phone_number)
    }
    
    return {
        "channels": test_results,
        "user_phone": phone_number is not None
    }

# Background task functions
async def process_notifications_batch(
    database: AsyncIOMotorDatabase,
    notification_ids: List[str]
):
    """Background task to process a batch of notifications"""
    try:
        notification_service = NotificationService(database)
        
        for notification_id in notification_ids:
            try:
                await notification_service.process_notification(notification_id)
            except Exception as e:
                print(f"Failed to process notification {notification_id}: {e}")
                
    except Exception as e:
        print(f"Notification batch processing failed: {e}")