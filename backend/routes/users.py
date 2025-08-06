from fastapi import APIRouter, Depends, HTTPException, status, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Optional, List

from models.user import (
    UserResponse, UserUpdateRequest, UserProfile, UserPreferences,
    UserActivityStats, CreditBalance
)
from utils.auth import get_current_user_id
from utils.database import ValidationUtils

router = APIRouter()

@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get current user's profile"""
    database: AsyncIOMotorDatabase = request.app.database
    
    user = await database.users.find_one({"id": current_user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(**ValidationUtils.convert_objectid_to_str(user))

@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    update_data: UserUpdateRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update user profile information"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Build update query
    update_fields = {"updated_at": datetime.utcnow()}
    
    if update_data.profile:
        # Update profile fields
        profile_dict = update_data.profile.dict(exclude_unset=True)
        for key, value in profile_dict.items():
            update_fields[f"profile.{key}"] = value
    
    if update_data.preferences:
        # Update preferences fields
        preferences_dict = update_data.preferences.dict(exclude_unset=True)
        for key, value in preferences_dict.items():
            update_fields[f"preferences.{key}"] = value
    
    # Update user in database
    result = await database.users.update_one(
        {"id": current_user_id},
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Return updated user
    updated_user = await database.users.find_one({"id": current_user_id})
    return UserResponse(**ValidationUtils.convert_objectid_to_str(updated_user))

@router.get("/activity", response_model=UserActivityStats)
async def get_user_activity_stats(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user activity statistics"""
    database: AsyncIOMotorDatabase = request.app.database
    
    user = await database.users.find_one({"id": current_user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserActivityStats(**user.get("activity", {}))

@router.get("/credits", response_model=CreditBalance)
async def get_credit_balance(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user credit balance"""
    database: AsyncIOMotorDatabase = request.app.database
    
    user = await database.users.find_one({"id": current_user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return CreditBalance(**user.get("credits", {}))

@router.post("/deactivate")
async def deactivate_account(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Deactivate user account"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Update user status
    result = await database.users.update_one(
        {"id": current_user_id},
        {
            "$set": {
                "is_active": False,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # TODO: Clean up user data, cancel subscriptions, etc.
    
    return {"message": "Account deactivated successfully"}

@router.post("/reactivate")
async def reactivate_account(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Reactivate user account"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Update user status
    result = await database.users.update_one(
        {"id": current_user_id},
        {
            "$set": {
                "is_active": True,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "Account reactivated successfully"}

@router.delete("/account")
async def delete_account(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Permanently delete user account and all associated data"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Find user first
    user = await database.users.find_one({"id": current_user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # TODO: Cancel Stripe subscription if exists
    # TODO: Revoke OAuth tokens
    
    # Delete all user data
    collections_to_clean = [
        "emails",
        "calendar_events", 
        "notifications",
        "user_guidelines",
        "email_drafts",
        "credit_transactions",
        "payments"
    ]
    
    for collection_name in collections_to_clean:
        await database[collection_name].delete_many({"user_id": current_user_id})
    
    # Finally delete the user
    await database.users.delete_one({"id": current_user_id})
    
    return {"message": "Account and all associated data deleted successfully"}

@router.get("/connections")
async def get_connection_status(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's third-party connection status"""
    database: AsyncIOMotorDatabase = request.app.database
    
    user = await database.users.find_one({"id": current_user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    connections = user.get("connections", {})
    
    # Remove sensitive token information
    safe_connections = {
        "google_connected": connections.get("google_connected", False),
        "microsoft_connected": connections.get("microsoft_connected", False),
        "connected_calendars": connections.get("connected_calendars", []),
        "connected_email_accounts": connections.get("connected_email_accounts", [])
    }
    
    return safe_connections

@router.post("/disconnect/{provider}")
async def disconnect_provider(
    provider: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Disconnect a third-party provider"""
    database: AsyncIOMotorDatabase = request.app.database
    
    if provider not in ["google", "microsoft"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider"
        )
    
    # Update fields to disconnect
    update_fields = {
        f"connections.{provider}_connected": False,
        f"connections.{provider}_access_token": None,
        f"connections.{provider}_refresh_token": None,
        f"connections.{provider}_token_expiry": None,
        "updated_at": datetime.utcnow()
    }
    
    result = await database.users.update_one(
        {"id": current_user_id},
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": f"{provider.title()} disconnected successfully"}

@router.get("/dashboard-stats")
async def get_dashboard_stats(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get comprehensive dashboard statistics for user"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get user info
    user = await database.users.find_one({"id": current_user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get email stats
    total_emails = await database.emails.count_documents({"user_id": current_user_id})
    unread_emails = await database.emails.count_documents({
        "user_id": current_user_id, 
        "status": "unread"
    })
    urgent_emails = await database.emails.count_documents({
        "user_id": current_user_id,
        "priority": "urgent",
        "status": "unread"
    })
    
    # Get calendar stats  
    upcoming_events = await database.calendar_events.count_documents({
        "user_id": current_user_id,
        "start_datetime": {"$gte": datetime.utcnow()}
    })
    
    # Get notification stats
    pending_notifications = await database.notifications.count_documents({
        "user_id": current_user_id,
        "status": "pending"
    })
    
    # Get credit balance
    credits = user.get("credits", {})
    
    return {
        "user_info": {
            "name": user.get("profile", {}).get("full_name", ""),
            "email": user.get("email", ""),
            "member_since": user.get("created_at"),
            "last_login": user.get("last_login")
        },
        "email_stats": {
            "total_emails": total_emails,
            "unread_emails": unread_emails,
            "urgent_emails": urgent_emails
        },
        "calendar_stats": {
            "upcoming_events": upcoming_events
        },
        "notification_stats": {
            "pending_notifications": pending_notifications
        },
        "credit_balance": {
            "remaining_credits": credits.get("remaining_credits", 0),
            "used_credits": credits.get("used_credits", 0),
            "total_credits": credits.get("total_credits", 0)
        },
        "connections": {
            "google_connected": user.get("connections", {}).get("google_connected", False),
            "microsoft_connected": user.get("connections", {}).get("microsoft_connected", False)
        },
        "activity": user.get("activity", {})
    }