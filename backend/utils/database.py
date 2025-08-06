from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from bson import ObjectId
import uuid

class DatabaseManager:
    """Database utility class for MongoDB operations"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
    
    async def create_indexes(self):
        """Create necessary database indexes for performance"""
        
        # Users collection indexes
        users = self.db.users
        await users.create_index("email", unique=True)
        await users.create_index("verification_token")
        await users.create_index("reset_password_token")
        await users.create_index("stripe_customer_id")
        await users.create_index("created_at")
        
        # Emails collection indexes
        emails = self.db.emails
        await emails.create_index([("user_id", 1), ("received_at", -1)])
        await emails.create_index([("user_id", 1), ("status", 1)])
        await emails.create_index([("user_id", 1), ("priority", 1)])
        await emails.create_index("metadata.provider_message_id", unique=True)
        await emails.create_index([("sender.email", 1), ("received_at", -1)])
        
        # Calendar events collection indexes
        calendar_events = self.db.calendar_events
        await calendar_events.create_index([("user_id", 1), ("start_datetime", 1)])
        await calendar_events.create_index([("user_id", 1), ("end_datetime", 1)])
        await calendar_events.create_index("provider_event_id", unique=True)
        await calendar_events.create_index([("attendees.email", 1)])
        
        # Notifications collection indexes
        notifications = self.db.notifications
        await notifications.create_index([("user_id", 1), ("created_at", -1)])
        await notifications.create_index([("user_id", 1), ("status", 1)])
        await notifications.create_index("scheduled_at")
        await notifications.create_index("expires_at")
        
        # Guidelines collection indexes
        guidelines = self.db.user_guidelines
        await guidelines.create_index("user_id", unique=True)
        await guidelines.create_index([("user_id", 1), ("updated_at", -1)])
        
        # Payments collection indexes
        payments = self.db.payments
        await payments.create_index([("user_id", 1), ("created_at", -1)])
        await payments.create_index("stripe_payment_intent_id", unique=True)
        await payments.create_index([("status", 1), ("created_at", -1)])
        
        # Credit transactions collection indexes
        credit_transactions = self.db.credit_transactions
        await credit_transactions.create_index([("user_id", 1), ("created_at", -1)])
        await credit_transactions.create_index([("user_id", 1), ("transaction_type", 1)])
        
        print("✅ Database indexes created successfully")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database health and connectivity"""
        try:
            # Test database connection
            await self.db.command("ping")
            
            # Get collection stats
            collections = await self.db.list_collection_names()
            
            stats = {}
            for collection_name in collections:
                collection = self.db[collection_name]
                count = await collection.count_documents({})
                stats[collection_name] = count
            
            return {
                "status": "healthy",
                "collections": len(collections),
                "collection_stats": stats,
                "timestamp": datetime.utcnow()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }

class QueryBuilder:
    """Helper class for building MongoDB queries"""
    
    @staticmethod
    def build_email_search_query(
        user_id: str,
        query: Optional[str] = None,
        sender: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        has_attachments: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Build query for email search"""
        
        base_query = {"user_id": user_id}
        
        if query:
            base_query["$or"] = [
                {"subject": {"$regex": query, "$options": "i"}},
                {"body_text": {"$regex": query, "$options": "i"}}
            ]
        
        if sender:
            base_query["sender.email"] = {"$regex": sender, "$options": "i"}
        
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = date_from
            if date_to:
                date_query["$lte"] = date_to
            base_query["received_at"] = date_query
        
        if priority:
            base_query["priority"] = priority
        
        if status:
            base_query["status"] = status
        
        if has_attachments is not None:
            base_query["has_attachments"] = has_attachments
        
        return base_query
    
    @staticmethod
    def build_calendar_query(
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        attendee_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build query for calendar events"""
        
        base_query = {"user_id": user_id}
        
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            base_query["start_datetime"] = date_query
        
        if status:
            base_query["status"] = status
        
        if attendee_email:
            base_query["attendees.email"] = attendee_email
        
        return base_query
    
    @staticmethod
    def build_notification_query(
        user_id: str,
        status: Optional[str] = None,
        type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Build query for notifications"""
        
        base_query = {"user_id": user_id}
        
        if status:
            base_query["status"] = status
        
        if type:
            base_query["type"] = type
        
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = date_from
            if date_to:
                date_query["$lte"] = date_to
            base_query["created_at"] = date_query
        
        return base_query

class ValidationUtils:
    """Utility functions for data validation"""
    
    @staticmethod
    def is_valid_uuid(value: str) -> bool:
        """Check if a string is a valid UUID"""
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """Sanitize and normalize email address"""
        return email.lower().strip()
    
    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """Basic phone number validation"""
        import re
        # Remove all non-digit characters
        clean_phone = re.sub(r'[^\d+]', '', phone)
        # Check if it starts with + and has 10-15 digits
        pattern = r'^\+?[1-9]\d{9,14}$'
        return bool(re.match(pattern, clean_phone))
    
    @staticmethod
    def convert_objectid_to_str(data: Union[Dict, List]) -> Union[Dict, List]:
        """Convert ObjectId fields to strings recursively"""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key == "_id" and isinstance(value, ObjectId):
                    result[key] = str(value)
                elif isinstance(value, ObjectId):
                    result[key] = str(value)
                elif isinstance(value, (dict, list)):
                    result[key] = ValidationUtils.convert_objectid_to_str(value)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            return [ValidationUtils.convert_objectid_to_str(item) for item in data]
        else:
            return data

# Pagination utility
class PaginationHelper:
    """Helper for handling pagination in API responses"""
    
    @staticmethod
    def paginate_query(
        collection: AsyncIOMotorCollection,
        query: Dict[str, Any],
        page: int = 1,
        limit: int = 50,
        sort_field: str = "created_at",
        sort_order: int = -1
    ) -> Dict[str, Any]:
        """Create pagination parameters for MongoDB query"""
        
        skip = (page - 1) * limit
        
        return {
            "find_query": query,
            "sort": [(sort_field, sort_order)],
            "skip": skip,
            "limit": limit
        }
    
    @staticmethod
    def build_pagination_response(
        items: List[Any],
        total_count: int,
        page: int,
        limit: int
    ) -> Dict[str, Any]:
        """Build standardized pagination response"""
        
        return {
            "items": items,
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit,
            "has_next": page * limit < total_count,
            "has_prev": page > 1
        }