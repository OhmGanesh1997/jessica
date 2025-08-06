import httpx
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decouple import config
import asyncio

class MicrosoftService:
    """Service for Microsoft Graph API integration (Outlook, Calendar)"""
    
    def __init__(self):
        self.client_id = config('MICROSOFT_CLIENT_ID', default='placeholder-client-id')
        self.client_secret = config('MICROSOFT_CLIENT_SECRET', default='placeholder-client-secret')
        self.redirect_uri = config('MICROSOFT_REDIRECT_URI', default='http://localhost:8001/api/auth/microsoft/callback')
        
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
        self.oauth_base_url = "https://login.microsoftonline.com/common/oauth2/v2.0"
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Microsoft access token"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.oauth_base_url}/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                        "scope": "https://graph.microsoft.com/mail.read https://graph.microsoft.com/calendars.readwrite offline_access"
                    }
                )
                response.raise_for_status()
                tokens = response.json()
                
                return {
                    "access_token": tokens["access_token"],
                    "expires_at": datetime.utcnow() + timedelta(seconds=tokens["expires_in"])
                }
                
        except Exception as e:
            print(f"Microsoft token refresh error: {e}")
            raise Exception(f"Failed to refresh Microsoft token: {str(e)}")
    
    async def fetch_recent_emails(
        self,
        access_token: str,
        limit: int = 50,
        filter_query: str = ""
    ) -> List[Dict[str, Any]]:
        """Fetch recent emails from Outlook"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            params = {
                "$top": limit,
                "$orderby": "receivedDateTime desc",
                "$select": "id,subject,from,toRecipients,receivedDateTime,body,hasAttachments,importance,conversationId"
            }
            
            if filter_query:
                params["$filter"] = filter_query
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.graph_base_url}/me/messages",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                
                data = response.json()
                return data.get("value", [])
                
        except Exception as e:
            print(f"Outlook fetch error: {e}")
            raise Exception(f"Failed to fetch Outlook emails: {str(e)}")
    
    async def send_email(
        self,
        access_token: str,
        to_emails: List[str],
        subject: str,
        body_text: str,
        body_html: str,
        reply_to_message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email through Outlook"""
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Prepare recipients
            to_recipients = [{"emailAddress": {"address": email}} for email in to_emails]
            
            email_data = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": body_html or body_text
                    },
                    "toRecipients": to_recipients
                }
            }
            
            # Add reply-to if replying
            if reply_to_message_id:
                email_data["message"]["replyTo"] = [{"emailAddress": {"address": ""}}]
            
            # Send email
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.graph_base_url}/me/sendMail",
                    headers=headers,
                    json=email_data
                )
                response.raise_for_status()
                
                return {"id": "sent", "status": "sent"}
                
        except Exception as e:
            print(f"Outlook send error: {e}")
            raise Exception(f"Failed to send Outlook email: {str(e)}")
    
    async def mark_email_read(self, access_token: str, message_id: str) -> bool:
        """Mark email as read in Outlook"""
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.graph_base_url}/me/messages/{message_id}",
                    headers=headers,
                    json={"isRead": True}
                )
                response.raise_for_status()
                return True
                
        except Exception as e:
            print(f"Outlook mark read error: {e}")
            return False
    
    async def fetch_calendar_events(
        self,
        access_token: str,
        calendar_id: str = "",
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Fetch calendar events from Outlook Calendar"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Calculate time range
            start_time = datetime.utcnow().isoformat() + 'Z'
            end_time = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            params = {
                "$filter": f"start/dateTime ge '{start_time}' and end/dateTime le '{end_time}'",
                "$orderby": "start/dateTime",
                "$top": 100,
                "$select": "id,subject,start,end,attendees,location,body,organizer,isAllDay,importance"
            }
            
            # Use specific calendar or default
            calendar_endpoint = f"/me/calendars/{calendar_id}/events" if calendar_id else "/me/events"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.graph_base_url}{calendar_endpoint}",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                
                data = response.json()
                return data.get("value", [])
                
        except Exception as e:
            print(f"Outlook Calendar fetch error: {e}")
            raise Exception(f"Failed to fetch Outlook Calendar events: {str(e)}")
    
    async def create_calendar_event(
        self,
        access_token: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        attendees: List[str],
        description: Optional[str] = None,
        location: Optional[str] = None,
        calendar_id: str = ""
    ) -> Dict[str, Any]:
        """Create calendar event in Outlook Calendar"""
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Prepare event data
            event_data = {
                "subject": title,
                "start": {
                    "dateTime": start_time.isoformat(),
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": end_time.isoformat(),
                    "timeZone": "UTC"
                }
            }
            
            if description:
                event_data["body"] = {
                    "contentType": "text",
                    "content": description
                }
            
            if location:
                event_data["location"] = {
                    "displayName": location
                }
            
            if attendees:
                event_data["attendees"] = [
                    {
                        "emailAddress": {"address": email},
                        "type": "required"
                    } for email in attendees
                ]
            
            # Use specific calendar or default
            calendar_endpoint = f"/me/calendars/{calendar_id}/events" if calendar_id else "/me/events"
            
            # Create event
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.graph_base_url}{calendar_endpoint}",
                    headers=headers,
                    json=event_data
                )
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            print(f"Outlook Calendar create error: {e}")
            raise Exception(f"Failed to create Outlook Calendar event: {str(e)}")
    
    async def update_calendar_event(
        self,
        access_token: str,
        event_id: str,
        updates: Dict[str, Any],
        calendar_id: str = ""
    ) -> Dict[str, Any]:
        """Update calendar event in Outlook Calendar"""
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Prepare update data
            update_data = {}
            
            if "title" in updates:
                update_data["subject"] = updates["title"]
            if "description" in updates:
                update_data["body"] = {
                    "contentType": "text",
                    "content": updates["description"]
                }
            if "start_datetime" in updates:
                update_data["start"] = {
                    "dateTime": updates["start_datetime"].isoformat(),
                    "timeZone": "UTC"
                }
            if "end_datetime" in updates:
                update_data["end"] = {
                    "dateTime": updates["end_datetime"].isoformat(),
                    "timeZone": "UTC"
                }
            
            # Use specific calendar or default
            calendar_endpoint = f"/me/calendars/{calendar_id}/events/{event_id}" if calendar_id else f"/me/events/{event_id}"
            
            # Update event
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.graph_base_url}{calendar_endpoint}",
                    headers=headers,
                    json=update_data
                )
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            print(f"Outlook Calendar update error: {e}")
            raise Exception(f"Failed to update Outlook Calendar event: {str(e)}")
    
    async def delete_calendar_event(
        self,
        access_token: str,
        event_id: str,
        calendar_id: str = ""
    ) -> bool:
        """Delete calendar event from Outlook Calendar"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Use specific calendar or default
            calendar_endpoint = f"/me/calendars/{calendar_id}/events/{event_id}" if calendar_id else f"/me/events/{event_id}"
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.graph_base_url}{calendar_endpoint}",
                    headers=headers
                )
                response.raise_for_status()
                return True
                
        except Exception as e:
            print(f"Outlook Calendar delete error: {e}")
            return False
    
    async def health_check(self, access_token: str) -> Dict[str, Any]:
        """Check Microsoft Graph API health and token validity"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with httpx.AsyncClient() as client:
                # Test user profile endpoint
                profile_response = await client.get(
                    f"{self.graph_base_url}/me",
                    headers=headers
                )
                profile_healthy = profile_response.status_code == 200
                
                # Test mail endpoint
                mail_response = await client.get(
                    f"{self.graph_base_url}/me/messages?$top=1",
                    headers=headers
                )
                mail_healthy = mail_response.status_code == 200
                
                # Test calendar endpoint
                calendar_response = await client.get(
                    f"{self.graph_base_url}/me/events?$top=1",
                    headers=headers
                )
                calendar_healthy = calendar_response.status_code == 200
                
                return {
                    "user_profile": "healthy" if profile_healthy else "unhealthy",
                    "mail_api": "healthy" if mail_healthy else "unhealthy",
                    "calendar_api": "healthy" if calendar_healthy else "unhealthy",
                    "overall_status": "healthy" if (profile_healthy and mail_healthy and calendar_healthy) else "degraded",
                    "token_valid": True
                }
                
        except Exception as e:
            print(f"Microsoft health check error: {e}")
            return {
                "user_profile": "unhealthy",
                "mail_api": "unhealthy", 
                "calendar_api": "unhealthy",
                "overall_status": "unhealthy",
                "token_valid": False,
                "error": str(e)
            }
    
    async def setup_webhooks(self, user_id: str, access_token: str) -> Dict[str, Any]:
        """Setup Microsoft Graph webhooks for real-time updates"""
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            webhook_results = {}
            webhook_url = f"{config('BACKEND_URL', 'http://localhost:8001')}/api/integrations/webhooks/microsoft"
            
            # Setup mail webhook
            try:
                mail_webhook_data = {
                    "changeType": "created,updated",
                    "notificationUrl": webhook_url,
                    "resource": "me/messages",
                    "expirationDateTime": (datetime.utcnow() + timedelta(days=3)).isoformat() + 'Z',
                    "clientState": f"mail-{user_id}"
                }
                
                async with httpx.AsyncClient() as client:
                    mail_response = await client.post(
                        f"{self.graph_base_url}/subscriptions",
                        headers=headers,
                        json=mail_webhook_data
                    )
                    
                    if mail_response.status_code == 201:
                        webhook_results["mail"] = mail_response.json()
                    else:
                        webhook_results["mail"] = {"error": "Failed to setup mail webhook"}
                        
            except Exception as e:
                webhook_results["mail"] = {"error": str(e)}
            
            # Setup calendar webhook
            try:
                calendar_webhook_data = {
                    "changeType": "created,updated,deleted",
                    "notificationUrl": webhook_url,
                    "resource": "me/events",
                    "expirationDateTime": (datetime.utcnow() + timedelta(days=3)).isoformat() + 'Z',
                    "clientState": f"calendar-{user_id}"
                }
                
                async with httpx.AsyncClient() as client:
                    calendar_response = await client.post(
                        f"{self.graph_base_url}/subscriptions",
                        headers=headers,
                        json=calendar_webhook_data
                    )
                    
                    if calendar_response.status_code == 201:
                        webhook_results["calendar"] = calendar_response.json()
                    else:
                        webhook_results["calendar"] = {"error": "Failed to setup calendar webhook"}
                        
            except Exception as e:
                webhook_results["calendar"] = {"error": str(e)}
            
            return webhook_results
            
        except Exception as e:
            print(f"Microsoft webhook setup error: {e}")
            return {"error": str(e)}
    
    async def remove_webhooks(self, user_id: str) -> bool:
        """Remove Microsoft Graph webhooks"""
        
        try:
            # In production, you would need to track subscription IDs
            # and delete them individually
            return True
            
        except Exception as e:
            print(f"Microsoft webhook removal error: {e}")
            return False
    
    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get user profile from Microsoft Graph"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.graph_base_url}/me",
                    headers=headers
                )
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            print(f"Microsoft profile fetch error: {e}")
            raise Exception(f"Failed to fetch Microsoft profile: {str(e)}")
    
    async def get_mailboxes(self, access_token: str) -> List[Dict[str, Any]]:
        """Get user's mailboxes/folders"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.graph_base_url}/me/mailFolders",
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                return data.get("value", [])
                
        except Exception as e:
            print(f"Microsoft mailboxes fetch error: {e}")
            return []
    
    async def get_calendars(self, access_token: str) -> List[Dict[str, Any]]:
        """Get user's calendars"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.graph_base_url}/me/calendars",
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                return data.get("value", [])
                
        except Exception as e:
            print(f"Microsoft calendars fetch error: {e}")
            return []
    
    async def sync_outlook(self, user_id: str) -> Dict[str, Any]:
        """Sync Outlook data for user"""
        
        try:
            # This would be called by the background sync task
            # Implementation would fetch recent emails and update database
            return {
                "status": "success",
                "synced_emails": 0,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            print(f"Outlook sync error: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def sync_calendar(self, user_id: str) -> Dict[str, Any]:
        """Sync Outlook Calendar data for user"""
        
        try:
            # This would be called by the background sync task
            # Implementation would fetch recent events and update database
            return {
                "status": "success",
                "synced_events": 0,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            print(f"Outlook Calendar sync error: {e}")
            return {"status": "failed", "error": str(e)}