import openai
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from decouple import config

class AIService:
    """Service for AI-powered email analysis and automation"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=config('OPENAI_API_KEY', default='sk-placeholder'))
        self.model = "gpt-4o"  # Using latest model
    
    async def analyze_email_content(
        self, 
        subject: str,
        body_text: str,
        sender_email: str,
        sender_name: Optional[str] = None,
        user_guidelines: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze email content for classification and insights"""
        
        try:
            # Prepare context from user guidelines
            guidelines_context = ""
            if user_guidelines:
                email_rules = user_guidelines.get("email_classification_rules", [])
                if email_rules:
                    guidelines_context = f"\nUser's email classification preferences: {json.dumps(email_rules, indent=2)}"
            
            # Create analysis prompt
            prompt = f"""
You are Jessica, an AI email assistant. Analyze this email and provide insights:

EMAIL DETAILS:
From: {sender_name or sender_email} <{sender_email}>
Subject: {subject}
Body: {body_text}

{guidelines_context}

Please analyze this email and return a JSON response with:
1. sentiment: "positive", "negative", or "neutral"
2. urgency_score: float 0.0-1.0 (0=not urgent, 1=extremely urgent)
3. topics: list of main topics/keywords (max 5)
4. action_required: boolean (does email require action from recipient?)
5. suggested_actions: list of suggested actions if any (max 3)
6. key_entities: list of people, places, organizations mentioned (max 5)
7. deadline_mentioned: ISO datetime if deadline mentioned, null otherwise
8. meeting_request: boolean (is this requesting a meeting?)
9. confidence_score: float 0.0-1.0 (confidence in analysis)

Consider factors like:
- Urgent language ("ASAP", "urgent", "deadline")
- Sender importance (domain, relationship)
- Time-sensitive content
- Action requests
- Questions requiring responses

Return only valid JSON.
"""

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are Jessica, an intelligent email analysis AI assistant. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse response
            analysis_text = response.choices[0].message.content.strip()
            
            # Clean and parse JSON
            if analysis_text.startswith("```json"):
                analysis_text = analysis_text[7:-3]
            elif analysis_text.startswith("```"):
                analysis_text = analysis_text[3:-3]
            
            analysis_result = json.loads(analysis_text)
            
            # Validate and set defaults
            return {
                "sentiment": analysis_result.get("sentiment", "neutral"),
                "urgency_score": float(analysis_result.get("urgency_score", 0.5)),
                "topics": analysis_result.get("topics", [])[:5],
                "action_required": bool(analysis_result.get("action_required", False)),
                "suggested_actions": analysis_result.get("suggested_actions", [])[:3],
                "key_entities": analysis_result.get("key_entities", [])[:5],
                "deadline_mentioned": analysis_result.get("deadline_mentioned"),
                "meeting_request": bool(analysis_result.get("meeting_request", False)),
                "confidence_score": float(analysis_result.get("confidence_score", 0.7))
            }
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error in AI analysis: {e}")
            return self._get_fallback_analysis()
        except Exception as e:
            print(f"AI analysis error: {e}")
            return self._get_fallback_analysis()
    
    async def generate_email_draft(
        self,
        original_email: Dict[str, Any],
        user_guidelines: Optional[Dict[str, Any]] = None,
        user_profile: Optional[Dict[str, Any]] = None,
        tone: str = "professional",
        length: str = "medium",
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate AI-powered email draft response"""
        
        try:
            # Extract communication style from guidelines
            comm_style = {}
            if user_guidelines:
                comm_style = user_guidelines.get("communication_style", {})
            
            # Extract user info
            user_name = ""
            user_signature = ""
            if user_profile:
                profile = user_profile.get("profile", {})
                user_name = profile.get("full_name", "")
                user_signature = comm_style.get("signature", "")
            
            # Prepare context
            context = f"""
ORIGINAL EMAIL:
From: {original_email['sender']['email']}
Subject: {original_email['subject']}
Body: {original_email.get('body_text', '')}

USER PROFILE:
Name: {user_name}
Communication Style: {comm_style.get('default_tone', 'professional')}
Signature: {user_signature}
Greeting Style: {comm_style.get('greeting_style', 'formal')}
Response Length Preference: {comm_style.get('preferred_response_length', 'medium')}

REQUIREMENTS:
- Tone: {tone}
- Length: {length}
- Include context: {comm_style.get('include_context', True)}
"""

            if custom_instructions:
                context += f"\nCUSTOM INSTRUCTIONS: {custom_instructions}"

            prompt = f"""
You are Jessica, an AI email assistant. Generate a professional email reply based on:

{context}

Please generate an appropriate email response and return JSON with:
1. body_text: plain text version of the reply
2. body_html: HTML version of the reply
3. confidence: float 0.0-1.0 (confidence in response appropriateness)
4. prompt_used: brief description of approach taken

Guidelines:
- Match the user's communication style and tone
- Address all points from the original email
- Be helpful and professional
- Include appropriate greeting and closing
- Keep length as requested ({length})
- Use {tone} tone throughout

Return only valid JSON.
"""

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are Jessica, an intelligent email drafting AI assistant. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=1500
            )
            
            # Parse response
            draft_text = response.choices[0].message.content.strip()
            
            # Clean and parse JSON
            if draft_text.startswith("```json"):
                draft_text = draft_text[7:-3]
            elif draft_text.startswith("```"):
                draft_text = draft_text[3:-3]
            
            draft_result = json.loads(draft_text)
            
            # Convert plain text to HTML if not provided
            body_html = draft_result.get("body_html")
            if not body_html:
                body_text = draft_result.get("body_text", "")
                body_html = body_text.replace("\n", "<br>")
            
            return {
                "body_text": draft_result.get("body_text", ""),
                "body_html": body_html,
                "confidence": float(draft_result.get("confidence", 0.7)),
                "prompt_used": draft_result.get("prompt_used", "Generated professional response")
            }
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error in draft generation: {e}")
            return self._get_fallback_draft()
        except Exception as e:
            print(f"Draft generation error: {e}")
            return self._get_fallback_draft()
    
    async def analyze_calendar_event(
        self,
        event: Dict[str, Any],
        context_events: List[Dict[str, Any]],
        user_guidelines: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze calendar event for scheduling optimization"""
        
        try:
            # Prepare scheduling preferences
            scheduling_prefs = []
            if user_guidelines:
                scheduling_prefs = user_guidelines.get("scheduling_preferences", [])
            
            # Analyze conflicts with other events
            conflicts = self._detect_conflicts(event, context_events)
            
            # Create analysis prompt
            prompt = f"""
You are Jessica, an AI calendar optimization assistant. Analyze this calendar event:

EVENT:
Title: {event['title']}
Start: {event['start_datetime']}
End: {event['end_datetime']}
Attendees: {len(event.get('attendees', []))}
Location: {event.get('location', {}).get('name', 'Not specified')}

CONTEXT EVENTS: {len(context_events)} other events in timeframe
CONFLICTS DETECTED: {len(conflicts)} potential conflicts

SCHEDULING PREFERENCES: {json.dumps(scheduling_prefs, indent=2) if scheduling_prefs else 'None specified'}

Analyze and return JSON with:
1. optimal_time_score: float 0.0-1.0 (how optimal is this timing?)
2. productivity_impact: "low", "medium", or "high"
3. meeting_type_classification: string (meeting type/purpose)
4. estimated_preparation_time: int (minutes needed to prepare)
5. recommended_buffer_time: int (minutes buffer before/after)
6. energy_level_match: "high", "medium", or "low" (energy needed vs time slot)
7. conflicts_detected: list of conflict objects with type and description
8. scheduling_suggestions: list of improvement suggestions (max 3)

Consider:
- Time of day for different meeting types
- Meeting duration appropriateness
- Attendee convenience
- Buffer time needs
- Energy levels throughout day

Return only valid JSON.
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are Jessica, an intelligent calendar analysis AI assistant. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse response
            analysis_text = response.choices[0].message.content.strip()
            
            # Clean and parse JSON
            if analysis_text.startswith("```json"):
                analysis_text = analysis_text[7:-3]
            elif analysis_text.startswith("```"):
                analysis_text = analysis_text[3:-3]
            
            analysis_result = json.loads(analysis_text)
            
            return {
                "optimal_time_score": float(analysis_result.get("optimal_time_score", 0.7)),
                "productivity_impact": analysis_result.get("productivity_impact", "medium"),
                "meeting_type_classification": analysis_result.get("meeting_type_classification", "general"),
                "estimated_preparation_time": int(analysis_result.get("estimated_preparation_time", 15)),
                "recommended_buffer_time": int(analysis_result.get("recommended_buffer_time", 15)),
                "energy_level_match": analysis_result.get("energy_level_match", "medium"),
                "conflicts_detected": conflicts,  # Use our detected conflicts
                "scheduling_suggestions": analysis_result.get("scheduling_suggestions", [])[:3]
            }
            
        except Exception as e:
            print(f"Calendar analysis error: {e}")
            return self._get_fallback_calendar_analysis()
    
    async def generate_scheduling_suggestions(
        self,
        title: str,
        duration_minutes: int,
        attendee_emails: List[str],
        existing_events: List[Dict[str, Any]],
        user_guidelines: Optional[Dict[str, Any]] = None,
        preferred_times: Optional[List[str]] = None,
        date_range_start: datetime = None,
        date_range_end: datetime = None
    ) -> List[Dict[str, Any]]:
        """Generate AI-powered scheduling suggestions"""
        
        try:
            # Prepare context
            context = f"""
MEETING TO SCHEDULE:
Title: {title}
Duration: {duration_minutes} minutes
Attendees: {len(attendee_emails)} people
Date Range: {date_range_start} to {date_range_end}
Preferred Times: {preferred_times or 'None specified'}

EXISTING EVENTS: {len(existing_events)} events in range
SCHEDULING PREFERENCES: {user_guidelines.get('scheduling_preferences', []) if user_guidelines else 'None'}

Find 3-5 optimal time slots considering:
- Avoid conflicts with existing events
- Prefer user's optimal time preferences
- Consider meeting type and duration
- Allow buffer time between meetings
- Account for different time zones if needed
"""

            prompt = f"""
You are Jessica, an AI scheduling assistant. Based on the context, suggest optimal meeting times:

{context}

Return JSON with array of suggestions, each containing:
1. suggested_datetime: ISO datetime string
2. duration_minutes: int (meeting duration)
3. confidence_score: float 0.0-1.0 (how good is this slot?)
4. reasons: list of strings explaining why this time is good (max 3)
5. attendee_availability: object with email keys and boolean availability values
6. optimal_score: float 0.0-1.0 (overall optimization score)

Suggest 3-5 time slots in order of preference.
Return only valid JSON.
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are Jessica, an intelligent scheduling AI assistant. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=1500
            )
            
            # Parse response
            suggestions_text = response.choices[0].message.content.strip()
            
            # Clean and parse JSON
            if suggestions_text.startswith("```json"):
                suggestions_text = suggestions_text[7:-3]
            elif suggestions_text.startswith("```"):
                suggestions_text = suggestions_text[3:-3]
            
            suggestions = json.loads(suggestions_text)
            
            # Ensure it's a list
            if isinstance(suggestions, dict):
                suggestions = suggestions.get("suggestions", [])
            
            return suggestions[:5]  # Limit to 5 suggestions
            
        except Exception as e:
            print(f"Scheduling suggestions error: {e}")
            return self._get_fallback_scheduling_suggestions()
    
    async def train_user_model(
        self,
        user_id: str,
        feedback_data: List[Dict[str, Any]],
        email_interactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Train user-specific AI model based on feedback and behavior"""
        
        try:
            # Analyze feedback patterns
            positive_feedback = [f for f in feedback_data if f.get("feedback_type") == "positive"]
            negative_feedback = [f for f in feedback_data if f.get("feedback_type") == "negative"]
            
            # Analyze email interaction patterns
            sent_drafts = [e for e in email_interactions if e.get("status") == "replied"]
            
            training_stats = {
                "total_feedback_points": len(feedback_data),
                "positive_feedback": len(positive_feedback),
                "negative_feedback": len(negative_feedback),
                "emails_with_replies": len(sent_drafts),
                "learning_confidence": min(1.0, len(feedback_data) / 50),  # More feedback = higher confidence
                "model_version": datetime.utcnow().isoformat(),
                "improvements_identified": []
            }
            
            # Identify improvement areas
            if len(negative_feedback) > len(positive_feedback) * 0.3:
                training_stats["improvements_identified"].append("Review email classification accuracy")
            
            if len(sent_drafts) < len(email_interactions) * 0.1:
                training_stats["improvements_identified"].append("Improve draft generation quality")
            
            return training_stats
            
        except Exception as e:
            print(f"Model training error: {e}")
            return {
                "total_feedback_points": 0,
                "learning_confidence": 0.0,
                "error": str(e)
            }
    
    def _detect_conflicts(self, event: Dict[str, Any], context_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect scheduling conflicts with other events"""
        conflicts = []
        
        event_start = datetime.fromisoformat(str(event['start_datetime']).replace('Z', '+00:00'))
        event_end = datetime.fromisoformat(str(event['end_datetime']).replace('Z', '+00:00'))
        
        for other_event in context_events:
            if other_event['id'] == event['id']:
                continue
                
            try:
                other_start = datetime.fromisoformat(str(other_event['start_datetime']).replace('Z', '+00:00'))
                other_end = datetime.fromisoformat(str(other_event['end_datetime']).replace('Z', '+00:00'))
                
                # Check for overlap
                if (event_start < other_end and event_end > other_start):
                    overlap_minutes = min(event_end, other_end) - max(event_start, other_start)
                    conflicts.append({
                        "conflict_type": "hard",
                        "conflicting_event_id": other_event['id'],
                        "conflicting_event_title": other_event['title'],
                        "overlap_duration_minutes": int(overlap_minutes.total_seconds() / 60),
                        "suggested_resolution": "Reschedule one of the events"
                    })
            except Exception as e:
                print(f"Error detecting conflict: {e}")
                continue
        
        return conflicts
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Fallback email analysis when AI fails"""
        return {
            "sentiment": "neutral",
            "urgency_score": 0.5,
            "topics": [],
            "action_required": False,
            "suggested_actions": [],
            "key_entities": [],
            "deadline_mentioned": None,
            "meeting_request": False,
            "confidence_score": 0.3
        }
    
    def _get_fallback_draft(self) -> Dict[str, Any]:
        """Fallback draft when AI fails"""
        return {
            "body_text": "Thank you for your email. I will review this and get back to you shortly.",
            "body_html": "Thank you for your email. I will review this and get back to you shortly.",
            "confidence": 0.3,
            "prompt_used": "Fallback template response"
        }
    
    def _get_fallback_calendar_analysis(self) -> Dict[str, Any]:
        """Fallback calendar analysis when AI fails"""
        return {
            "optimal_time_score": 0.7,
            "productivity_impact": "medium",
            "meeting_type_classification": "general",
            "estimated_preparation_time": 15,
            "recommended_buffer_time": 15,
            "energy_level_match": "medium",
            "conflicts_detected": [],
            "scheduling_suggestions": []
        }
    
    def _get_fallback_scheduling_suggestions(self) -> List[Dict[str, Any]]:
        """Fallback scheduling suggestions when AI fails"""
        return [
            {
                "suggested_datetime": datetime.utcnow().isoformat(),
                "duration_minutes": 30,
                "confidence_score": 0.3,
                "reasons": ["Default time slot"],
                "attendee_availability": {},
                "optimal_score": 0.5
            }
        ]