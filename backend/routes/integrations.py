from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Optional, List, Dict, Any

from utils.auth import get_current_user_id
from utils.database import ValidationUtils
from services.google_service import GoogleService
from services.microsoft_service import MicrosoftService
from services.openai_service import OpenAIService
from services.twilio_service import TwilioService

router = APIRouter()

@router.get("/status")
async def get_integration_status(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get status of all integrations for user"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get user's connection status
    user = await database.users.find_one({"id": current_user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    connections = user.get("connections", {})
    
    # Check each integration status
    integration_status = {
        "google": {
            "connected": connections.get("google_connected", False),
            "services": ["gmail", "calendar"],
            "last_sync": None,
            "status": "active" if connections.get("google_connected") else "disconnected"
        },
        "microsoft": {
            "connected": connections.get("microsoft_connected", False),
            "services": ["outlook", "calendar"],
            "last_sync": None,
            "status": "active" if connections.get("microsoft_connected") else "disconnected"
        },
        "openai": {
            "connected": True,  # Always available if API key is configured
            "services": ["email_analysis", "draft_generation", "smart_scheduling"],
            "status": "active"
        },
        "twilio": {
            "connected": bool(user.get("profile", {}).get("phone_number")),
            "services": ["sms", "whatsapp"],
            "status": "active" if user.get("profile", {}).get("phone_number") else "requires_phone"
        }
    }
    
    # Get sync status from database if available
    sync_statuses = await database.integration_sync_status.find({
        "user_id": current_user_id
    }).to_list(None)
    
    for sync_status in sync_statuses:
        provider = sync_status.get("provider")
        if provider in integration_status:
            integration_status[provider]["last_sync"] = sync_status.get("last_sync")
            integration_status[provider]["status"] = sync_status.get("status", "unknown")
    
    return {"integrations": integration_status}

@router.post("/google/sync")
async def sync_google_data(
    request: Request,
    background_tasks: BackgroundTasks,
    service_type: Optional[str] = None,  # "gmail", "calendar", or None for both
    current_user_id: str = Depends(get_current_user_id)
):
    """Sync data from Google services"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Check if Google is connected
    user = await database.users.find_one({"id": current_user_id})
    if not user or not user.get("connections", {}).get("google_connected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected"
        )
    
    # Determine which services to sync
    services_to_sync = []
    if service_type == "gmail":
        services_to_sync = ["gmail"]
    elif service_type == "calendar":
        services_to_sync = ["calendar"]
    else:
        services_to_sync = ["gmail", "calendar"]
    
    # Start sync in background
    background_tasks.add_task(
        sync_google_services,
        database,
        current_user_id,
        services_to_sync
    )
    
    return {
        "message": f"Google sync started for {', '.join(services_to_sync)}",
        "services": services_to_sync
    }

@router.post("/microsoft/sync")
async def sync_microsoft_data(
    request: Request,
    background_tasks: BackgroundTasks,
    service_type: Optional[str] = None,  # "outlook", "calendar", or None for both
    current_user_id: str = Depends(get_current_user_id)
):
    """Sync data from Microsoft services"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Check if Microsoft is connected
    user = await database.users.find_one({"id": current_user_id})
    if not user or not user.get("connections", {}).get("microsoft_connected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Microsoft account not connected"
        )
    
    # Determine which services to sync
    services_to_sync = []
    if service_type == "outlook":
        services_to_sync = ["outlook"]
    elif service_type == "calendar":
        services_to_sync = ["calendar"]
    else:
        services_to_sync = ["outlook", "calendar"]
    
    # Start sync in background
    background_tasks.add_task(
        sync_microsoft_services,
        database,
        current_user_id,
        services_to_sync
    )
    
    return {
        "message": f"Microsoft sync started for {', '.join(services_to_sync)}",
        "services": services_to_sync
    }

@router.post("/openai/test")
async def test_openai_integration(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Test OpenAI integration"""
    try:
        # Initialize OpenAI service
        openai_service = OpenAIService()
        
        # Test API connection
        test_response = await openai_service.test_connection()
        
        return {
            "status": "success",
            "message": "OpenAI integration is working",
            "model_info": test_response
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"OpenAI integration failed: {str(e)}"
        }

@router.post("/twilio/test")
async def test_twilio_integration(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Test Twilio integration"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get user phone number
    user = await database.users.find_one({"id": current_user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    phone_number = user.get("profile", {}).get("phone_number")
    if not phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number not configured"
        )
    
    try:
        # Initialize Twilio service
        twilio_service = TwilioService()
        
        # Test SMS
        sms_result = await twilio_service.test_sms(phone_number)
        
        # Test WhatsApp (if available)
        whatsapp_result = await twilio_service.test_whatsapp(phone_number)
        
        return {
            "status": "success",
            "message": "Twilio integration tested",
            "sms_test": sms_result,
            "whatsapp_test": whatsapp_result
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Twilio integration failed: {str(e)}"
        }

@router.get("/sync-history")
async def get_sync_history(
    request: Request,
    provider: Optional[str] = None,
    limit: int = 50,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get synchronization history for integrations"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Build query
    query = {"user_id": current_user_id}
    if provider:
        query["provider"] = provider
    
    # Get sync history
    sync_history = await database.integration_sync_logs.find(query)\
        .sort("created_at", -1)\
        .limit(limit)\
        .to_list(None)
    
    # Convert to response format
    history_items = []
    for item in sync_history:
        history_data = ValidationUtils.convert_objectid_to_str(item)
        history_items.append(history_data)
    
    return {
        "sync_history": history_items,
        "total_items": len(history_items)
    }

@router.post("/webhooks/google")
async def handle_google_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle Google API webhooks for real-time updates"""
    try:
        # Get webhook payload
        body = await request.body()
        headers = dict(request.headers)
        
        # Verify webhook authenticity (if configured)
        # This would typically involve verifying signatures
        
        # Parse the webhook data
        # Google sends different webhook formats for different services
        
        # For now, just log the webhook
        print(f"Received Google webhook: {headers.get('x-goog-channel-id', 'unknown')}")
        
        # Process webhook in background
        background_tasks.add_task(
            process_google_webhook,
            body,
            headers
        )
        
        return {"status": "received"}
        
    except Exception as e:
        print(f"Google webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )

@router.post("/webhooks/microsoft")
async def handle_microsoft_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle Microsoft Graph webhooks for real-time updates"""
    try:
        # Get webhook payload
        body = await request.body()
        headers = dict(request.headers)
        
        # Microsoft Graph webhooks include validation tokens
        validation_token = request.query_params.get("validationToken")
        if validation_token:
            # This is a subscription validation request
            return validation_token
        
        # Process webhook in background
        background_tasks.add_task(
            process_microsoft_webhook,
            body,
            headers
        )
        
        return {"status": "received"}
        
    except Exception as e:
        print(f"Microsoft webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )

@router.post("/refresh-tokens")
async def refresh_oauth_tokens(
    request: Request,
    provider: str,  # "google" or "microsoft"
    current_user_id: str = Depends(get_current_user_id)
):
    """Refresh OAuth tokens for specified provider"""
    database: AsyncIOMotorDatabase = request.app.database
    
    if provider not in ["google", "microsoft"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider"
        )
    
    # Get user
    user = await database.users.find_one({"id": current_user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    connections = user.get("connections", {})
    
    try:
        if provider == "google":
            google_service = GoogleService()
            new_tokens = await google_service.refresh_access_token(
                connections.get("google_refresh_token")
            )
            
            # Update tokens in database
            await database.users.update_one(
                {"id": current_user_id},
                {
                    "$set": {
                        "connections.google_access_token": new_tokens["access_token"],
                        "connections.google_token_expiry": new_tokens["expires_at"]
                    }
                }
            )
            
        elif provider == "microsoft":
            microsoft_service = MicrosoftService()
            new_tokens = await microsoft_service.refresh_access_token(
                connections.get("microsoft_refresh_token")
            )
            
            # Update tokens in database
            await database.users.update_one(
                {"id": current_user_id},
                {
                    "$set": {
                        "connections.microsoft_access_token": new_tokens["access_token"],
                        "connections.microsoft_token_expiry": new_tokens["expires_at"]
                    }
                }
            )
        
        return {"message": f"{provider.title()} tokens refreshed successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh {provider} tokens: {str(e)}"
        )

@router.get("/health-check")
async def integration_health_check(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Check health of all integrations"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get user
    user = await database.users.find_one({"id": current_user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    health_status = {}
    
    # Check Google integration
    if user.get("connections", {}).get("google_connected"):
        try:
            google_service = GoogleService()
            google_health = await google_service.health_check(
                user.get("connections", {}).get("google_access_token")
            )
            health_status["google"] = {"status": "healthy", "details": google_health}
        except Exception as e:
            health_status["google"] = {"status": "unhealthy", "error": str(e)}
    else:
        health_status["google"] = {"status": "disconnected"}
    
    # Check Microsoft integration
    if user.get("connections", {}).get("microsoft_connected"):
        try:
            microsoft_service = MicrosoftService()
            microsoft_health = await microsoft_service.health_check(
                user.get("connections", {}).get("microsoft_access_token")
            )
            health_status["microsoft"] = {"status": "healthy", "details": microsoft_health}
        except Exception as e:
            health_status["microsoft"] = {"status": "unhealthy", "error": str(e)}
    else:
        health_status["microsoft"] = {"status": "disconnected"}
    
    # Check OpenAI integration
    try:
        openai_service = OpenAIService()
        openai_health = await openai_service.health_check()
        health_status["openai"] = {"status": "healthy", "details": openai_health}
    except Exception as e:
        health_status["openai"] = {"status": "unhealthy", "error": str(e)}
    
    # Check Twilio integration
    try:
        twilio_service = TwilioService()
        twilio_health = await twilio_service.health_check()
        health_status["twilio"] = {"status": "healthy", "details": twilio_health}
    except Exception as e:
        health_status["twilio"] = {"status": "unhealthy", "error": str(e)}
    
    # Overall health
    all_healthy = all(
        status.get("status") in ["healthy", "disconnected"] 
        for status in health_status.values()
    )
    
    return {
        "overall_status": "healthy" if all_healthy else "degraded",
        "integrations": health_status,
        "timestamp": datetime.utcnow()
    }

@router.post("/setup-webhooks")
async def setup_integration_webhooks(
    request: Request,
    provider: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Setup webhooks for real-time integration updates"""
    database: AsyncIOMotorDatabase = request.app.database
    
    if provider not in ["google", "microsoft"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider"
        )
    
    # Get user
    user = await database.users.find_one({"id": current_user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        if provider == "google":
            google_service = GoogleService()
            webhook_result = await google_service.setup_webhooks(
                user_id=current_user_id,
                access_token=user.get("connections", {}).get("google_access_token")
            )
            
        elif provider == "microsoft":
            microsoft_service = MicrosoftService()
            webhook_result = await microsoft_service.setup_webhooks(
                user_id=current_user_id,
                access_token=user.get("connections", {}).get("microsoft_access_token")
            )
        
        return {
            "message": f"{provider.title()} webhooks setup successfully",
            "webhook_details": webhook_result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup {provider} webhooks: {str(e)}"
        )

@router.delete("/webhooks/{provider}")
async def remove_integration_webhooks(
    provider: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Remove webhooks for specified provider"""
    database: AsyncIOMotorDatabase = request.app.database
    
    if provider not in ["google", "microsoft"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider"
        )
    
    try:
        if provider == "google":
            google_service = GoogleService()
            await google_service.remove_webhooks(current_user_id)
            
        elif provider == "microsoft":
            microsoft_service = MicrosoftService()
            await microsoft_service.remove_webhooks(current_user_id)
        
        return {"message": f"{provider.title()} webhooks removed successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove {provider} webhooks: {str(e)}"
        )

# Background task functions
async def sync_google_services(
    database: AsyncIOMotorDatabase,
    user_id: str,
    services: List[str]
):
    """Background task to sync Google services"""
    try:
        google_service = GoogleService()
        
        for service in services:
            try:
                if service == "gmail":
                    await google_service.sync_gmail(user_id)
                elif service == "calendar":
                    await google_service.sync_calendar(user_id)
                    
                # Log sync success
                await database.integration_sync_logs.insert_one({
                    "user_id": user_id,
                    "provider": "google",
                    "service": service,
                    "status": "success",
                    "created_at": datetime.utcnow()
                })
                
            except Exception as e:
                print(f"Failed to sync Google {service}: {e}")
                
                # Log sync failure
                await database.integration_sync_logs.insert_one({
                    "user_id": user_id,
                    "provider": "google",
                    "service": service,
                    "status": "failed",
                    "error": str(e),
                    "created_at": datetime.utcnow()
                })
                
    except Exception as e:
        print(f"Google sync failed: {e}")

async def sync_microsoft_services(
    database: AsyncIOMotorDatabase,
    user_id: str,
    services: List[str]
):
    """Background task to sync Microsoft services"""
    try:
        microsoft_service = MicrosoftService()
        
        for service in services:
            try:
                if service == "outlook":
                    await microsoft_service.sync_outlook(user_id)
                elif service == "calendar":
                    await microsoft_service.sync_calendar(user_id)
                    
                # Log sync success
                await database.integration_sync_logs.insert_one({
                    "user_id": user_id,
                    "provider": "microsoft",
                    "service": service,
                    "status": "success",
                    "created_at": datetime.utcnow()
                })
                
            except Exception as e:
                print(f"Failed to sync Microsoft {service}: {e}")
                
                # Log sync failure
                await database.integration_sync_logs.insert_one({
                    "user_id": user_id,
                    "provider": "microsoft", 
                    "service": service,
                    "status": "failed",
                    "error": str(e),
                    "created_at": datetime.utcnow()
                })
                
    except Exception as e:
        print(f"Microsoft sync failed: {e}")

async def process_google_webhook(body: bytes, headers: Dict[str, str]):
    """Process Google webhook notification"""
    try:
        # Parse and handle Google webhook
        print(f"Processing Google webhook with headers: {headers}")
        # Implementation would depend on specific Google service webhooks
        
    except Exception as e:
        print(f"Failed to process Google webhook: {e}")

async def process_microsoft_webhook(body: bytes, headers: Dict[str, str]):
    """Process Microsoft webhook notification"""
    try:
        # Parse and handle Microsoft webhook
        print(f"Processing Microsoft webhook with headers: {headers}")
        # Implementation would depend on specific Microsoft Graph webhooks
        
    except Exception as e:
        print(f"Failed to process Microsoft webhook: {e}")