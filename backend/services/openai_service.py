import openai
from typing import Dict, Any, List, Optional
from decouple import config

class OpenAIService:
    """Service for OpenAI API integration"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=config('OPENAI_API_KEY', default='sk-placeholder'))
        self.model = "gpt-4o"  # Latest model as of 2025
        self.max_tokens = 2000
        self.temperature = 0.3
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test OpenAI API connection"""
        
        try:
            # Make a simple test request
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say hello in one word."}
                ],
                max_tokens=10,
                temperature=0
            )
            
            return {
                "status": "connected",
                "model": self.model,
                "response": response.choices[0].message.content.strip(),
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            print(f"OpenAI connection test error: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def analyze_text(
        self,
        text: str,
        analysis_type: str = "sentiment",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze text with specified analysis type"""
        
        try:
            if analysis_type == "sentiment":
                system_prompt = """You are an expert sentiment analysis AI. 
                Analyze the sentiment of the given text and return a JSON response with:
                - sentiment: "positive", "negative", or "neutral"
                - confidence: float 0.0-1.0
                - reasoning: brief explanation
                Return only valid JSON."""
                
            elif analysis_type == "urgency":
                system_prompt = """You are an expert at detecting urgency in text.
                Analyze the urgency level and return JSON with:
                - urgency_score: float 0.0-1.0 (0=not urgent, 1=extremely urgent)
                - indicators: list of urgency indicators found
                - confidence: float 0.0-1.0
                Return only valid JSON."""
                
            elif analysis_type == "topics":
                system_prompt = """You are an expert at topic extraction.
                Extract main topics and return JSON with:
                - topics: list of main topics (max 5)
                - categories: list of categories this text belongs to
                - keywords: list of important keywords (max 10)
                Return only valid JSON."""
                
            else:
                system_prompt = """You are a general text analysis AI.
                Provide a comprehensive analysis of the text."""
            
            if context:
                user_prompt = f"Context: {context}\n\nText to analyze: {text}"
            else:
                user_prompt = f"Text to analyze: {text}"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to parse as JSON
            try:
                import json
                if content.startswith("```json"):
                    content = content[7:-3]
                elif content.startswith("```"):
                    content = content[3:-3]
                
                analysis_result = json.loads(content)
                
                return {
                    "analysis": analysis_result,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
                
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw content
                return {
                    "analysis": {"raw_response": content},
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
            
        except Exception as e:
            print(f"OpenAI text analysis error: {e}")
            return {
                "error": str(e),
                "analysis": None
            }
    
    async def generate_text(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """Generate text based on prompt"""
        
        try:
            messages = []
            
            if system_message:
                messages.append({"role": "system", "content": system_message})
            
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature
            )
            
            return {
                "generated_text": response.choices[0].message.content.strip(),
                "finish_reason": response.choices[0].finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            print(f"OpenAI text generation error: {e}")
            return {
                "error": str(e),
                "generated_text": None
            }
    
    async def summarize_text(
        self,
        text: str,
        max_length: str = "medium",
        style: str = "professional"
    ) -> Dict[str, Any]:
        """Summarize text with specified length and style"""
        
        try:
            length_instructions = {
                "brief": "in 1-2 sentences",
                "medium": "in 3-5 sentences", 
                "detailed": "in 1-2 paragraphs"
            }
            
            system_prompt = f"""You are an expert at summarizing text.
            Create a {style} summary of the given text {length_instructions.get(max_length, 'concisely')}.
            Focus on the key points and main takeaways.
            Return only the summary without any additional text."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Summarize this text: {text}"}
                ],
                max_tokens=min(1000, self.max_tokens),
                temperature=0.3
            )
            
            return {
                "summary": response.choices[0].message.content.strip(),
                "original_length": len(text),
                "summary_length": len(response.choices[0].message.content),
                "compression_ratio": len(response.choices[0].message.content) / len(text),
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            print(f"OpenAI summarization error: {e}")
            return {
                "error": str(e),
                "summary": None
            }
    
    async def extract_entities(
        self,
        text: str,
        entity_types: List[str] = None
    ) -> Dict[str, Any]:
        """Extract named entities from text"""
        
        try:
            if not entity_types:
                entity_types = ["person", "organization", "location", "date", "email", "phone"]
            
            system_prompt = f"""You are an expert at named entity recognition.
            Extract entities of these types: {', '.join(entity_types)}
            Return a JSON response with:
            - entities: array of objects with 'text', 'type', and 'confidence' fields
            - entity_counts: object with counts for each entity type
            Return only valid JSON."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract entities from: {text}"}
                ],
                max_tokens=self.max_tokens,
                temperature=0.2
            )
            
            content = response.choices[0].message.content.strip()
            
            try:
                import json
                if content.startswith("```json"):
                    content = content[7:-3]
                elif content.startswith("```"):
                    content = content[3:-3]
                
                entities_result = json.loads(content)
                
                return {
                    "entities": entities_result,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
                
            except json.JSONDecodeError:
                return {
                    "entities": {"raw_response": content},
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
            
        except Exception as e:
            print(f"OpenAI entity extraction error: {e}")
            return {
                "error": str(e),
                "entities": None
            }
    
    async def classify_text(
        self,
        text: str,
        categories: List[str],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Classify text into provided categories"""
        
        try:
            system_prompt = f"""You are an expert text classifier.
            Classify the given text into one or more of these categories: {', '.join(categories)}
            Return a JSON response with:
            - primary_category: the most likely category
            - all_categories: array of categories with confidence scores
            - reasoning: brief explanation of the classification
            Return only valid JSON."""
            
            user_prompt = f"Text to classify: {text}"
            if context:
                user_prompt = f"Context: {context}\n\n{user_prompt}"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.2
            )
            
            content = response.choices[0].message.content.strip()
            
            try:
                import json
                if content.startswith("```json"):
                    content = content[7:-3]
                elif content.startswith("```"):
                    content = content[3:-3]
                
                classification_result = json.loads(content)
                
                return {
                    "classification": classification_result,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
                
            except json.JSONDecodeError:
                return {
                    "classification": {"raw_response": content},
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
            
        except Exception as e:
            print(f"OpenAI text classification error: {e}")
            return {
                "error": str(e),
                "classification": None
            }
    
    async def get_embeddings(
        self,
        texts: List[str],
        model: str = "text-embedding-3-small"
    ) -> Dict[str, Any]:
        """Get embeddings for list of texts"""
        
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=model
            )
            
            embeddings = [embedding.embedding for embedding in response.data]
            
            return {
                "embeddings": embeddings,
                "model": model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            print(f"OpenAI embeddings error: {e}")
            return {
                "error": str(e),
                "embeddings": None
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI API health"""
        
        try:
            # Test with a simple request
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Respond with 'OK' if you can understand this."}
                ],
                max_tokens=5,
                temperature=0
            )
            
            return {
                "status": "healthy",
                "model": self.model,
                "api_responsive": True,
                "response_time": "< 1s",  # Approximate
                "test_response": response.choices[0].message.content.strip()
            }
            
        except Exception as e:
            print(f"OpenAI health check error: {e}")
            return {
                "status": "unhealthy",
                "api_responsive": False,
                "error": str(e)
            }
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about available models"""
        
        try:
            models = self.client.models.list()
            
            # Filter for relevant models
            relevant_models = []
            for model in models.data:
                if any(keyword in model.id for keyword in ['gpt', 'text-embedding', 'whisper']):
                    relevant_models.append({
                        "id": model.id,
                        "owned_by": model.owned_by,
                        "created": model.created
                    })
            
            return {
                "current_model": self.model,
                "available_models": relevant_models[:10],  # Limit to 10
                "total_models": len(models.data)
            }
            
        except Exception as e:
            print(f"OpenAI model info error: {e}")
            return {
                "error": str(e),
                "current_model": self.model,
                "available_models": []
            }
    
    async def calculate_token_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate estimated cost for token usage"""
        
        try:
            # Pricing as of 2025 (these would need to be updated based on actual pricing)
            pricing = {
                "gpt-4o": {
                    "input": 0.005 / 1000,  # $0.005 per 1K input tokens
                    "output": 0.015 / 1000  # $0.015 per 1K output tokens
                },
                "gpt-4": {
                    "input": 0.03 / 1000,
                    "output": 0.06 / 1000
                },
                "gpt-3.5-turbo": {
                    "input": 0.001 / 1000,
                    "output": 0.002 / 1000
                }
            }
            
            model_name = model or self.model
            model_pricing = pricing.get(model_name, pricing["gpt-4o"])
            
            input_cost = prompt_tokens * model_pricing["input"]
            output_cost = completion_tokens * model_pricing["output"]
            total_cost = input_cost + output_cost
            
            return {
                "model": model_name,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "input_cost_usd": round(input_cost, 6),
                "output_cost_usd": round(output_cost, 6),
                "total_cost_usd": round(total_cost, 6)
            }
            
        except Exception as e:
            print(f"Token cost calculation error: {e}")
            return {
                "error": str(e),
                "total_cost_usd": 0.0
            }