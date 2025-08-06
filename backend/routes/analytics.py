from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from utils.auth import get_current_user_id
from utils.database import ValidationUtils

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_analytics(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get comprehensive dashboard analytics"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Date range for analytics
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Email analytics
    email_stats = await get_email_analytics(database, current_user_id, start_date)
    
    # Calendar analytics
    calendar_stats = await get_calendar_analytics(database, current_user_id, start_date)
    
    # Credit usage analytics
    credit_stats = await get_credit_analytics(database, current_user_id, start_date)
    
    # AI processing analytics
    ai_stats = await get_ai_analytics(database, current_user_id, start_date)
    
    # Notification analytics
    notification_stats = await get_notification_analytics(database, current_user_id, start_date)
    
    # Productivity metrics
    productivity_stats = await get_productivity_metrics(database, current_user_id, start_date)
    
    return {
        "period": {
            "days": days,
            "start_date": start_date,
            "end_date": datetime.utcnow()
        },
        "email_analytics": email_stats,
        "calendar_analytics": calendar_stats,
        "credit_analytics": credit_stats,
        "ai_analytics": ai_stats,
        "notification_analytics": notification_stats,
        "productivity_metrics": productivity_stats
    }

@router.get("/email-insights")
async def get_email_insights(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get detailed email insights and patterns"""
    database: AsyncIOMotorDatabase = request.app.database
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Email volume trends
    email_trends = await database.emails.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "received_at": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$received_at"
                    }
                },
                "total": {"$sum": 1},
                "unread": {
                    "$sum": {"$cond": [{"$eq": ["$status", "unread"]}, 1, 0]}
                },
                "urgent": {
                    "$sum": {"$cond": [{"$eq": ["$priority", "urgent"]}, 1, 0]}
                }
            }
        },
        {"$sort": {"_id": 1}}
    ]).to_list(None)
    
    # Sender analysis
    top_senders = await database.emails.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "received_at": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": "$sender.email",
                "count": {"$sum": 1},
                "urgent_count": {
                    "$sum": {"$cond": [{"$eq": ["$priority", "urgent"]}, 1, 0]}
                }
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]).to_list(None)
    
    # Response time analysis
    response_times = await database.emails.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "status": "replied",
                "received_at": {"$gte": start_date}
            }
        },
        {
            "$lookup": {
                "from": "email_drafts",
                "localField": "id",
                "foreignField": "original_email_id",
                "as": "drafts"
            }
        },
        {
            "$match": {
                "drafts.is_sent": True
            }
        },
        {
            "$addFields": {
                "response_time_hours": {
                    "$divide": [
                        {"$subtract": [{"$first": "$drafts.sent_at"}, "$received_at"]},
                        3600000
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": None,
                "avg_response_time": {"$avg": "$response_time_hours"},
                "median_response_time": {"$median": "$response_time_hours"},
                "fast_responses": {
                    "$sum": {"$cond": [{"$lt": ["$response_time_hours", 2]}, 1, 0]}
                },
                "total_responses": {"$sum": 1}
            }
        }
    ]).to_list(None)
    
    # Email classification accuracy
    classification_stats = await database.emails.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "ai_analysis": {"$exists": True},
                "processing_status": "completed"
            }
        },
        {
            "$group": {
                "_id": "$priority",
                "count": {"$sum": 1},
                "avg_confidence": {"$avg": "$ai_analysis.confidence_score"}
            }
        }
    ]).to_list(None)
    
    return {
        "email_trends": email_trends,
        "top_senders": top_senders,
        "response_analysis": response_times[0] if response_times else {},
        "classification_stats": classification_stats,
        "period_days": days
    }

@router.get("/calendar-insights")
async def get_calendar_insights(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get detailed calendar insights and patterns"""
    database: AsyncIOMotorDatabase = request.app.database
    
    start_date = datetime.utcnow() - timedelta(days=days)
    end_date = datetime.utcnow() + timedelta(days=7)  # Include future events
    
    # Meeting patterns
    meeting_patterns = await database.calendar_events.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "start_datetime": {"$gte": start_date, "$lte": end_date}
            }
        },
        {
            "$addFields": {
                "hour": {"$hour": "$start_datetime"},
                "day_of_week": {"$dayOfWeek": "$start_datetime"},
                "duration_minutes": {
                    "$divide": [
                        {"$subtract": ["$end_datetime", "$start_datetime"]},
                        60000
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "hour": "$hour",
                    "day": "$day_of_week"
                },
                "meeting_count": {"$sum": 1},
                "avg_duration": {"$avg": "$duration_minutes"}
            }
        }
    ]).to_list(None)
    
    # Meeting efficiency metrics
    efficiency_metrics = await database.calendar_events.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "start_datetime": {"$gte": start_date}
            }
        },
        {
            "$addFields": {
                "duration_minutes": {
                    "$divide": [
                        {"$subtract": ["$end_datetime", "$start_datetime"]},
                        60000
                    ]
                },
                "attendee_count": {"$size": "$attendees"}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_meeting_time": {"$sum": "$duration_minutes"},
                "avg_meeting_duration": {"$avg": "$duration_minutes"},
                "total_meetings": {"$sum": 1},
                "avg_attendees": {"$avg": "$attendee_count"},
                "meetings_with_ai_analysis": {
                    "$sum": {"$cond": [{"$exists": ["$ai_analysis", True]}, 1, 0]}
                }
            }
        }
    ]).to_list(None)
    
    # Scheduling conflicts
    conflicts = await database.calendar_events.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "ai_analysis.conflicts_detected": {"$exists": True, "$ne": []}
            }
        },
        {
            "$unwind": "$ai_analysis.conflicts_detected"
        },
        {
            "$group": {
                "_id": "$ai_analysis.conflicts_detected.conflict_type",
                "count": {"$sum": 1}
            }
        }
    ]).to_list(None)
    
    # Most frequent attendees
    frequent_attendees = await database.calendar_events.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "start_datetime": {"$gte": start_date}
            }
        },
        {"$unwind": "$attendees"},
        {
            "$group": {
                "_id": "$attendees.email",
                "meeting_count": {"$sum": 1},
                "accepted_meetings": {
                    "$sum": {"$cond": [{"$eq": ["$attendees.status", "accepted"]}, 1, 0]}
                }
            }
        },
        {"$sort": {"meeting_count": -1}},
        {"$limit": 15}
    ]).to_list(None)
    
    return {
        "meeting_patterns": meeting_patterns,
        "efficiency_metrics": efficiency_metrics[0] if efficiency_metrics else {},
        "conflicts_analysis": conflicts,
        "frequent_attendees": frequent_attendees,
        "period_days": days
    }

@router.get("/ai-performance")
async def get_ai_performance_metrics(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get AI performance and accuracy metrics"""
    database: AsyncIOMotorDatabase = request.app.database
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Email classification performance
    email_classification = await database.emails.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "ai_analysis": {"$exists": True},
                "processed_at": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": "$priority",
                "count": {"$sum": 1},
                "avg_confidence": {"$avg": "$ai_analysis.confidence_score"},
                "avg_urgency_score": {"$avg": "$ai_analysis.urgency_score"}
            }
        }
    ]).to_list(None)
    
    # Draft generation metrics
    draft_metrics = await database.email_drafts.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "generated_by_ai": True,
                "created_at": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_drafts": {"$sum": 1},
                "sent_drafts": {
                    "$sum": {"$cond": ["$is_sent", 1, 0]}
                },
                "avg_confidence": {"$avg": "$ai_confidence"},
                "modified_drafts": {
                    "$sum": {"$cond": [{"$gt": [{"$size": "$user_modifications"}, 0]}, 1, 0]}
                }
            }
        }
    ]).to_list(None)
    
    # User feedback analysis
    feedback_analysis = await database.guideline_feedback.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "timestamp": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": "$feedback_type",
                "count": {"$sum": 1}
            }
        }
    ]).to_list(None)
    
    # Processing time analysis
    processing_times = await database.emails.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "processing_status": "completed",
                "processed_at": {"$gte": start_date}
            }
        },
        {
            "$addFields": {
                "processing_time_seconds": {
                    "$divide": [
                        {"$subtract": ["$processed_at", "$created_at"]},
                        1000
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": None,
                "avg_processing_time": {"$avg": "$processing_time_seconds"},
                "max_processing_time": {"$max": "$processing_time_seconds"},
                "min_processing_time": {"$min": "$processing_time_seconds"}
            }
        }
    ]).to_list(None)
    
    return {
        "email_classification": email_classification,
        "draft_generation": draft_metrics[0] if draft_metrics else {},
        "user_feedback": feedback_analysis,
        "processing_performance": processing_times[0] if processing_times else {},
        "period_days": days
    }

@router.get("/productivity-score")
async def get_productivity_score(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    current_user_id: str = Depends(get_current_user_id)
):
    """Calculate and return user's productivity score"""
    database: AsyncIOMotorDatabase = request.app.database
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get user activity stats
    user = await database.users.find_one({"id": current_user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    activity = user.get("activity", {})
    
    # Calculate component scores (0-100)
    scores = {}
    
    # Email efficiency score
    emails_processed = activity.get("emails_processed", 0)
    email_score = min(100, (emails_processed / 100) * 100)  # 100 emails = 100%
    scores["email_efficiency"] = email_score
    
    # Response time score (based on quick responses)
    quick_responses = await database.emails.count_documents({
        "user_id": current_user_id,
        "status": "replied",
        "received_at": {"$gte": start_date}
    })
    response_score = min(100, (quick_responses / 50) * 100)  # 50 quick responses = 100%
    scores["response_speed"] = response_score
    
    # AI utilization score
    ai_actions = activity.get("drafts_generated", 0) + emails_processed
    ai_score = min(100, (ai_actions / 200) * 100)  # 200 AI actions = 100%
    scores["ai_utilization"] = ai_score
    
    # Calendar optimization score
    meetings_scheduled = activity.get("meetings_scheduled", 0)
    calendar_score = min(100, (meetings_scheduled / 30) * 100)  # 30 meetings = 100%
    scores["calendar_optimization"] = calendar_score
    
    # Automation adoption score
    notifications_sent = activity.get("notifications_sent", 0)
    automation_score = min(100, (notifications_sent / 100) * 100)  # 100 notifications = 100%
    scores["automation_adoption"] = automation_score
    
    # Calculate overall productivity score (weighted average)
    weights = {
        "email_efficiency": 0.3,
        "response_speed": 0.25,
        "ai_utilization": 0.2,
        "calendar_optimization": 0.15,
        "automation_adoption": 0.1
    }
    
    overall_score = sum(scores[key] * weights[key] for key in scores.keys())
    
    # Determine productivity level
    if overall_score >= 80:
        level = "Expert"
        level_description = "You're maximizing Jessica's potential!"
    elif overall_score >= 60:
        level = "Advanced"
        level_description = "Great progress! Keep optimizing your workflow."
    elif overall_score >= 40:
        level = "Intermediate"
        level_description = "You're getting the hang of it. Try more features."
    elif overall_score >= 20:
        level = "Beginner"
        level_description = "Good start! Explore more automation options."
    else:
        level = "New User"
        level_description = "Welcome! Let's get you started with Jessica."
    
    # Get improvement suggestions
    suggestions = []
    if scores["email_efficiency"] < 50:
        suggestions.append("Process more emails with AI analysis to improve efficiency")
    if scores["response_speed"] < 50:
        suggestions.append("Use AI draft generation to respond faster")
    if scores["ai_utilization"] < 50:
        suggestions.append("Try more AI features like smart scheduling and auto-replies")
    if scores["calendar_optimization"] < 50:
        suggestions.append("Let Jessica optimize your meeting schedules")
    
    return {
        "overall_score": round(overall_score, 1),
        "level": level,
        "level_description": level_description,
        "component_scores": {k: round(v, 1) for k, v in scores.items()},
        "improvement_suggestions": suggestions,
        "time_saved_minutes": activity.get("total_time_saved_minutes", 0),
        "period_days": days,
        "last_updated": datetime.utcnow()
    }

@router.get("/trends")
async def get_usage_trends(
    request: Request,
    metric: str = Query(..., description="Metric to analyze (emails, meetings, credits, etc.)"),
    days: int = Query(30, ge=7, le=365),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get usage trends for specific metrics"""
    database: AsyncIOMotorDatabase = request.app.database
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    if metric == "emails":
        trend_data = await database.emails.aggregate([
            {
                "$match": {
                    "user_id": current_user_id,
                    "received_at": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$received_at"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]).to_list(None)
    
    elif metric == "meetings":
        trend_data = await database.calendar_events.aggregate([
            {
                "$match": {
                    "user_id": current_user_id,
                    "start_datetime": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$start_datetime"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]).to_list(None)
    
    elif metric == "credits":
        trend_data = await database.credit_transactions.aggregate([
            {
                "$match": {
                    "user_id": current_user_id,
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
                    "credits_used": {"$sum": {"$abs": "$credits_amount"}}
                }
            },
            {"$sort": {"_id": 1}}
        ]).to_list(None)
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid metric. Choose from: emails, meetings, credits"
        )
    
    # Calculate trend direction
    if len(trend_data) >= 2:
        recent_avg = sum(item.get("count", item.get("credits_used", 0)) 
                        for item in trend_data[-7:]) / min(7, len(trend_data))
        earlier_avg = sum(item.get("count", item.get("credits_used", 0)) 
                         for item in trend_data[:7]) / min(7, len(trend_data))
        
        if recent_avg > earlier_avg * 1.1:
            trend_direction = "increasing"
        elif recent_avg < earlier_avg * 0.9:
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"
    else:
        trend_direction = "insufficient_data"
    
    return {
        "metric": metric,
        "trend_data": trend_data,
        "trend_direction": trend_direction,
        "period_days": days,
        "data_points": len(trend_data)
    }

# Helper functions
async def get_email_analytics(database: AsyncIOMotorDatabase, user_id: str, start_date: datetime):
    """Get email analytics for dashboard"""
    total_emails = await database.emails.count_documents({"user_id": user_id})
    recent_emails = await database.emails.count_documents({
        "user_id": user_id,
        "received_at": {"$gte": start_date}
    })
    unread_emails = await database.emails.count_documents({
        "user_id": user_id,
        "status": "unread"
    })
    
    return {
        "total_emails": total_emails,
        "recent_emails": recent_emails,
        "unread_emails": unread_emails,
        "unread_percentage": (unread_emails / max(total_emails, 1)) * 100
    }

async def get_calendar_analytics(database: AsyncIOMotorDatabase, user_id: str, start_date: datetime):
    """Get calendar analytics for dashboard"""
    upcoming_events = await database.calendar_events.count_documents({
        "user_id": user_id,
        "start_datetime": {"$gte": datetime.utcnow()}
    })
    recent_events = await database.calendar_events.count_documents({
        "user_id": user_id,
        "start_datetime": {"$gte": start_date}
    })
    
    return {
        "upcoming_events": upcoming_events,
        "recent_events": recent_events
    }

async def get_credit_analytics(database: AsyncIOMotorDatabase, user_id: str, start_date: datetime):
    """Get credit analytics for dashboard"""
    user = await database.users.find_one({"id": user_id})
    credits = user.get("credits", {}) if user else {}
    
    recent_usage = await database.credit_transactions.aggregate([
        {
            "$match": {
                "user_id": user_id,
                "transaction_type": "usage",
                "created_at": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_used": {"$sum": {"$abs": "$credits_amount"}}
            }
        }
    ]).to_list(None)
    
    return {
        "remaining_credits": credits.get("remaining_credits", 0),
        "recent_usage": recent_usage[0]["total_used"] if recent_usage else 0
    }

async def get_ai_analytics(database: AsyncIOMotorDatabase, user_id: str, start_date: datetime):
    """Get AI analytics for dashboard"""
    processed_emails = await database.emails.count_documents({
        "user_id": user_id,
        "processing_status": "completed",
        "processed_at": {"$gte": start_date}
    })
    
    generated_drafts = await database.email_drafts.count_documents({
        "user_id": user_id,
        "generated_by_ai": True,
        "created_at": {"$gte": start_date}
    })
    
    return {
        "processed_emails": processed_emails,
        "generated_drafts": generated_drafts
    }

async def get_notification_analytics(database: AsyncIOMotorDatabase, user_id: str, start_date: datetime):
    """Get notification analytics for dashboard"""
    total_notifications = await database.notifications.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": start_date}
    })
    
    urgent_notifications = await database.notifications.count_documents({
        "user_id": user_id,
        "type": "urgent_email",
        "created_at": {"$gte": start_date}
    })
    
    return {
        "total_notifications": total_notifications,
        "urgent_notifications": urgent_notifications
    }

async def get_productivity_metrics(database: AsyncIOMotorDatabase, user_id: str, start_date: datetime):
    """Get productivity metrics for dashboard"""
    user = await database.users.find_one({"id": user_id})
    activity = user.get("activity", {}) if user else {}
    
    return {
        "time_saved_minutes": activity.get("total_time_saved_minutes", 0),
        "emails_processed": activity.get("emails_processed", 0),
        "drafts_generated": activity.get("drafts_generated", 0),
        "meetings_scheduled": activity.get("meetings_scheduled", 0)
    }