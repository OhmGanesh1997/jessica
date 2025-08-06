import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.calendar import (
    CalendarEvent, EventCreateRequest, EventUpdateRequest, 
    SchedulingSuggestion, CalendarProvider, EventStatus,
    AvailabilitySlot, ConflictInfo
)
from services.ai_service import AIService
from services.google_service import GoogleService
from services.microsoft_service import MicrosoftService

class CalendarService:
    """Service for calendar management and smart scheduling"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.ai_service = AIService()
        self.google_service = GoogleService()
        self.microsoft_service = MicrosoftService()
    
    async def create_event(
        self,
        user_id: str,
        event_data: EventCreateRequest
    ) -> CalendarEvent:
        """Create a new calendar event"""
        
        try:
            # Get user's primary calendar provider
            user = await self.db.users.find_one({"id": user_id})
            if not user:
                raise Exception(f"User {user_id} not found")
            
            connections = user.get("connections", {})
            
            # Determine provider (prefer Google, fall back to Microsoft)
            provider = CalendarProvider.GOOGLE
            if not connections.get("google_connected") and connections.get("microsoft_connected"):
                provider = CalendarProvider.MICROSOFT
            
            # Create event object
            event = CalendarEvent(
                user_id=user_id,
                provider=provider,
                title=event_data.title,
                description=event_data.description,
                location=event_data.location,
                start_datetime=event_data.start_datetime,
                end_datetime=event_data.end_datetime,
                attendees=[],  # Will be populated from emails
                organizer={"email": user["email"], "name": user.get("profile", {}).get("full_name", "")},
                provider_event_id=str(uuid.uuid4()),  # Temporary, will be replaced by provider
                provider_calendar_id="primary"
            )
            
            # Add attendees
            for email in event_data.attendee_emails:
                event.attendees.append({
                    "email": email,
                    "status": "needsAction",
                    "is_organizer": False,
                    "is_required": True
                })
            
            # Create event in external provider
            if provider == CalendarProvider.GOOGLE and connections.get("google_connected"):
                access_token = connections.get("google_access_token")
                if access_token:
                    provider_event = await self.google_service.create_calendar_event(
                        access_token=access_token,
                        title=event_data.title,
                        start_time=event_data.start_datetime,
                        end_time=event_data.end_datetime,
                        attendees=event_data.attendee_emails,
                        description=event_data.description,
                        location=event_data.location.name if event_data.location else None
                    )
                    event.provider_event_id = provider_event.get("id", event.provider_event_id)
            
            elif provider == CalendarProvider.MICROSOFT and connections.get("microsoft_connected"):
                access_token = connections.get("microsoft_access_token")
                if access_token:
                    provider_event = await self.microsoft_service.create_calendar_event(
                        access_token=access_token,
                        title=event_data.title,
                        start_time=event_data.start_datetime,
                        end_time=event_data.end_datetime,
                        attendees=event_data.attendee_emails,
                        description=event_data.description,
                        location=event_data.location.name if event_data.location else None
                    )
                    event.provider_event_id = provider_event.get("id", event.provider_event_id)
            
            # Store in database
            await self.db.calendar_events.insert_one(event.dict())
            
            return event
            
        except Exception as e:
            print(f"Event creation error: {e}")
            raise Exception(f"Failed to create event: {str(e)}")
    
    async def update_event(
        self,
        user_id: str,
        event_id: str,
        update_data: EventUpdateRequest
    ) -> CalendarEvent:
        """Update existing calendar event"""
        
        try:
            # Get existing event
            existing_event = await self.db.calendar_events.find_one({
                "id": event_id,
                "user_id": user_id
            })
            
            if not existing_event:
                raise Exception(f"Event {event_id} not found")
            
            # Prepare update fields
            update_fields = {"updated_at": datetime.utcnow()}
            
            if update_data.title:
                update_fields["title"] = update_data.title
            if update_data.description:
                update_fields["description"] = update_data.description
            if update_data.start_datetime:
                update_fields["start_datetime"] = update_data.start_datetime
            if update_data.end_datetime:
                update_fields["end_datetime"] = update_data.end_datetime
            if update_data.location:
                update_fields["location"] = update_data.location.dict()
            if update_data.attendee_emails:
                # Convert emails to attendee objects
                attendees = []
                for email in update_data.attendee_emails:
                    attendees.append({
                        "email": email,
                        "status": "needsAction",
                        "is_organizer": False,
                        "is_required": True
                    })
                update_fields["attendees"] = attendees
            if update_data.status:
                update_fields["status"] = update_data.status
            
            # Update in database
            await self.db.calendar_events.update_one(
                {"id": event_id},
                {"$set": update_fields}
            )
            
            # Update in external provider
            user = await self.db.users.find_one({"id": user_id})
            connections = user.get("connections", {})
            provider = existing_event["provider"]
            
            if provider == "google" and connections.get("google_connected"):
                access_token = connections.get("google_access_token")
                if access_token:
                    await self.google_service.update_calendar_event(
                        access_token=access_token,
                        event_id=existing_event["provider_event_id"],
                        updates=update_fields
                    )
            
            elif provider == "outlook" and connections.get("microsoft_connected"):
                access_token = connections.get("microsoft_access_token")
                if access_token:
                    await self.microsoft_service.update_calendar_event(
                        access_token=access_token,
                        event_id=existing_event["provider_event_id"],
                        updates=update_fields
                    )
            
            # Get updated event
            updated_event = await self.db.calendar_events.find_one({"id": event_id})
            return CalendarEvent(**updated_event)
            
        except Exception as e:
            print(f"Event update error: {e}")
            raise Exception(f"Failed to update event: {str(e)}")
    
    async def delete_event(self, user_id: str, event_id: str) -> bool:
        """Delete calendar event"""
        
        try:
            # Get event to delete
            event = await self.db.calendar_events.find_one({
                "id": event_id,
                "user_id": user_id
            })
            
            if not event:
                return False
            
            # Delete from external provider
            user = await self.db.users.find_one({"id": user_id})
            connections = user.get("connections", {})
            provider = event["provider"]
            
            if provider == "google" and connections.get("google_connected"):
                access_token = connections.get("google_access_token")
                if access_token:
                    await self.google_service.delete_calendar_event(
                        access_token, event["provider_event_id"]
                    )
            
            elif provider == "outlook" and connections.get("microsoft_connected"):
                access_token = connections.get("microsoft_access_token")
                if access_token:
                    await self.microsoft_service.delete_calendar_event(
                        access_token, event["provider_event_id"]
                    )
            
            # Delete from database
            result = await self.db.calendar_events.delete_one({"id": event_id})
            return result.deleted_count > 0
            
        except Exception as e:
            print(f"Event deletion error: {e}")
            return False
    
    async def check_availability(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        attendee_emails: Optional[List[str]] = None,
        duration_minutes: int = 30,
        buffer_time_minutes: int = 15
    ) -> List[Dict[str, Any]]:
        """Check availability for scheduling"""
        
        try:
            # Get user's events in date range
            user_events = await self.db.calendar_events.find({
                "user_id": user_id,
                "start_datetime": {"$lte": end_date},
                "end_datetime": {"$gte": start_date},
                "status": {"$ne": "cancelled"}
            }).to_list(None)
            
            # Generate availability slots
            availability_by_date = {}
            current_date = start_date.date()
            end_date_only = end_date.date()
            
            while current_date <= end_date_only:
                # Create time slots for this date (9 AM to 6 PM by default)
                day_start = datetime.combine(current_date, datetime.min.time().replace(hour=9))
                day_end = datetime.combine(current_date, datetime.min.time().replace(hour=18))
                
                availability_slots = []
                current_slot = day_start
                
                while current_slot + timedelta(minutes=duration_minutes) <= day_end:
                    slot_end = current_slot + timedelta(minutes=duration_minutes)
                    
                    # Check if slot conflicts with existing events
                    is_busy = False
                    conflicting_event = None
                    
                    for event in user_events:
                        event_start = event["start_datetime"]
                        event_end = event["end_datetime"]
                        
                        # Add buffer time
                        buffered_start = current_slot - timedelta(minutes=buffer_time_minutes)
                        buffered_end = slot_end + timedelta(minutes=buffer_time_minutes)
                        
                        if (buffered_start < event_end and buffered_end > event_start):
                            is_busy = True
                            conflicting_event = event
                            break
                    
                    availability_slots.append(AvailabilitySlot(
                        start_datetime=current_slot,
                        end_datetime=slot_end,
                        is_busy=is_busy,
                        event_title=conflicting_event["title"] if conflicting_event else None,
                        event_id=conflicting_event["id"] if conflicting_event else None,
                        buffer_time_needed=True
                    ))
                    
                    # Move to next slot (15-minute increments)
                    current_slot += timedelta(minutes=15)
                
                availability_by_date[current_date.isoformat()] = {
                    "date": current_date.isoformat(),
                    "slots": [slot.dict() for slot in availability_slots]
                }
                
                current_date += timedelta(days=1)
            
            return list(availability_by_date.values())
            
        except Exception as e:
            print(f"Availability check error: {e}")
            return []
    
    async def get_smart_scheduling_suggestions(
        self,
        user_id: str,
        scheduling_request: Dict[str, Any]
    ) -> List[SchedulingSuggestion]:
        """Get AI-powered scheduling suggestions"""
        
        try:
            # Get user's events for context
            existing_events = await self.db.calendar_events.find({
                "user_id": user_id,
                "start_datetime": {
                    "$gte": scheduling_request["date_range_start"],
                    "$lte": scheduling_request["date_range_end"]
                }
            }).to_list(None)
            
            # Get user guidelines
            guidelines = await self.db.user_guidelines.find_one({"user_id": user_id})
            
            # Use AI service to generate suggestions
            suggestions = await self.ai_service.generate_scheduling_suggestions(
                title=scheduling_request["title"],
                duration_minutes=scheduling_request["duration_minutes"],
                attendee_emails=scheduling_request["attendee_emails"],
                existing_events=existing_events,
                user_guidelines=guidelines,
                preferred_times=scheduling_request.get("preferred_times"),
                date_range_start=scheduling_request["date_range_start"],
                date_range_end=scheduling_request["date_range_end"]
            )
            
            # Convert to SchedulingSuggestion objects
            suggestion_objects = []
            for suggestion in suggestions:
                try:
                    suggestion_obj = SchedulingSuggestion(
                        suggested_datetime=datetime.fromisoformat(suggestion["suggested_datetime"]),
                        duration_minutes=suggestion["duration_minutes"],
                        confidence_score=suggestion["confidence_score"],
                        reasons=suggestion["reasons"],
                        attendee_availability=suggestion.get("attendee_availability", {}),
                        optimal_score=suggestion.get("optimal_score", 0.5)
                    )
                    suggestion_objects.append(suggestion_obj)
                except Exception as e:
                    print(f"Invalid suggestion format: {e}")
                    continue
            
            return suggestion_objects
            
        except Exception as e:
            print(f"Smart scheduling error: {e}")
            return []
    
    async def find_scheduling_conflicts(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[ConflictInfo]:
        """Find scheduling conflicts in date range"""
        
        try:
            # Get events in date range
            events = await self.db.calendar_events.find({
                "user_id": user_id,
                "start_datetime": {"$lte": end_date},
                "end_datetime": {"$gte": start_date},
                "status": {"$ne": "cancelled"}
            }).sort("start_datetime", 1).to_list(None)
            
            conflicts = []
            
            # Check for overlapping events
            for i, event1 in enumerate(events):
                for event2 in events[i+1:]:
                    # Check if events overlap
                    if (event1["start_datetime"] < event2["end_datetime"] and 
                        event1["end_datetime"] > event2["start_datetime"]):
                        
                        # Calculate overlap duration
                        overlap_start = max(event1["start_datetime"], event2["start_datetime"])
                        overlap_end = min(event1["end_datetime"], event2["end_datetime"])
                        overlap_minutes = int((overlap_end - overlap_start).total_seconds() / 60)
                        
                        conflict = ConflictInfo(
                            conflict_type="hard",
                            conflicting_event_id=event2["id"],
                            conflicting_event_title=event2["title"],
                            overlap_duration_minutes=overlap_minutes,
                            suggested_resolution=f"Reschedule '{event2['title']}' to avoid overlap with '{event1['title']}'"
                        )
                        conflicts.append(conflict)
            
            # Check for insufficient buffer time
            for i, event in enumerate(events[:-1]):
                next_event = events[i + 1]
                time_between = (next_event["start_datetime"] - event["end_datetime"]).total_seconds() / 60
                
                if 0 < time_between < 15:  # Less than 15 minutes between events
                    conflict = ConflictInfo(
                        conflict_type="soft",
                        conflicting_event_id=next_event["id"],
                        conflicting_event_title=next_event["title"],
                        overlap_duration_minutes=0,
                        suggested_resolution=f"Add buffer time between '{event['title']}' and '{next_event['title']}'"
                    )
                    conflicts.append(conflict)
            
            return conflicts
            
        except Exception as e:
            print(f"Conflict detection error: {e}")
            return []
    
    async def resolve_scheduling_conflict(
        self,
        user_id: str,
        event_id: str,
        resolution_strategy: str,
        preferred_alternatives: Optional[List[datetime]] = None
    ) -> Dict[str, Any]:
        """Resolve scheduling conflicts with AI suggestions"""
        
        try:
            # Get the conflicting event
            event = await self.db.calendar_events.find_one({
                "id": event_id,
                "user_id": user_id
            })
            
            if not event:
                raise Exception(f"Event {event_id} not found")
            
            if resolution_strategy == "reschedule":
                # Find alternative times
                start_search = event["start_datetime"]
                end_search = start_search + timedelta(days=7)  # Search next 7 days
                
                availability = await self.check_availability(
                    user_id=user_id,
                    start_date=start_search,
                    end_date=end_search,
                    duration_minutes=int((event["end_datetime"] - event["start_datetime"]).total_seconds() / 60)
                )
                
                # Find free slots
                alternatives = []
                for day_availability in availability:
                    for slot in day_availability["slots"]:
                        if not slot["is_busy"]:
                            alternatives.append(slot["start_datetime"])
                        if len(alternatives) >= 5:  # Limit to 5 alternatives
                            break
                    if len(alternatives) >= 5:
                        break
                
                return {
                    "strategy": "reschedule",
                    "alternatives": alternatives[:3],
                    "current_time": event["start_datetime"],
                    "message": f"Found {len(alternatives)} alternative times for '{event['title']}'"
                }
            
            elif resolution_strategy == "shorten":
                # Suggest shortening the meeting
                current_duration = (event["end_datetime"] - event["start_datetime"]).total_seconds() / 60
                suggested_duration = max(15, current_duration - 15)  # Shorten by 15 minutes, minimum 15 min
                
                return {
                    "strategy": "shorten",
                    "current_duration": int(current_duration),
                    "suggested_duration": int(suggested_duration),
                    "message": f"Shorten '{event['title']}' from {int(current_duration)} to {int(suggested_duration)} minutes"
                }
            
            elif resolution_strategy == "cancel":
                return {
                    "strategy": "cancel",
                    "event_id": event_id,
                    "message": f"Cancel '{event['title']}' to resolve conflict"
                }
            
            else:
                raise Exception(f"Unknown resolution strategy: {resolution_strategy}")
            
        except Exception as e:
            print(f"Conflict resolution error: {e}")
            raise Exception(f"Failed to resolve conflict: {str(e)}")
    
    async def sync_calendar_from_provider(self, user_id: str, provider: str) -> Dict[str, Any]:
        """Sync calendar events from external provider"""
        
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
                
                # Fetch events from Google Calendar
                google_events = await self.google_service.fetch_calendar_events(
                    access_token, days_ahead=30
                )
                
                # Process and store events
                for google_event in google_events:
                    try:
                        event = await self._convert_google_to_event(user_id, google_event)
                        await self._store_event_if_new(event)
                        sync_result["synced_count"] += 1
                    except Exception as e:
                        sync_result["errors"].append(f"Failed to process event: {str(e)}")
            
            elif provider == "microsoft" and connections.get("microsoft_connected"):
                access_token = connections.get("microsoft_access_token")
                if not access_token:
                    raise Exception("Microsoft access token not found")
                
                # Fetch events from Outlook Calendar
                outlook_events = await self.microsoft_service.fetch_calendar_events(
                    access_token, days_ahead=30
                )
                
                # Process and store events
                for outlook_event in outlook_events:
                    try:
                        event = await self._convert_outlook_to_event(user_id, outlook_event)
                        await self._store_event_if_new(event)
                        sync_result["synced_count"] += 1
                    except Exception as e:
                        sync_result["errors"].append(f"Failed to process event: {str(e)}")
            
            else:
                raise Exception(f"Provider {provider} not connected or not supported")
            
            return sync_result
            
        except Exception as e:
            print(f"Calendar sync error for {provider}: {e}")
            return {"synced_count": 0, "errors": [str(e)]}
    
    async def _convert_google_to_event(self, user_id: str, google_data: Dict[str, Any]) -> CalendarEvent:
        """Convert Google Calendar API response to CalendarEvent object"""
        
        try:
            # Parse start and end times
            start_time = google_data.get("start", {})
            end_time = google_data.get("end", {})
            
            if "dateTime" in start_time:
                start_datetime = datetime.fromisoformat(start_time["dateTime"].replace("Z", "+00:00"))
                end_datetime = datetime.fromisoformat(end_time["dateTime"].replace("Z", "+00:00"))
                all_day = False
            else:
                # All-day event
                start_datetime = datetime.fromisoformat(start_time["date"])
                end_datetime = datetime.fromisoformat(end_time["date"])
                all_day = True
            
            # Parse attendees
            attendees = []
            for attendee in google_data.get("attendees", []):
                attendees.append({
                    "email": attendee.get("email", ""),
                    "name": attendee.get("displayName"),
                    "status": attendee.get("responseStatus", "needsAction"),
                    "is_organizer": attendee.get("organizer", False),
                    "is_required": not attendee.get("optional", False)
                })
            
            # Parse organizer
            organizer_data = google_data.get("organizer", {})
            organizer = {
                "email": organizer_data.get("email", ""),
                "name": organizer_data.get("displayName"),
                "status": "accepted",
                "is_organizer": True,
                "is_required": True
            }
            
            # Create event object
            event = CalendarEvent(
                user_id=user_id,
                provider=CalendarProvider.GOOGLE,
                title=google_data.get("summary", "Untitled Event"),
                description=google_data.get("description"),
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                all_day=all_day,
                attendees=attendees,
                organizer=organizer,
                status=google_data.get("status", "confirmed"),
                provider_event_id=google_data["id"],
                provider_calendar_id=google_data.get("organizer", {}).get("email", "primary"),
                provider_metadata=google_data
            )
            
            return event
            
        except Exception as e:
            print(f"Google event conversion error: {e}")
            raise Exception(f"Failed to convert Google event: {str(e)}")
    
    async def _convert_outlook_to_event(self, user_id: str, outlook_data: Dict[str, Any]) -> CalendarEvent:
        """Convert Outlook API response to CalendarEvent object"""
        
        try:
            # Parse start and end times
            start_datetime = datetime.fromisoformat(outlook_data["start"]["dateTime"])
            end_datetime = datetime.fromisoformat(outlook_data["end"]["dateTime"])
            all_day = outlook_data.get("isAllDay", False)
            
            # Parse attendees
            attendees = []
            for attendee in outlook_data.get("attendees", []):
                email_addr = attendee.get("emailAddress", {})
                attendees.append({
                    "email": email_addr.get("address", ""),
                    "name": email_addr.get("name"),
                    "status": attendee.get("status", {}).get("response", "none"),
                    "is_organizer": False,
                    "is_required": attendee.get("type") == "required"
                })
            
            # Parse organizer
            organizer_data = outlook_data.get("organizer", {}).get("emailAddress", {})
            organizer = {
                "email": organizer_data.get("address", ""),
                "name": organizer_data.get("name"),
                "status": "accepted",
                "is_organizer": True,
                "is_required": True
            }
            
            # Parse location
            location = None
            if outlook_data.get("location", {}).get("displayName"):
                location = {
                    "name": outlook_data["location"]["displayName"],
                    "address": outlook_data["location"].get("address", {}).get("street"),
                    "is_virtual": False
                }
            
            # Create event object
            event = CalendarEvent(
                user_id=user_id,
                provider=CalendarProvider.MICROSOFT,
                title=outlook_data.get("subject", "Untitled Event"),
                description=outlook_data.get("bodyPreview"),
                location=location,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                all_day=all_day,
                attendees=attendees,
                organizer=organizer,
                status="confirmed",  # Outlook doesn't have same status model
                provider_event_id=outlook_data["id"],
                provider_calendar_id="primary",
                provider_metadata=outlook_data
            )
            
            return event
            
        except Exception as e:
            print(f"Outlook event conversion error: {e}")
            raise Exception(f"Failed to convert Outlook event: {str(e)}")
    
    async def _store_event_if_new(self, event: CalendarEvent) -> bool:
        """Store calendar event in database if it doesn't already exist"""
        
        try:
            # Check if event already exists
            existing = await self.db.calendar_events.find_one({
                "user_id": event.user_id,
                "provider_event_id": event.provider_event_id
            })
            
            if existing:
                # Update existing event
                await self.db.calendar_events.update_one(
                    {"id": existing["id"]},
                    {"$set": event.dict(exclude={"id", "created_at"})}
                )
                return False
            
            # Store new event
            await self.db.calendar_events.insert_one(event.dict())
            return True
            
        except Exception as e:
            print(f"Event storage error: {e}")
            return False