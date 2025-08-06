from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.payments import CreditTransaction, CREDIT_COSTS
from models.user import CreditBalance

class CreditService:
    """Service for managing user credits and consumption tracking"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.credit_costs = CREDIT_COSTS
    
    async def has_sufficient_credits(self, user_id: str, action_type: str) -> bool:
        """Check if user has sufficient credits for an action"""
        
        try:
            # Get user's current credit balance
            user = await self.db.users.find_one({"id": user_id})
            if not user:
                return False
            
            credits = user.get("credits", {})
            remaining_credits = credits.get("remaining_credits", 0)
            
            # Get cost for this action
            action_cost = self.credit_costs.get(action_type, 1)
            
            return remaining_credits >= action_cost
            
        except Exception as e:
            print(f"Credit check error: {e}")
            return False
    
    async def deduct_credits(
        self, 
        user_id: str, 
        action_type: str, 
        related_resource_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """Deduct credits for a specific action"""
        
        try:
            # Get cost for this action
            action_cost = self.credit_costs.get(action_type, 1)
            
            # Get current user credits
            user = await self.db.users.find_one({"id": user_id})
            if not user:
                return False
            
            credits = user.get("credits", {})
            current_remaining = credits.get("remaining_credits", 0)
            current_used = credits.get("used_credits", 0)
            
            # Check if sufficient credits
            if current_remaining < action_cost:
                return False
            
            # Update user credits
            new_remaining = current_remaining - action_cost
            new_used = current_used + action_cost
            
            await self.db.users.update_one(
                {"id": user_id},
                {
                    "$set": {
                        "credits.remaining_credits": new_remaining,
                        "credits.used_credits": new_used,
                        "credits.updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Create credit transaction record
            transaction = CreditTransaction(
                user_id=user_id,
                transaction_type="usage",
                credits_amount=-action_cost,  # Negative for usage
                description=description or f"Used credits for {action_type}",
                action_type=action_type,
                related_resource_id=related_resource_id
            )
            
            await self.db.credit_transactions.insert_one(transaction.dict())
            
            # Check if user needs credit refill warning
            if new_remaining <= 50:  # Low credit threshold
                await self._send_low_credit_notification(user_id, new_remaining)
            
            return True
            
        except Exception as e:
            print(f"Credit deduction error: {e}")
            return False
    
    async def add_credits(
        self,
        user_id: str,
        credits: int,
        transaction_type: str = "purchase",
        description: str = "Credit purchase",
        payment_intent_id: Optional[str] = None,
        stripe_invoice_id: Optional[str] = None
    ) -> bool:
        """Add credits to user account"""
        
        try:
            # Get current user credits
            user = await self.db.users.find_one({"id": user_id})
            if not user:
                return False
            
            current_credits = user.get("credits", {})
            current_total = current_credits.get("total_credits", 0)
            current_remaining = current_credits.get("remaining_credits", 0)
            
            # Calculate new totals
            new_total = current_total + credits
            new_remaining = current_remaining + credits
            
            # Set expiry date (12 months from now)
            expiry_date = datetime.utcnow() + timedelta(days=365)
            
            # Update user credits
            await self.db.users.update_one(
                {"id": user_id},
                {
                    "$set": {
                        "credits.total_credits": new_total,
                        "credits.remaining_credits": new_remaining,
                        "credits.last_purchase_date": datetime.utcnow(),
                        "credits.credit_expiry_date": expiry_date,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Create credit transaction record
            transaction = CreditTransaction(
                user_id=user_id,
                transaction_type=transaction_type,
                credits_amount=credits,  # Positive for addition
                description=description,
                payment_intent_id=payment_intent_id,
                stripe_payment_id=stripe_invoice_id
            )
            
            await self.db.credit_transactions.insert_one(transaction.dict())
            
            return True
            
        except Exception as e:
            print(f"Credit addition error: {e}")
            return False
    
    async def get_credit_balance(self, user_id: str) -> Dict[str, Any]:
        """Get user's current credit balance and history"""
        
        try:
            # Get user credits
            user = await self.db.users.find_one({"id": user_id})
            if not user:
                return {"error": "User not found"}
            
            credits = user.get("credits", {})
            
            # Get recent usage
            recent_usage = await self.db.credit_transactions.find(
                {
                    "user_id": user_id,
                    "transaction_type": "usage"
                }
            ).sort("created_at", -1).limit(10).to_list(None)
            
            # Get usage by action type
            usage_by_action = await self.db.credit_transactions.aggregate([
                {
                    "$match": {
                        "user_id": user_id,
                        "transaction_type": "usage"
                    }
                },
                {
                    "$group": {
                        "_id": "$action_type",
                        "total_credits": {"$sum": {"$abs": "$credits_amount"}},
                        "usage_count": {"$sum": 1}
                    }
                },
                {"$sort": {"total_credits": -1}}
            ]).to_list(None)
            
            return {
                "balance": CreditBalance(**credits).dict(),
                "recent_usage": recent_usage,
                "usage_by_action": usage_by_action,
                "low_credit_warning": credits.get("remaining_credits", 0) <= 50
            }
            
        except Exception as e:
            print(f"Credit balance retrieval error: {e}")
            return {"error": str(e)}
    
    async def get_usage_analytics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get detailed credit usage analytics"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Daily usage trends
            daily_usage = await self.db.credit_transactions.aggregate([
                {
                    "$match": {
                        "user_id": user_id,
                        "transaction_type": "usage",
                        "created_at": {"$gte": start_date}
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": "$created_at"
                            }
                        },
                        "credits_used": {"$sum": {"$abs": "$credits_amount"}},
                        "action_count": {"$sum": 1}
                    }
                },
                {"$sort": {"_id": 1}}
            ]).to_list(None)
            
            # Usage by action type
            action_usage = await self.db.credit_transactions.aggregate([
                {
                    "$match": {
                        "user_id": user_id,
                        "transaction_type": "usage",
                        "created_at": {"$gte": start_date}
                    }
                },
                {
                    "$group": {
                        "_id": "$action_type",
                        "total_credits": {"$sum": {"$abs": "$credits_amount"}},
                        "usage_count": {"$sum": 1},
                        "avg_credits_per_use": {"$avg": {"$abs": "$credits_amount"}}
                    }
                },
                {"$sort": {"total_credits": -1}}
            ]).to_list(None)
            
            # Usage efficiency (credits per day)
            total_credits_used = sum(day["credits_used"] for day in daily_usage)
            avg_daily_usage = total_credits_used / max(len(daily_usage), 1)
            
            # Predict monthly usage
            if len(daily_usage) >= 7:
                recent_week_avg = sum(day["credits_used"] for day in daily_usage[-7:]) / 7
                predicted_monthly = recent_week_avg * 30
            else:
                predicted_monthly = avg_daily_usage * 30
            
            return {
                "period_days": days,
                "total_credits_used": total_credits_used,
                "avg_daily_usage": round(avg_daily_usage, 2),
                "predicted_monthly_usage": round(predicted_monthly, 2),
                "daily_usage_trend": daily_usage,
                "usage_by_action": action_usage,
                "most_used_action": action_usage[0]["_id"] if action_usage else None,
                "efficiency_score": self._calculate_efficiency_score(action_usage)
            }
            
        except Exception as e:
            print(f"Usage analytics error: {e}")
            return {"error": str(e)}
    
    async def process_expired_credits(self) -> Dict[str, Any]:
        """Process expired credits across all users"""
        
        try:
            now = datetime.utcnow()
            processed_count = 0
            
            # Find users with expired credits
            users_with_expired_credits = await self.db.users.find({
                "credits.credit_expiry_date": {"$lt": now},
                "credits.remaining_credits": {"$gt": 0}
            }).to_list(None)
            
            for user in users_with_expired_credits:
                user_id = user["id"]
                expired_credits = user.get("credits", {}).get("remaining_credits", 0)
                
                if expired_credits > 0:
                    # Reset remaining credits to 0
                    await self.db.users.update_one(
                        {"id": user_id},
                        {
                            "$set": {
                                "credits.remaining_credits": 0,
                                "updated_at": now
                            }
                        }
                    )
                    
                    # Create expiry transaction
                    transaction = CreditTransaction(
                        user_id=user_id,
                        transaction_type="expiry",
                        credits_amount=-expired_credits,
                        description=f"Credits expired - {expired_credits} credits removed"
                    )
                    
                    await self.db.credit_transactions.insert_one(transaction.dict())
                    
                    # Send expiry notification
                    await self._send_credit_expiry_notification(user_id, expired_credits)
                    
                    processed_count += 1
            
            return {
                "processed_users": processed_count,
                "timestamp": now
            }
            
        except Exception as e:
            print(f"Credit expiry processing error: {e}")
            return {"error": str(e)}
    
    async def estimate_action_cost(self, action_type: str, complexity_factor: float = 1.0) -> int:
        """Estimate cost for an action with complexity factor"""
        
        base_cost = self.credit_costs.get(action_type, 1)
        estimated_cost = int(base_cost * complexity_factor)
        
        return max(1, estimated_cost)  # Minimum 1 credit
    
    async def get_credit_recommendations(self, user_id: str) -> Dict[str, Any]:
        """Get personalized credit purchase recommendations"""
        
        try:
            # Get usage analytics
            analytics = await self.get_usage_analytics(user_id, days=30)
            
            if "error" in analytics:
                return analytics
            
            # Get current balance
            balance_info = await self.get_credit_balance(user_id)
            remaining_credits = balance_info["balance"]["remaining_credits"]
            
            # Calculate recommendations
            predicted_monthly = analytics.get("predicted_monthly_usage", 100)
            
            recommendations = []
            
            if remaining_credits < predicted_monthly * 0.5:
                # User needs credits soon
                if predicted_monthly <= 500:
                    recommendations.append({
                        "package": "starter",
                        "reason": "Perfect for your usage pattern",
                        "credits": 500,
                        "estimated_duration": "1-2 months"
                    })
                elif predicted_monthly <= 2000:
                    recommendations.append({
                        "package": "professional",
                        "reason": "Best value for your usage level",
                        "credits": 2000,
                        "estimated_duration": "1 month"
                    })
                else:
                    recommendations.append({
                        "package": "enterprise",
                        "reason": "Heavy usage requires enterprise package",
                        "credits": 10000,
                        "estimated_duration": "4-5 months"
                    })
            
            elif remaining_credits < predicted_monthly * 0.2:
                recommendations.append({
                    "package": "starter",
                    "reason": "Top up recommended",
                    "credits": 500,
                    "estimated_duration": "2-3 weeks"
                })
            
            return {
                "recommendations": recommendations,
                "current_remaining": remaining_credits,
                "predicted_monthly_usage": predicted_monthly,
                "urgency": "high" if remaining_credits < 50 else "low"
            }
            
        except Exception as e:
            print(f"Credit recommendations error: {e}")
            return {"error": str(e)}
    
    def _calculate_efficiency_score(self, action_usage: list) -> float:
        """Calculate efficiency score based on action usage patterns"""
        
        try:
            if not action_usage:
                return 0.0
            
            # Weight different actions by their business value
            action_weights = {
                "email_processing": 1.0,
                "draft_generation": 1.5,
                "smart_scheduling": 1.2,
                "calendar_analysis": 0.8,
                "urgent_notification": 0.5,
                "ai_analysis": 1.0
            }
            
            weighted_score = 0.0
            total_credits = 0
            
            for usage in action_usage:
                action_type = usage["_id"]
                credits_used = usage["total_credits"]
                weight = action_weights.get(action_type, 0.5)
                
                weighted_score += credits_used * weight
                total_credits += credits_used
            
            if total_credits == 0:
                return 0.0
            
            # Normalize to 0-100 scale
            efficiency = (weighted_score / total_credits) * 100
            return min(100.0, efficiency)
            
        except Exception as e:
            print(f"Efficiency calculation error: {e}")
            return 0.0
    
    async def _send_low_credit_notification(self, user_id: str, remaining_credits: int):
        """Send notification when user has low credits"""
        
        try:
            # This would integrate with the notification service
            # For now, just create a notification record
            from models.notifications import Notification, NotificationType, NotificationPriority, NotificationContent
            
            notification = Notification(
                user_id=user_id,
                type=NotificationType.CREDIT_LOW,
                priority=NotificationPriority.HIGH,
                content=NotificationContent(
                    title="Low Credit Warning",
                    message=f"You have {remaining_credits} credits remaining. Consider purchasing more credits to continue using Jessica's features.",
                    metadata={"remaining_credits": remaining_credits}
                ),
                preferred_channels=["email", "in_app"]
            )
            
            await self.db.notifications.insert_one(notification.dict())
            
        except Exception as e:
            print(f"Low credit notification error: {e}")
    
    async def _send_credit_expiry_notification(self, user_id: str, expired_credits: int):
        """Send notification when credits expire"""
        
        try:
            from models.notifications import Notification, NotificationType, NotificationPriority, NotificationContent
            
            notification = Notification(
                user_id=user_id,
                type=NotificationType.SYSTEM_UPDATE,
                priority=NotificationPriority.NORMAL,
                content=NotificationContent(
                    title="Credits Expired",
                    message=f"{expired_credits} credits have expired. Purchase new credits to continue using Jessica's features.",
                    metadata={"expired_credits": expired_credits}
                ),
                preferred_channels=["email", "in_app"]
            )
            
            await self.db.notifications.insert_one(notification.dict())
            
        except Exception as e:
            print(f"Credit expiry notification error: {e}")