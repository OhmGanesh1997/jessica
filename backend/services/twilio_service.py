from twilio.rest import Client
from typing import Dict, Any, Optional
from decouple import config
import re

class TwilioService:
    """Service for SMS and WhatsApp notifications via Twilio"""
    
    def __init__(self):
        self.account_sid = config('TWILIO_ACCOUNT_SID', default='placeholder_account_sid')
        self.auth_token = config('TWILIO_AUTH_TOKEN', default='placeholder_auth_token')
        self.phone_number = config('TWILIO_PHONE_NUMBER', default='+1234567890')
        
        try:
            self.client = Client(self.account_sid, self.auth_token)
        except Exception as e:
            print(f"Twilio client initialization error: {e}")
            self.client = None
    
    async def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send SMS message"""
        
        try:
            if not self.client:
                return {"success": False, "error": "Twilio client not initialized"}
            
            # Validate and format phone number
            formatted_number = self._format_phone_number(to_number)
            if not formatted_number:
                return {"success": False, "error": "Invalid phone number format"}
            
            # Truncate message if too long (SMS limit is 160 characters)
            if len(message) > 160:
                message = message[:157] + "..."
            
            # Send SMS
            message_obj = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=formatted_number
            )
            
            return {
                "success": True,
                "message_sid": message_obj.sid,
                "status": message_obj.status,
                "to": formatted_number,
                "body": message
            }
            
        except Exception as e:
            print(f"SMS sending error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_whatsapp(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send WhatsApp message"""
        
        try:
            if not self.client:
                return {"success": False, "error": "Twilio client not initialized"}
            
            # Validate and format phone number
            formatted_number = self._format_phone_number(to_number)
            if not formatted_number:
                return {"success": False, "error": "Invalid phone number format"}
            
            # WhatsApp messages have higher character limit
            if len(message) > 1600:
                message = message[:1597] + "..."
            
            # Send WhatsApp message
            message_obj = self.client.messages.create(
                body=message,
                from_=f"whatsapp:{self.phone_number}",
                to=f"whatsapp:{formatted_number}"
            )
            
            return {
                "success": True,
                "message_sid": message_obj.sid,
                "status": message_obj.status,
                "to": formatted_number,
                "body": message,
                "channel": "whatsapp"
            }
            
        except Exception as e:
            print(f"WhatsApp sending error: {e}")
            return {
                "success": False,
                "error": str(e),
                "channel": "whatsapp"
            }
    
    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """Get status of a sent message"""
        
        try:
            if not self.client:
                return {"error": "Twilio client not initialized"}
            
            message = self.client.messages(message_sid).fetch()
            
            return {
                "sid": message.sid,
                "status": message.status,
                "error_code": message.error_code,
                "error_message": message.error_message,
                "date_created": message.date_created,
                "date_updated": message.date_updated,
                "date_sent": message.date_sent,
                "price": message.price,
                "direction": message.direction
            }
            
        except Exception as e:
            print(f"Message status retrieval error: {e}")
            return {"error": str(e)}
    
    async def test_sms(self, to_number: str) -> Dict[str, Any]:
        """Send test SMS message"""
        
        test_message = "🤖 Jessica AI Test: SMS notifications are working correctly!"
        
        result = await self.send_sms(to_number, test_message)
        
        return {
            "test_type": "sms",
            "success": result.get("success", False),
            "message": "SMS test completed",
            "details": result
        }
    
    async def test_whatsapp(self, to_number: str) -> Dict[str, Any]:
        """Send test WhatsApp message"""
        
        test_message = """🤖 *Jessica AI Test*
        
WhatsApp notifications are working correctly!

This is a test message to verify your notification settings."""
        
        result = await self.send_whatsapp(to_number, test_message)
        
        return {
            "test_type": "whatsapp",
            "success": result.get("success", False),
            "message": "WhatsApp test completed",
            "details": result
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Twilio service health"""
        
        try:
            if not self.client:
                return {
                    "status": "unhealthy",
                    "error": "Twilio client not initialized",
                    "configured": False
                }
            
            # Try to fetch account info as health check
            account = self.client.api.accounts(self.account_sid).fetch()
            
            return {
                "status": "healthy",
                "account_sid": self.account_sid,
                "account_status": account.status,
                "phone_number": self.phone_number,
                "configured": True,
                "capabilities": {
                    "sms": True,
                    "whatsapp": True
                }
            }
            
        except Exception as e:
            print(f"Twilio health check error: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "configured": False
            }
    
    async def get_delivery_report(self, message_sids: list) -> Dict[str, Any]:
        """Get delivery report for multiple messages"""
        
        try:
            if not self.client:
                return {"error": "Twilio client not initialized"}
            
            delivery_report = {
                "total_messages": len(message_sids),
                "delivered": 0,
                "failed": 0,
                "pending": 0,
                "details": []
            }
            
            for sid in message_sids:
                try:
                    status_info = await self.get_message_status(sid)
                    
                    if "error" in status_info:
                        delivery_report["failed"] += 1
                        continue
                    
                    status = status_info.get("status", "").lower()
                    
                    if status in ["delivered", "read"]:
                        delivery_report["delivered"] += 1
                    elif status in ["failed", "undelivered"]:
                        delivery_report["failed"] += 1
                    else:
                        delivery_report["pending"] += 1
                    
                    delivery_report["details"].append({
                        "sid": sid,
                        "status": status,
                        "error_code": status_info.get("error_code"),
                        "price": status_info.get("price")
                    })
                    
                except Exception as e:
                    print(f"Error checking message {sid}: {e}")
                    delivery_report["failed"] += 1
            
            # Calculate success rate
            if delivery_report["total_messages"] > 0:
                delivery_report["success_rate"] = (
                    delivery_report["delivered"] / delivery_report["total_messages"] * 100
                )
            else:
                delivery_report["success_rate"] = 0
            
            return delivery_report
            
        except Exception as e:
            print(f"Delivery report error: {e}")
            return {"error": str(e)}
    
    async def validate_phone_number(self, phone_number: str) -> Dict[str, Any]:
        """Validate phone number using Twilio Lookup API"""
        
        try:
            if not self.client:
                return {"valid": False, "error": "Twilio client not initialized"}
            
            formatted_number = self._format_phone_number(phone_number)
            if not formatted_number:
                return {"valid": False, "error": "Invalid phone number format"}
            
            # Use Twilio Lookup API
            try:
                phone_number_info = self.client.lookups.phone_numbers(formatted_number).fetch()
                
                return {
                    "valid": True,
                    "phone_number": phone_number_info.phone_number,
                    "country_code": phone_number_info.country_code,
                    "national_format": phone_number_info.national_format,
                    "carrier": getattr(phone_number_info, 'carrier', None),
                    "line_type": getattr(phone_number_info, 'line_type_intelligence', None)
                }
                
            except Exception as lookup_error:
                # If lookup fails, still validate basic format
                return {
                    "valid": True,  # Basic format is valid
                    "phone_number": formatted_number,
                    "lookup_error": str(lookup_error),
                    "note": "Basic validation only - Lookup API unavailable"
                }
            
        except Exception as e:
            print(f"Phone validation error: {e}")
            return {"valid": False, "error": str(e)}
    
    async def get_usage_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get SMS/WhatsApp usage statistics"""
        
        try:
            if not self.client:
                return {"error": "Twilio client not initialized"}
            
            from datetime import datetime, timedelta
            
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get message usage
            messages = self.client.messages.list(
                date_sent_after=start_date,
                date_sent_before=end_date,
                limit=1000
            )
            
            usage_stats = {
                "period_days": days,
                "total_messages": len(messages),
                "sms_count": 0,
                "whatsapp_count": 0,
                "delivered_count": 0,
                "failed_count": 0,
                "total_cost": 0.0,
                "daily_breakdown": {}
            }
            
            for message in messages:
                # Count by type
                if message.from_.startswith("whatsapp:"):
                    usage_stats["whatsapp_count"] += 1
                else:
                    usage_stats["sms_count"] += 1
                
                # Count by status
                if message.status in ["delivered", "read"]:
                    usage_stats["delivered_count"] += 1
                elif message.status in ["failed", "undelivered"]:
                    usage_stats["failed_count"] += 1
                
                # Add to cost
                if message.price:
                    usage_stats["total_cost"] += float(message.price)
                
                # Daily breakdown
                date_key = message.date_sent.strftime("%Y-%m-%d") if message.date_sent else "unknown"
                if date_key not in usage_stats["daily_breakdown"]:
                    usage_stats["daily_breakdown"][date_key] = 0
                usage_stats["daily_breakdown"][date_key] += 1
            
            # Calculate success rate
            if usage_stats["total_messages"] > 0:
                usage_stats["success_rate"] = (
                    usage_stats["delivered_count"] / usage_stats["total_messages"] * 100
                )
            else:
                usage_stats["success_rate"] = 0
            
            return usage_stats
            
        except Exception as e:
            print(f"Usage statistics error: {e}")
            return {"error": str(e)}
    
    def _format_phone_number(self, phone_number: str) -> Optional[str]:
        """Format phone number to E.164 format"""
        
        try:
            # Remove all non-digit characters except +
            cleaned = re.sub(r'[^\d+]', '', phone_number)
            
            # If it doesn't start with +, add +1 for US numbers
            if not cleaned.startswith('+'):
                if len(cleaned) == 10:  # US number without country code
                    cleaned = f"+1{cleaned}"
                elif len(cleaned) == 11 and cleaned.startswith('1'):  # US number with 1 prefix
                    cleaned = f"+{cleaned}"
                else:
                    # Try to add + to the beginning
                    cleaned = f"+{cleaned}"
            
            # Basic validation
            if len(cleaned) < 10 or len(cleaned) > 15:
                return None
            
            return cleaned
            
        except Exception as e:
            print(f"Phone number formatting error: {e}")
            return None
    
    async def send_bulk_sms(self, recipients: list, message: str) -> Dict[str, Any]:
        """Send SMS to multiple recipients"""
        
        results = {
            "total_recipients": len(recipients),
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        for recipient in recipients:
            result = await self.send_sms(recipient, message)
            
            if result.get("success"):
                results["successful"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "recipient": recipient,
                "success": result.get("success", False),
                "message_sid": result.get("message_sid"),
                "error": result.get("error")
            })
        
        results["success_rate"] = (results["successful"] / results["total_recipients"] * 100) if results["total_recipients"] > 0 else 0
        
        return results
    
    async def send_bulk_whatsapp(self, recipients: list, message: str) -> Dict[str, Any]:
        """Send WhatsApp message to multiple recipients"""
        
        results = {
            "total_recipients": len(recipients),
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        for recipient in recipients:
            result = await self.send_whatsapp(recipient, message)
            
            if result.get("success"):
                results["successful"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "recipient": recipient,
                "success": result.get("success", False),
                "message_sid": result.get("message_sid"),
                "error": result.get("error")
            })
        
        results["success_rate"] = (results["successful"] / results["total_recipients"] * 100) if results["total_recipients"] > 0 else 0
        
        return results