import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.notifications import (
    Notification, NotificationChannel, NotificationType, 
    NotificationPriority, NotificationStatus, NotificationContent,
    UserNotificationPreferences, DeliveryAttempt
)
from services.twilio_service import TwilioService

class NotificationService:
    """Service for managing multi-channel notifications"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.twilio_service = TwilioService()
    
    async def send_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        channels: List[NotificationChannel],
        priority: NotificationPriority = NotificationPriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        metadata: Dict[str, Any] = None,
        related_email_id: Optional[str] = None,
        related_event_id: Optional[str] = None
    ) -> Notification:
        """Send a notification through specified channels"""
        
        try:
            # Get user's notification preferences
            preferences = await self._get_user_preferences(user_id)
            
            # Check if user wants this type of notification
            user_channels = preferences.channel_preferences.get(notification_type, channels)
            if not user_channels:
                user_channels = channels
            
            # Check quiet hours if applicable
            if (priority != NotificationPriority.URGENT and 
                preferences.quiet_hours_enabled and 
                self._is_in_quiet_hours(preferences)):
                # Schedule for later
                scheduled_at = self._get_next_allowed_time(preferences)
            
            # Check rate limits
            if not await self._check_rate_limits(user_id, user_channels, preferences):
                # Skip or delay notification
                scheduled_at = datetime.utcnow() + timedelta(minutes=30)
            
            # Create notification content
            content = NotificationContent(
                title=title,
                message=message,
                metadata=metadata or {}
            )
            
            # Create notification object
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                priority=priority,
                content=content,
                preferred_channels=user_channels,
                scheduled_at=scheduled_at or datetime.utcnow(),
                related_email_id=related_email_id,
                related_event_id=related_event_id
            )
            
            # Store notification
            await self.db.notifications.insert_one(notification.dict())
            
            # Send immediately if not scheduled
            if not scheduled_at or scheduled_at <= datetime.utcnow():
                await self._deliver_notification(notification)
            
            return notification
            
        except Exception as e:
            print(f"Notification sending error: {e}")
            raise Exception(f"Failed to send notification: {str(e)}")
    
    async def send_urgent_email_notification(
        self,
        user_id: str,
        email: Dict[str, Any],
        ai_analysis: Dict[str, Any]
    ) -> Notification:
        """Send urgent email notification"""
        
        try:
            # Create notification content
            title = f"Urgent Email: {email['subject'][:50]}"
            message = f"From: {email['sender']['email']}\n"
            message += f"Priority: {ai_analysis.get('urgency_score', 0)} urgency\n"
            
            if ai_analysis.get('action_required'):
                message += "⚠️ Action Required\n"
            
            if ai_analysis.get('deadline_mentioned'):
                message += f"⏰ Deadline: {ai_analysis['deadline_mentioned']}\n"
            
            # Add suggested actions
            if ai_analysis.get('suggested_actions'):
                message += f"Suggested: {', '.join(ai_analysis['suggested_actions'][:2])}"
            
            # Send through priority channels
            return await self.send_notification(
                user_id=user_id,
                notification_type=NotificationType.URGENT_EMAIL,
                title=title,
                message=message,
                channels=[NotificationChannel.SMS, NotificationChannel.WHATSAPP],
                priority=NotificationPriority.URGENT,
                metadata={
                    "email_subject": email['subject'],
                    "sender_email": email['sender']['email'],
                    "urgency_score": ai_analysis.get('urgency_score', 0)
                },
                related_email_id=email['id']
            )
            
        except Exception as e:
            print(f"Urgent email notification error: {e}")
            raise Exception(f"Failed to send urgent email notification: {str(e)}")
    
    async def send_meeting_reminder(
        self,
        user_id: str,
        event: Dict[str, Any],
        minutes_before: int = 15
    ) -> Notification:
        """Send meeting reminder notification"""
        
        try:
            # Calculate reminder time
            event_start = event["start_datetime"]
            reminder_time = event_start - timedelta(minutes=minutes_before)
            
            # Create notification content
            title = f"Meeting in {minutes_before} minutes"
            message = f"'{event['title']}'\n"
            
            if event.get("location"):
                message += f"📍 {event['location']['name']}\n"
            
            attendees = event.get("attendees", [])
            if attendees:
                message += f"👥 {len(attendees)} attendees\n"
            
            message += f"🕐 {event_start.strftime('%I:%M %p')}"
            
            return await self.send_notification(
                user_id=user_id,
                notification_type=NotificationType.MEETING_REMINDER,
                title=title,
                message=message,
                channels=[NotificationChannel.SMS, NotificationChannel.IN_APP],
                priority=NotificationPriority.HIGH,
                scheduled_at=reminder_time,
                metadata={
                    "event_title": event['title'],
                    "event_start": event_start.isoformat(),
                    "minutes_before": minutes_before
                },
                related_event_id=event['id']
            )
            
        except Exception as e:
            print(f"Meeting reminder error: {e}")
            raise Exception(f"Failed to send meeting reminder: {str(e)}")
    
    async def send_daily_summary(self, user_id: str) -> Notification:
        """Send daily summary notification"""
        
        try:
            # Get today's stats
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            
            # Get email stats
            email_stats = await self.db.emails.aggregate([
                {
                    "$match": {
                        "user_id": user_id,
                        "received_at": {"$gte": today, "$lt": tomorrow}
                    }
                },
                {
                    "$group": {
                        "_id": "$priority",
                        "count": {"$sum": 1}
                    }
                }
            ]).to_list(None)
            
            # Get upcoming events
            upcoming_events = await self.db.calendar_events.count_documents({
                "user_id": user_id,
                "start_datetime": {"$gte": datetime.utcnow(), "$lt": tomorrow}
            })
            
            # Get credit usage
            credits_used_today = await self.db.credit_transactions.aggregate([
                {
                    "$match": {
                        "user_id": user_id,
                        "transaction_type": "usage",
                        "created_at": {"$gte": today, "$lt": tomorrow}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": {"$abs": "$credits_amount"}}
                    }
                }
            ]).to_list(None)
            
            # Create summary message
            total_emails = sum(stat["count"] for stat in email_stats)
            urgent_emails = next((stat["count"] for stat in email_stats if stat["_id"] == "urgent"), 0)
            credits_used = credits_used_today[0]["total"] if credits_used_today else 0
            
            title = "Jessica Daily Summary"
            message = f"📧 {total_emails} emails processed"
            if urgent_emails > 0:
                message += f" ({urgent_emails} urgent)"
            
            message += f"\n📅 {upcoming_events} meetings today"
            message += f"\n⚡ {credits_used} credits used"
            
            # Add productivity insight
            if total_emails > 20:
                message += "\n🎯 High email volume day!"
            elif upcoming_events > 5:
                message += "\n📅 Busy meeting schedule!"
            
            return await self.send_notification(
                user_id=user_id,
                notification_type=NotificationType.DAILY_SUMMARY,
                title=title,
                message=message,
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
                priority=NotificationPriority.LOW,
                metadata={
                    "total_emails": total_emails,
                    "urgent_emails": urgent_emails,
                    "upcoming_events": upcoming_events,
                    "credits_used": credits_used
                }
            )
            
        except Exception as e:
            print(f"Daily summary error: {e}")
            raise Exception(f"Failed to send daily summary: {str(e)}")
    
    async def process_notification(self, notification_id: str) -> bool:
        """Process a pending notification"""
        
        try:
            # Get notification
            notification = await self.db.notifications.find_one({"id": notification_id})
            if not notification:
                return False
            
            # Check if it's time to send
            if notification["scheduled_at"] > datetime.utcnow():
                return False
            
            # Convert to Notification object
            notification_obj = Notification(**notification)
            
            # Deliver notification
            success = await self._deliver_notification(notification_obj)
            
            return success
            
        except Exception as e:
            print(f"Notification processing error: {e}")
            return False
    
    async def _deliver_notification(self, notification: Notification) -> bool:
        """Deliver notification through all specified channels"""
        
        try:
            success = False
            
            for channel in notification.preferred_channels:
                try:
                    delivery_attempt = DeliveryAttempt(
                        channel=channel,
                        attempted_at=datetime.utcnow(),
                        status=NotificationStatus.PENDING
                    )
                    
                    if channel == NotificationChannel.SMS:
                        result = await self._send_sms_notification(notification)
                        delivery_attempt.status = NotificationStatus.SENT if result else NotificationStatus.FAILED
                        
                    elif channel == NotificationChannel.WHATSAPP:
                        result = await self._send_whatsapp_notification(notification)
                        delivery_attempt.status = NotificationStatus.SENT if result else NotificationStatus.FAILED
                        
                    elif channel == NotificationChannel.EMAIL:
                        result = await self._send_email_notification(notification)
                        delivery_attempt.status = NotificationStatus.SENT if result else NotificationStatus.FAILED
                        
                    elif channel == NotificationChannel.IN_APP:
                        result = await self._send_in_app_notification(notification)
                        delivery_attempt.status = NotificationStatus.SENT if result else NotificationStatus.FAILED
                    
                    # Record delivery attempt
                    await self.db.notifications.update_one(
                        {"id": notification.id},
                        {"$push": {"delivery_attempts": delivery_attempt.dict()}}
                    )
                    
                    if delivery_attempt.status == NotificationStatus.SENT:
                        success = True
                    
                except Exception as e:
                    print(f"Channel delivery error for {channel}: {e}")
                    
                    # Record failed attempt
                    failed_attempt = DeliveryAttempt(
                        channel=channel,
                        attempted_at=datetime.utcnow(),
                        status=NotificationStatus.FAILED,
                        error_message=str(e)
                    )
                    
                    await self.db.notifications.update_one(
                        {"id": notification.id},
                        {"$push": {"delivery_attempts": failed_attempt.dict()}}
                    )
            
            # Update notification status
            final_status = NotificationStatus.SENT if success else NotificationStatus.FAILED
            update_data = {
                "status": final_status,
                "sent_at": datetime.utcnow() if success else None
            }
            
            if success:
                update_data["delivered_at"] = datetime.utcnow()
            
            await self.db.notifications.update_one(
                {"id": notification.id},
                {"$set": update_data}
            )
            
            return success
            
        except Exception as e:
            print(f"Notification delivery error: {e}")
            return False
    
    async def _send_sms_notification(self, notification: Notification) -> bool:
        """Send SMS notification"""
        try:
            # Get user phone number
            user = await self.db.users.find_one({"id": notification.user_id})
            if not user:
                return False
            
            phone_number = user.get("profile", {}).get("phone_number")
            if not phone_number:
                return False
            
            # Format message for SMS
            sms_message = f"{notification.content.title}\n{notification.content.message}"
            
            # Send via Twilio
            result = await self.twilio_service.send_sms(phone_number, sms_message)
            return result.get("success", False)
            
        except Exception as e:
            print(f"SMS sending error: {e}")
            return False
    
    async def _send_whatsapp_notification(self, notification: Notification) -> bool:
        """Send WhatsApp notification"""
        try:
            # Get user phone number
            user = await self.db.users.find_one({"id": notification.user_id})
            if not user:
                return False
            
            phone_number = user.get("profile", {}).get("phone_number")
            if not phone_number:
                return False
            
            # Format message for WhatsApp
            whatsapp_message = f"*{notification.content.title}*\n{notification.content.message}"
            
            # Send via Twilio
            result = await self.twilio_service.send_whatsapp(phone_number, whatsapp_message)
            return result.get("success", False)
            
        except Exception as e:
            print(f"WhatsApp sending error: {e}")
            return False
    
    async def _send_email_notification(self, notification: Notification) -> bool:
        """Send email notification"""
        try:
            # For now, just mark as sent
            # In production, would integrate with email service
            return True
            
        except Exception as e:
            print(f"Email notification error: {e}")
            return False
    
    async def _send_in_app_notification(self, notification: Notification) -> bool:
        """Send in-app notification"""
        try:
            # For in-app notifications, just ensure it's stored in database
            # The frontend will poll/subscribe for new notifications
            return True
            
        except Exception as e:
            print(f"In-app notification error: {e}")
            return False
    
    async def _get_user_preferences(self, user_id: str) -> UserNotificationPreferences:
        """Get user's notification preferences"""
        try:
            preferences = await self.db.notification_preferences.find_one({"user_id": user_id})
            
            if not preferences:
                # Create default preferences
                default_prefs = UserNotificationPreferences(user_id=user_id)
                await self.db.notification_preferences.insert_one(default_prefs.dict())
                return default_prefs
            
            return UserNotificationPreferences(**preferences)
            
        except Exception as e:
            print(f"Preferences retrieval error: {e}")
            return UserNotificationPreferences(user_id=user_id)
    
    def _is_in_quiet_hours(self, preferences: UserNotificationPreferences) -> bool:
        """Check if current time is within quiet hours"""
        try:
            if not preferences.quiet_hours_enabled:
                return False
            
            now = datetime.utcnow().time()
            start_time = datetime.strptime(preferences.quiet_hours_start, "%H:%M").time()
            end_time = datetime.strptime(preferences.quiet_hours_end, "%H:%M").time()
            
            if start_time <= end_time:
                return start_time <= now <= end_time
            else:
                # Quiet hours span midnight
                return now >= start_time or now <= end_time
            
        except Exception as e:
            print(f"Quiet hours check error: {e}")
            return False
    
    def _get_next_allowed_time(self, preferences: UserNotificationPreferences) -> datetime:
        """Get next allowed time outside quiet hours"""
        try:
            now = datetime.utcnow()
            end_time = datetime.strptime(preferences.quiet_hours_end, "%H:%M").time()
            
            # Schedule for end of quiet hours
            next_allowed = now.replace(
                hour=end_time.hour,
                minute=end_time.minute,
                second=0,
                microsecond=0
            )
            
            # If end time is tomorrow
            if next_allowed <= now:
                next_allowed += timedelta(days=1)
            
            return next_allowed
            
        except Exception as e:
            print(f"Next allowed time calculation error: {e}")
            return datetime.utcnow() + timedelta(hours=1)
    
    async def _check_rate_limits(
        self,
        user_id: str,
        channels: List[NotificationChannel],
        preferences: UserNotificationPreferences
    ) -> bool:
        """Check if sending notification would exceed rate limits"""
        try:
            now = datetime.utcnow()
            hour_ago = now - timedelta(hours=1)
            
            for channel in channels:
                # Count notifications sent in last hour for this channel
                sent_count = await self.db.notifications.count_documents({
                    "user_id": user_id,
                    "preferred_channels": channel,
                    "sent_at": {"$gte": hour_ago, "$lte": now}
                })
                
                # Check against user's limit
                max_per_hour = preferences.max_notifications_per_hour.get(channel, 10)
                
                if sent_count >= max_per_hour:
                    return False
            
            return True
            
        except Exception as e:
            print(f"Rate limit check error: {e}")
            return True  # Allow if check fails