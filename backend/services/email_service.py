import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.email import Email, EmailDraft, EmailRecipient, EmailProvider
from services.ai_service import AIService
from services.google_service import GoogleService
from services.microsoft_service import MicrosoftService

class EmailService:
    """Service for email management and processing"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.ai_service = AIService()
        self.google_service = GoogleService()
        self.microsoft_service = MicrosoftService()
    
    async def sync_emails_from_provider(self, user_id: str, provider: str) -> Dict[str, Any]:
        """Sync emails from external provider"""
        
        try:
            # Get user's connection info
            user = await self.db.users.find_one({"id": user_id})
            if not user:
                raise Exception(f"User {user_id} not found")
            
            connections = user.get("connections", {})
            sync_result = {"synced_count": 0, "errors": []}
            
            if provider == "google" and connections.get("google_connected"):
                access_token = connections.get("google_access_token")
                if not access_token:
                    raise Exception("Google access token not found")
                
                # Fetch emails from Gmail
                gmail_emails = await self.google_service.fetch_recent_emails(
                    access_token, limit=50
                )
                
                # Process and store emails
                for gmail_email in gmail_emails:
                    try:
                        email = await self._convert_gmail_to_email(user_id, gmail_email)
                        await self._store_email_if_new(email)
                        sync_result["synced_count"] += 1
                    except Exception as e:
                        sync_result["errors"].append(f"Failed to process email: {str(e)}")
            
            elif provider == "microsoft" and connections.get("microsoft_connected"):
                access_token = connections.get("microsoft_access_token")
                if not access_token:
                    raise Exception("Microsoft access token not found")
                
                # Fetch emails from Outlook
                outlook_emails = await self.microsoft_service.fetch_recent_emails(
                    access_token, limit=50
                )
                
                # Process and store emails
                for outlook_email in outlook_emails:
                    try:
                        email = await self._convert_outlook_to_email(user_id, outlook_email)
                        await self._store_email_if_new(email)
                        sync_result["synced_count"] += 1
                    except Exception as e:
                        sync_result["errors"].append(f"Failed to process email: {str(e)}")
            
            else:
                raise Exception(f"Provider {provider} not connected or not supported")
            
            return sync_result
            
        except Exception as e:
            print(f"Email sync error for {provider}: {e}")
            return {"synced_count": 0, "errors": [str(e)]}
    
    async def generate_ai_draft(
        self,
        user_id: str,
        original_email: Dict[str, Any],
        tone: str = "professional",
        length: str = "medium",
        custom_instructions: Optional[str] = None
    ) -> EmailDraft:
        """Generate AI-powered email draft"""
        
        try:
            # Get user guidelines and profile
            guidelines = await self.db.user_guidelines.find_one({"user_id": user_id})
            user_profile = await self.db.users.find_one({"id": user_id})
            
            # Generate draft using AI service
            draft_content = await self.ai_service.generate_email_draft(
                original_email=original_email,
                user_guidelines=guidelines,
                user_profile=user_profile,
                tone=tone,
                length=length,
                custom_instructions=custom_instructions
            )
            
            # Create draft object
            draft = EmailDraft(
                user_id=user_id,
                original_email_id=original_email["id"],
                to=[EmailRecipient(
                    email=original_email["sender"]["email"],
                    name=original_email["sender"].get("name")
                )],
                subject=f"Re: {original_email['subject']}",
                body_text=draft_content["body_text"],
                body_html=draft_content["body_html"],
                is_reply=True,
                provider=original_email["provider"],
                generated_by_ai=True,
                ai_confidence=draft_content["confidence"],
                generation_prompt=draft_content.get("prompt_used")
            )
            
            # Save draft to database
            await self.db.email_drafts.insert_one(draft.dict())
            
            return draft
            
        except Exception as e:
            print(f"Draft generation error: {e}")
            raise Exception(f"Failed to generate draft: {str(e)}")
    
    async def send_draft_email(
        self,
        user_id: str,
        draft: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send email draft through appropriate provider"""
        
        try:
            # Get user's connection info
            user = await self.db.users.find_one({"id": user_id})
            if not user:
                raise Exception(f"User {user_id} not found")
            
            connections = user.get("connections", {})
            provider = draft["provider"]
            
            if provider == "gmail" and connections.get("google_connected"):
                access_token = connections.get("google_access_token")
                if not access_token:
                    raise Exception("Google access token not found")
                
                # Send through Gmail
                result = await self.google_service.send_email(
                    access_token=access_token,
                    to_emails=[recipient["email"] for recipient in draft["to"]],
                    subject=draft["subject"],
                    body_text=draft["body_text"],
                    body_html=draft["body_html"],
                    reply_to_message_id=draft.get("original_email_id")
                )
                
                return {"message_id": result.get("id"), "provider": "gmail"}
            
            elif provider == "outlook" and connections.get("microsoft_connected"):
                access_token = connections.get("microsoft_access_token")
                if not access_token:
                    raise Exception("Microsoft access token not found")
                
                # Send through Outlook
                result = await self.microsoft_service.send_email(
                    access_token=access_token,
                    to_emails=[recipient["email"] for recipient in draft["to"]],
                    subject=draft["subject"],
                    body_text=draft["body_text"],
                    body_html=draft["body_html"],
                    reply_to_message_id=draft.get("original_email_id")
                )
                
                return {"message_id": result.get("id"), "provider": "outlook"}
            
            else:
                raise Exception(f"Provider {provider} not connected or not supported")
            
        except Exception as e:
            print(f"Email sending error: {e}")
            raise Exception(f"Failed to send email: {str(e)}")
    
    async def process_email_with_ai(
        self,
        user_id: str,
        email_id: str
    ) -> Dict[str, Any]:
        """Process single email with AI analysis"""
        
        try:
            # Get email
            email = await self.db.emails.find_one({"id": email_id, "user_id": user_id})
            if not email:
                raise Exception(f"Email {email_id} not found")
            
            # Get user guidelines
            guidelines = await self.db.user_guidelines.find_one({"user_id": user_id})
            
            # Analyze email with AI
            analysis = await self.ai_service.analyze_email_content(
                subject=email["subject"],
                body_text=email.get("body_text", ""),
                sender_email=email["sender"]["email"],
                sender_name=email["sender"].get("name"),
                user_guidelines=guidelines
            )
            
            # Determine priority based on analysis
            priority = "normal"
            urgency_score = analysis.get("urgency_score", 0.5)
            if urgency_score >= 0.8:
                priority = "urgent"
            elif urgency_score >= 0.6:
                priority = "high"
            elif urgency_score <= 0.3:
                priority = "low"
            
            # Update email with analysis
            await self.db.emails.update_one(
                {"id": email_id},
                {
                    "$set": {
                        "ai_analysis": analysis,
                        "priority": priority,
                        "processing_status": "completed",
                        "processed_at": datetime.utcnow()
                    }
                }
            )
            
            return {"status": "completed", "priority": priority, "analysis": analysis}
            
        except Exception as e:
            print(f"Email processing error: {e}")
            # Update status to failed
            await self.db.emails.update_one(
                {"id": email_id},
                {"$set": {"processing_status": "failed"}}
            )
            raise Exception(f"Failed to process email: {str(e)}")
    
    async def _convert_gmail_to_email(self, user_id: str, gmail_data: Dict[str, Any]) -> Email:
        """Convert Gmail API response to Email object"""
        
        try:
            # Extract email data from Gmail format
            headers = {h["name"]: h["value"] for h in gmail_data.get("payload", {}).get("headers", [])}
            
            # Extract body
            body_text = ""
            body_html = ""
            payload = gmail_data.get("payload", {})
            
            if payload.get("body", {}).get("data"):
                import base64
                body_text = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
            elif payload.get("parts"):
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                        body_text = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    elif part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                        body_html = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            
            # Parse sender
            sender_header = headers.get("From", "")
            sender_email = sender_header.split("<")[-1].replace(">", "").strip()
            sender_name = sender_header.split("<")[0].strip().strip('"') if "<" in sender_header else None
            
            # Parse recipients
            recipients = []
            for field in ["To", "Cc", "Bcc"]:
                if field in headers:
                    # Simple parsing - would need more robust parsing in production
                    emails = headers[field].split(",")
                    for email_str in emails:
                        email_addr = email_str.split("<")[-1].replace(">", "").strip()
                        recipients.append(EmailRecipient(
                            email=email_addr,
                            name=email_str.split("<")[0].strip() if "<" in email_str else None,
                            type=field.lower()
                        ))
            
            # Create email object
            email = Email(
                user_id=user_id,
                provider=EmailProvider.GMAIL,
                subject=headers.get("Subject", ""),
                body_text=body_text,
                body_html=body_html,
                sender=EmailRecipient(email=sender_email, name=sender_name),
                recipients=recipients,
                received_at=datetime.fromtimestamp(int(gmail_data["internalDate"]) / 1000),
                metadata={
                    "provider_message_id": gmail_data["id"],
                    "provider_thread_id": gmail_data.get("threadId"),
                    "labels": gmail_data.get("labelIds", [])
                }
            )
            
            return email
            
        except Exception as e:
            print(f"Gmail conversion error: {e}")
            raise Exception(f"Failed to convert Gmail data: {str(e)}")
    
    async def _convert_outlook_to_email(self, user_id: str, outlook_data: Dict[str, Any]) -> Email:
        """Convert Outlook API response to Email object"""
        
        try:
            # Parse sender
            sender_info = outlook_data.get("from", {}).get("emailAddress", {})
            sender = EmailRecipient(
                email=sender_info.get("address", ""),
                name=sender_info.get("name")
            )
            
            # Parse recipients
            recipients = []
            for field, type_name in [("toRecipients", "to"), ("ccRecipients", "cc"), ("bccRecipients", "bcc")]:
                for recipient in outlook_data.get(field, []):
                    email_addr = recipient.get("emailAddress", {})
                    recipients.append(EmailRecipient(
                        email=email_addr.get("address", ""),
                        name=email_addr.get("name"),
                        type=type_name
                    ))
            
            # Parse date
            received_at = datetime.fromisoformat(outlook_data["receivedDateTime"].replace("Z", "+00:00"))
            
            # Create email object
            email = Email(
                user_id=user_id,
                provider=EmailProvider.OUTLOOK,
                subject=outlook_data.get("subject", ""),
                body_text=outlook_data.get("body", {}).get("content", "") if outlook_data.get("body", {}).get("contentType") == "text" else "",
                body_html=outlook_data.get("body", {}).get("content", "") if outlook_data.get("body", {}).get("contentType") == "html" else "",
                sender=sender,
                recipients=recipients,
                received_at=received_at,
                has_attachments=outlook_data.get("hasAttachments", False),
                metadata={
                    "provider_message_id": outlook_data["id"],
                    "provider_thread_id": outlook_data.get("conversationId"),
                    "importance": outlook_data.get("importance", "normal"),
                    "categories": outlook_data.get("categories", [])
                }
            )
            
            return email
            
        except Exception as e:
            print(f"Outlook conversion error: {e}")
            raise Exception(f"Failed to convert Outlook data: {str(e)}")
    
    async def _store_email_if_new(self, email: Email) -> bool:
        """Store email in database if it doesn't already exist"""
        
        try:
            # Check if email already exists
            existing = await self.db.emails.find_one({
                "user_id": email.user_id,
                "metadata.provider_message_id": email.metadata.provider_message_id
            })
            
            if existing:
                return False  # Email already exists
            
            # Store new email
            await self.db.emails.insert_one(email.dict())
            return True
            
        except Exception as e:
            print(f"Email storage error: {e}")
            return False
    
    async def get_email_thread(self, user_id: str, thread_id: str) -> List[Email]:
        """Get all emails in a conversation thread"""
        
        try:
            emails = await self.db.emails.find({
                "user_id": user_id,
                "metadata.provider_thread_id": thread_id
            }).sort("received_at", 1).to_list(None)
            
            return [Email(**email) for email in emails]
            
        except Exception as e:
            print(f"Thread retrieval error: {e}")
            return []
    
    async def mark_email_as_read(self, user_id: str, email_id: str) -> bool:
        """Mark email as read in both database and provider"""
        
        try:
            # Update in database
            result = await self.db.emails.update_one(
                {"id": email_id, "user_id": user_id},
                {"$set": {"status": "read", "updated_at": datetime.utcnow()}}
            )
            
            if result.matched_count == 0:
                return False
            
            # Get email for provider update
            email = await self.db.emails.find_one({"id": email_id})
            if not email:
                return False
            
            # Get user connection info
            user = await self.db.users.find_one({"id": user_id})
            if not user:
                return False
            
            connections = user.get("connections", {})
            provider = email["provider"]
            
            # Update in provider
            if provider == "gmail" and connections.get("google_connected"):
                access_token = connections.get("google_access_token")
                if access_token:
                    await self.google_service.mark_email_read(
                        access_token, email["metadata"]["provider_message_id"]
                    )
            
            elif provider == "outlook" and connections.get("microsoft_connected"):
                access_token = connections.get("microsoft_access_token")
                if access_token:
                    await self.microsoft_service.mark_email_read(
                        access_token, email["metadata"]["provider_message_id"]
                    )
            
            return True
            
        except Exception as e:
            print(f"Mark as read error: {e}")
            return False
    
    async def search_emails(
        self,
        user_id: str,
        query: Optional[str] = None,
        sender: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> Dict[str, Any]:
        """Advanced email search"""
        
        try:
            # Build search query
            search_query = {"user_id": user_id}
            
            if query:
                search_query["$or"] = [
                    {"subject": {"$regex": query, "$options": "i"}},
                    {"body_text": {"$regex": query, "$options": "i"}}
                ]
            
            if sender:
                search_query["sender.email"] = {"$regex": sender, "$options": "i"}
            
            if date_from or date_to:
                date_filter = {}
                if date_from:
                    date_filter["$gte"] = date_from
                if date_to:
                    date_filter["$lte"] = date_to
                search_query["received_at"] = date_filter
            
            if priority:
                search_query["priority"] = priority
            
            if status:
                search_query["status"] = status
            
            # Execute search
            emails = await self.db.emails.find(search_query)\
                .sort("received_at", -1)\
                .skip(skip)\
                .limit(limit)\
                .to_list(None)
            
            # Get total count
            total_count = await self.db.emails.count_documents(search_query)
            
            return {
                "emails": emails,
                "total_count": total_count,
                "has_more": (skip + len(emails)) < total_count
            }
            
        except Exception as e:
            print(f"Email search error: {e}")
            return {"emails": [], "total_count": 0, "has_more": False}