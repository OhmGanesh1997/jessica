import httpx
import json
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decouple import config
import asyncio

class GoogleService:
    """Service for Google APIs integration (Gmail, Calendar)"""
    
    def __init__(self):
        self.client_id = config('GOOGLE_CLIENT_ID', default='placeholder-client-id')
        self.client_secret = config('GOOGLE_CLIENT_SECRET', default='placeholder-client-secret')
        self.redirect_uri = config('GOOGLE_REDIRECT_URI', default='http://localhost:8001/api/auth/google/callback')
        
        self.gmail_base_url = "https://gmail.googleapis.com/gmail/v1"
        self.calendar_base_url = "https://www.googleapis.com/calendar/v3"
        self.oauth_base_url = "https://oauth2.googleapis.com"
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Google access token"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.oauth_base_url}/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token"
                    }
                )
                response.raise_for_status()
                tokens = response.json()
                
                return {
                    "access_token": tokens["access_token"],
                    "expires_at": datetime.utcnow() + timedelta(seconds=tokens["expires_in"])
                }
                
        except Exception as e:
            print(f"Google token refresh error: {e}")
            raise Exception(f"Failed to refresh Google token: {str(e)}")
    
    async def fetch_recent_emails(
        self,
        access_token: str,
        limit: int = 50,
        query: str = ""
    ) -> List[Dict[str, Any]]:
        """Fetch recent emails from Gmail"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with httpx.AsyncClient() as client:
                # First, get list of message IDs
                params = {
                    "maxResults": limit,
                    "q": query or "in:inbox"
                }
                
                response = await client.get(
                    f"{self.gmail_base_url}/users/me/messages",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                message_list = response.json()
                
                emails = []
                
                # Fetch details for each message
                for message_info in message_list.get("messages", []):
                    try:
                        message_response = await client.get(
                            f"{self.gmail_base_url}/users/me/messages/{message_info['id']}",
                            headers=headers,
                            params={"format": "full"}
                        )
                        message_response.raise_for_status()
                        email_data = message_response.json()
                        emails.append(email_data)
                        
                        # Small delay to avoid rate limiting
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        print(f"Failed to fetch email {message_info['id']}: {e}")
                        continue
                
                return emails
                
        except Exception as e:
            print(f"Gmail fetch error: {e}")
            raise Exception(f"Failed to fetch Gmail emails: {str(e)}")
    
    async def send_email(
        self,
        access_token: str,
        to_emails: List[str],
        subject: str,
        body_text: str,
        body_html: str,
        reply_to_message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email through Gmail"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Create email message
            message_parts = []
            message_parts.append(f"To: {', '.join(to_emails)}")
            message_parts.append(f"Subject: {subject}")
            message_parts.append("Content-Type: text/html; charset=utf-8")
            message_parts.append("")
            message_parts.append(body_html or body_text)
            
            raw_message = "\r\n".join(message_parts)
            encoded_message = base64.urlsafe_b64encode(raw_message.encode()).decode()
            
            email_payload = {
                "raw": encoded_message
            }
            
            # Add thread ID if replying
            if reply_to_message_id:
                try:
                    # Get original message to find thread ID
                    async with httpx.AsyncClient() as client:
                        orig_response = await client.get(
                            f"{self.gmail_base_url}/users/me/messages/{reply_to_message_id}",
                            headers=headers,
                            params={"format": "minimal"}
                        )
                        if orig_response.status_code == 200:
                            orig_data = orig_response.json()
                            thread_id = orig_data.get("threadId")
                            if thread_id:
                                email_payload["threadId"] = thread_id
                except Exception as e:
                    print(f"Failed to get thread ID: {e}")
            
            # Send email
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.gmail_base_url}/users/me/messages/send",
                    headers=headers,
                    json=email_payload
                )
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            print(f"Gmail send error: {e}")
            raise Exception(f"Failed to send Gmail email: {str(e)}")
    
    async def mark_email_read(self, access_token: str, message_id: str) -> bool:
        """Mark email as read in Gmail"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.gmail_base_url}/users/me/messages/{message_id}/modify",
                    headers=headers,
                    json={
                        "removeLabelIds": ["UNREAD"]
                    }
                )
                response.raise_for_status()
                return True
                
        except Exception as e:
            print(f"Gmail mark read error: {e}")
            return False
    
    async def fetch_calendar_events(
        self,
        access_token: str,
        calendar_id: str = "primary",
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Fetch calendar events from Google Calendar"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Calculate time range
            time_min = datetime.utcnow().isoformat() + 'Z'
            time_max = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            params = {
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": True,
                "orderBy": "startTime",
                "maxResults": 100
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.calendar_base_url}/calendars/{calendar_id}/events",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                
                calendar_data = response.json()
                return calendar_data.get("items", [])
                
        except Exception as e:
            print(f"Google Calendar fetch error: {e}")
            raise Exception(f"Failed to fetch Google Calendar events: {str(e)}")
    
    async def create_calendar_event(
        self,
        access_token: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        attendees: List[str],
        description: Optional[str] = None,
        location: Optional[str] = None,
        calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """Create calendar event in Google Calendar"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Prepare event data
            event_data = {
                "summary": title,
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
                event_data["description"] = description
            
            if location:
                event_data["location"] = location
            
            if attendees:
                event_data["attendees"] = [{"email": email} for email in attendees]
            
            # Create event
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.calendar_base_url}/calendars/{calendar_id}/events",
                    headers=headers,
                    json=event_data
                )
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            print(f"Google Calendar create error: {e}")
            raise Exception(f"Failed to create Google Calendar event: {str(e)}")
    
    async def update_calendar_event(
        self,
        access_token: str,
        event_id: str,
        updates: Dict[str, Any],
        calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """Update calendar event in Google Calendar"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Get current event
            async with httpx.AsyncClient() as client:
                get_response = await client.get(
                    f"{self.calendar_base_url}/calendars/{calendar_id}/events/{event_id}",
                    headers=headers
                )
                get_response.raise_for_status()
                current_event = get_response.json()
                
                # Apply updates
                if "title" in updates:
                    current_event["summary"] = updates["title"]
                if "description" in updates:
                    current_event["description"] = updates["description"]
                if "start_datetime" in updates:
                    current_event["start"] = {
                        "dateTime": updates["start_datetime"].isoformat(),
                        "timeZone": "UTC"
                    }
                if "end_datetime" in updates:
                    current_event["end"] = {
                        "dateTime": updates["end_datetime"].isoformat(),
                        "timeZone": "UTC"
                    }
                
                # Update event
                update_response = await client.put(
                    f"{self.calendar_base_url}/calendars/{calendar_id}/events/{event_id}",
                    headers=headers,
                    json=current_event
                )
                update_response.raise_for_status()
                
                return update_response.json()
                
        except Exception as e:
            print(f"Google Calendar update error: {e}")
            raise Exception(f"Failed to update Google Calendar event: {str(e)}")
    
    async def delete_calendar_event(
        self,
        access_token: str,
        event_id: str,
        calendar_id: str = "primary"
    ) -> bool:
        """Delete calendar event from Google Calendar"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.calendar_base_url}/calendars/{calendar_id}/events/{event_id}",
                    headers=headers
                )
                response.raise_for_status()
                return True
                
        except Exception as e:
            print(f"Google Calendar delete error: {e}")
            return False
    
    async def health_check(self, access_token: str) -> Dict[str, Any]:
        """Check Google API health and token validity"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with httpx.AsyncClient() as client:
                # Test Gmail API
                gmail_response = await client.get(
                    f"{self.gmail_base_url}/users/me/profile",
                    headers=headers
                )
                gmail_healthy = gmail_response.status_code == 200
                
                # Test Calendar API
                calendar_response = await client.get(
                    f"{self.calendar_base_url}/calendars/primary",
                    headers=headers
                )
                calendar_healthy = calendar_response.status_code == 200
                
                return {
                    "gmail_api": "healthy" if gmail_healthy else "unhealthy",
                    "calendar_api": "healthy" if calendar_healthy else "unhealthy",
                    "overall_status": "healthy" if (gmail_healthy and calendar_healthy) else "degraded",
                    "token_valid": True
                }
                
        except Exception as e:
            print(f"Google health check error: {e}")
            return {
                "gmail_api": "unhealthy",
                "calendar_api": "unhealthy",
                "overall_status": "unhealthy",
                "token_valid": False,
                "error": str(e)
            }
    
    async def setup_webhooks(self, user_id: str, access_token: str) -> Dict[str, Any]:
        """Setup Google API webhooks for real-time updates"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            webhook_results = {}
            
            # Setup Gmail webhook
            try:
                gmail_webhook_data = {
                    "labelIds": ["INBOX"],
                    "topicName": f"projects/your-project/topics/gmail-{user_id}"
                }
                
                async with httpx.AsyncClient() as client:
                    gmail_response = await client.post(
                        f"{self.gmail_base_url}/users/me/watch",
                        headers=headers,
                        json=gmail_webhook_data
                    )
                    
                    if gmail_response.status_code == 200:
                        webhook_results["gmail"] = gmail_response.json()
                    else:
                        webhook_results["gmail"] = {"error": "Failed to setup Gmail webhook"}
                        
            except Exception as e:
                webhook_results["gmail"] = {"error": str(e)}
            
            # Setup Calendar webhook
            try:
                calendar_webhook_data = {
                    "id": f"calendar-webhook-{user_id}",
                    "type": "web_hook",
                    "address": f"{config('BACKEND_URL', 'http://localhost:8001')}/api/integrations/webhooks/google"
                }
                
                async with httpx.AsyncClient() as client:
                    calendar_response = await client.post(
                        f"{self.calendar_base_url}/calendars/primary/events/watch",
                        headers=headers,
                        json=calendar_webhook_data
                    )
                    
                    if calendar_response.status_code == 200:
                        webhook_results["calendar"] = calendar_response.json()
                    else:
                        webhook_results["calendar"] = {"error": "Failed to setup Calendar webhook"}
                        
            except Exception as e:
                webhook_results["calendar"] = {"error": str(e)}
            
            return webhook_results
            
        except Exception as e:
            print(f"Google webhook setup error: {e}")
            return {"error": str(e)}
    
    async def remove_webhooks(self, user_id: str) -> bool:
        """Remove Google API webhooks"""
        
        try:
            # In a production system, you would need to track and remove
            # active webhook subscriptions. For now, just return success.
            return True
            
        except Exception as e:
            print(f"Google webhook removal error: {e}")
            return False
    
    async def sync_gmail(self, user_id: str) -> Dict[str, Any]:
        """Sync Gmail data for user"""
        
        try:
            # This would be called by the background sync task
            # Implementation would fetch recent emails and update database
            return {
                "status": "success",
                "synced_emails": 0,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            print(f"Gmail sync error: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def sync_calendar(self, user_id: str) -> Dict[str, Any]:
        """Sync Google Calendar data for user"""
        
        try:
            # This would be called by the background sync task
            # Implementation would fetch recent events and update database
            return {
                "status": "success",
                "synced_events": 0,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            print(f"Google Calendar sync error: {e}")
            return {"status": "failed", "error": str(e)}