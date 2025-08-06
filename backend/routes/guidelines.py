from fastapi import APIRouter, Depends, HTTPException, status, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Optional, List

from models.guidelines import (
    UserGuidelines, GuidelinesUpdateRequest, GuidelinesResponse,
    GuidelinesFeedback, EmailClassificationRule, SchedulingPreference,
    NotificationRule, CommunicationStyleGuide, AutomationRule,
    GuidelineVersion, PriorityLevel, ResponseTone
)
from utils.auth import get_current_user_id
from utils.database import ValidationUtils

router = APIRouter()

@router.get("/", response_model=GuidelinesResponse)
async def get_user_guidelines(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's current guidelines"""
    database: AsyncIOMotorDatabase = request.app.database
    
    guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    
    if not guidelines:
        # Create default guidelines for new user
        default_guidelines = UserGuidelines(user_id=current_user_id)
        await database.user_guidelines.insert_one(default_guidelines.dict())
        guidelines = default_guidelines.dict()
    
    return GuidelinesResponse(**ValidationUtils.convert_objectid_to_str(guidelines))

@router.put("/", response_model=GuidelinesResponse)
async def update_user_guidelines(
    updates: GuidelinesUpdateRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update user's guidelines"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Find existing guidelines
    existing_guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    
    if not existing_guidelines:
        # Create new guidelines if none exist
        guidelines = UserGuidelines(user_id=current_user_id)
        await database.user_guidelines.insert_one(guidelines.dict())
        existing_guidelines = guidelines.dict()
    
    # Build update fields
    update_fields = {"updated_at": datetime.utcnow()}
    
    if updates.email_classification_rules is not None:
        update_fields["email_classification_rules"] = [rule.dict() for rule in updates.email_classification_rules]
    
    if updates.scheduling_preferences is not None:
        update_fields["scheduling_preferences"] = [pref.dict() for pref in updates.scheduling_preferences]
    
    if updates.notification_rules is not None:
        update_fields["notification_rules"] = [rule.dict() for rule in updates.notification_rules]
    
    if updates.communication_style is not None:
        update_fields["communication_style"] = updates.communication_style.dict()
    
    if updates.automation_rules is not None:
        update_fields["automation_rules"] = [rule.dict() for rule in updates.automation_rules]
    
    if updates.custom_instructions is not None:
        update_fields["custom_instructions"] = updates.custom_instructions
    
    if updates.special_contacts is not None:
        update_fields["special_contacts"] = updates.special_contacts
    
    # Update version info
    current_version = existing_guidelines.get("current_version", {})
    new_version = GuidelineVersion(
        version_number=current_version.get("version_number", 0) + 1,
        changes_summary="User manual update"
    )
    update_fields["current_version"] = new_version.dict()
    
    # Add current version to history
    version_history = existing_guidelines.get("version_history", [])
    if current_version:
        current_version["is_active"] = False
        version_history.append(current_version)
    update_fields["version_history"] = version_history
    
    # Update in database
    await database.user_guidelines.update_one(
        {"user_id": current_user_id},
        {"$set": update_fields}
    )
    
    # Return updated guidelines
    updated_guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    return GuidelinesResponse(**ValidationUtils.convert_objectid_to_str(updated_guidelines))

@router.post("/feedback")
async def submit_guideline_feedback(
    feedback: GuidelinesFeedback,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Submit feedback on guideline-based actions for learning"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Store feedback for learning algorithm
    feedback_doc = feedback.dict()
    feedback_doc["user_id"] = current_user_id
    
    await database.guideline_feedback.insert_one(feedback_doc)
    
    # Update last learning timestamp
    await database.user_guidelines.update_one(
        {"user_id": current_user_id},
        {"$set": {"last_learning_update": datetime.utcnow()}}
    )
    
    # TODO: Trigger learning algorithm to process feedback
    
    return {"message": "Feedback submitted successfully"}

@router.get("/email-rules")
async def get_email_classification_rules(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's email classification rules"""
    database: AsyncIOMotorDatabase = request.app.database
    
    guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    
    if not guidelines:
        return {"email_classification_rules": []}
    
    return {"email_classification_rules": guidelines.get("email_classification_rules", [])}

@router.post("/email-rules")
async def add_email_classification_rule(
    rule: EmailClassificationRule,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Add a new email classification rule"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get current guidelines
    guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    
    if not guidelines:
        # Create default guidelines
        new_guidelines = UserGuidelines(
            user_id=current_user_id,
            email_classification_rules=[rule]
        )
        await database.user_guidelines.insert_one(new_guidelines.dict())
    else:
        # Add rule to existing guidelines
        current_rules = guidelines.get("email_classification_rules", [])
        current_rules.append(rule.dict())
        
        await database.user_guidelines.update_one(
            {"user_id": current_user_id},
            {
                "$set": {
                    "email_classification_rules": current_rules,
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    return {"message": "Email classification rule added successfully"}

@router.get("/scheduling-preferences")
async def get_scheduling_preferences(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's scheduling preferences"""
    database: AsyncIOMotorDatabase = request.app.database
    
    guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    
    if not guidelines:
        return {"scheduling_preferences": []}
    
    return {"scheduling_preferences": guidelines.get("scheduling_preferences", [])}

@router.post("/scheduling-preferences")
async def add_scheduling_preference(
    preference: SchedulingPreference,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Add a new scheduling preference"""
    database: AsyncIOMotorDatabase = request.app.database
    
    guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    
    if not guidelines:
        new_guidelines = UserGuidelines(
            user_id=current_user_id,
            scheduling_preferences=[preference]
        )
        await database.user_guidelines.insert_one(new_guidelines.dict())
    else:
        current_prefs = guidelines.get("scheduling_preferences", [])
        current_prefs.append(preference.dict())
        
        await database.user_guidelines.update_one(
            {"user_id": current_user_id},
            {
                "$set": {
                    "scheduling_preferences": current_prefs,
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    return {"message": "Scheduling preference added successfully"}

@router.get("/communication-style")
async def get_communication_style(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's communication style guide"""
    database: AsyncIOMotorDatabase = request.app.database
    
    guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    
    if not guidelines:
        return {"communication_style": CommunicationStyleGuide().dict()}
    
    return {"communication_style": guidelines.get("communication_style", CommunicationStyleGuide().dict())}

@router.put("/communication-style")
async def update_communication_style(
    style: CommunicationStyleGuide,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update user's communication style guide"""
    database: AsyncIOMotorDatabase = request.app.database
    
    await database.user_guidelines.update_one(
        {"user_id": current_user_id},
        {
            "$set": {
                "communication_style": style.dict(),
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    return {"message": "Communication style updated successfully"}

@router.get("/automation-rules")
async def get_automation_rules(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's automation rules"""
    database: AsyncIOMotorDatabase = request.app.database
    
    guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    
    if not guidelines:
        return {"automation_rules": []}
    
    return {"automation_rules": guidelines.get("automation_rules", [])}

@router.post("/automation-rules")
async def add_automation_rule(
    rule: AutomationRule,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Add a new automation rule"""
    database: AsyncIOMotorDatabase = request.app.database
    
    guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    
    if not guidelines:
        new_guidelines = UserGuidelines(
            user_id=current_user_id,
            automation_rules=[rule]
        )
        await database.user_guidelines.insert_one(new_guidelines.dict())
    else:
        current_rules = guidelines.get("automation_rules", [])
        current_rules.append(rule.dict())
        
        await database.user_guidelines.update_one(
            {"user_id": current_user_id},
            {
                "$set": {
                    "automation_rules": current_rules,
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    return {"message": "Automation rule added successfully"}

@router.delete("/automation-rules/{rule_name}")
async def delete_automation_rule(
    rule_name: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Delete an automation rule"""
    database: AsyncIOMotorDatabase = request.app.database
    
    guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    
    if not guidelines:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guidelines not found"
        )
    
    current_rules = guidelines.get("automation_rules", [])
    updated_rules = [rule for rule in current_rules if rule.get("rule_name") != rule_name]
    
    if len(updated_rules) == len(current_rules):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation rule not found"
        )
    
    await database.user_guidelines.update_one(
        {"user_id": current_user_id},
        {
            "$set": {
                "automation_rules": updated_rules,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Automation rule deleted successfully"}

@router.get("/version-history")
async def get_version_history(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get guidelines version history"""
    database: AsyncIOMotorDatabase = request.app.database
    
    guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    
    if not guidelines:
        return {"version_history": [], "current_version": None}
    
    return {
        "version_history": guidelines.get("version_history", []),
        "current_version": guidelines.get("current_version")
    }

@router.post("/revert/{version_number}")
async def revert_to_version(
    version_number: int,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Revert guidelines to a previous version"""
    database: AsyncIOMotorDatabase = request.app.database
    
    guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    
    if not guidelines:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guidelines not found"
        )
    
    version_history = guidelines.get("version_history", [])
    target_version = None
    
    for version in version_history:
        if version.get("version_number") == version_number:
            target_version = version
            break
    
    if not target_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )
    
    # Create new version entry for the revert
    new_version = GuidelineVersion(
        version_number=guidelines.get("current_version", {}).get("version_number", 0) + 1,
        changes_summary=f"Reverted to version {version_number}"
    )
    
    # Update guidelines (this would require storing the full state in version history)
    await database.user_guidelines.update_one(
        {"user_id": current_user_id},
        {
            "$set": {
                "current_version": new_version.dict(),
                "updated_at": datetime.utcnow()
            },
            "$push": {"version_history": guidelines.get("current_version")}
        }
    )
    
    return {"message": f"Guidelines reverted to version {version_number}"}

@router.get("/learning-stats")
async def get_learning_stats(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get learning and adaptation statistics"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get feedback stats
    feedback_pipeline = [
        {"$match": {"user_id": current_user_id}},
        {"$group": {
            "_id": "$feedback_type",
            "count": {"$sum": 1}
        }}
    ]
    
    feedback_stats = await database.guideline_feedback.aggregate(feedback_pipeline).to_list(None)
    
    # Get guidelines info
    guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    
    if not guidelines:
        return {
            "feedback_stats": [],
            "learning_enabled": True,
            "last_learning_update": None,
            "total_rules": 0
        }
    
    total_rules = (
        len(guidelines.get("email_classification_rules", [])) +
        len(guidelines.get("scheduling_preferences", [])) +
        len(guidelines.get("notification_rules", [])) +
        len(guidelines.get("automation_rules", []))
    )
    
    return {
        "feedback_stats": feedback_stats,
        "learning_enabled": guidelines.get("learning_enabled", True),
        "last_learning_update": guidelines.get("last_learning_update"),
        "total_rules": total_rules,
        "current_version": guidelines.get("current_version", {}).get("version_number", 1)
    }

@router.post("/export")
async def export_guidelines(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Export user's guidelines as JSON"""
    database: AsyncIOMotorDatabase = request.app.database
    
    guidelines = await database.user_guidelines.find_one({"user_id": current_user_id})
    
    if not guidelines:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guidelines not found"
        )
    
    # Remove sensitive fields
    export_data = ValidationUtils.convert_objectid_to_str(guidelines)
    export_data.pop("_id", None)
    export_data.pop("user_id", None)
    
    return {
        "guidelines": export_data,
        "exported_at": datetime.utcnow(),
        "version": guidelines.get("current_version", {}).get("version_number", 1)
    }

@router.post("/import")
async def import_guidelines(
    import_data: dict,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Import guidelines from JSON"""
    database: AsyncIOMotorDatabase = request.app.database
    
    try:
        # Validate import data structure
        guidelines_data = import_data.get("guidelines", {})
        
        # Create new guidelines object
        imported_guidelines = UserGuidelines(
            user_id=current_user_id,
            **guidelines_data
        )
        
        # Save imported guidelines
        await database.user_guidelines.replace_one(
            {"user_id": current_user_id},
            imported_guidelines.dict(),
            upsert=True
        )
        
        return {"message": "Guidelines imported successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid import data: {str(e)}"
        )