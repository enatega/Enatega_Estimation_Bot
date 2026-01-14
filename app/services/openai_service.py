from openai import OpenAI
from typing import List, Dict, Optional
from app.core.config import settings
from app.models.schemas import EstimateResponse, FeatureBreakdown
from app.services.knowledge_base import KnowledgeBase
import logging
import json
import re

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service for interacting with OpenAI API"""
    
    def __init__(self, knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        
        if not self.client:
            logger.warning("OpenAI API key not configured")
    
    def _build_system_prompt(self) -> str:
        """Build system prompt based on ChatGPT examples"""
        chatgpt_examples = self.knowledge_base.get_chatgpt_examples()
        
        system_prompt = f"""You are an expert estimation consultant for client onboarding systems. Your ONLY role is to provide estimates based on documents.

CRITICAL RULES:
1. You ONLY provide time and cost estimates - nothing else
2. Base estimates STRICTLY on provided context - NO hallucination
3. Be CONCISE - max 120 words
4. Use HTML formatting: <b>bold</b>, <br/> for line breaks, <ul><li> for lists
5. Do NOT use markdown asterisks - use HTML tags
6. Do NOT include "Next Steps" section
7. Match exact values from breakdown provided
8. If asked about non-estimation topics, politely redirect: "I specialize in providing time and cost estimates. How can I help with your project requirements?"

Example format from reference conversations:
{chatgpt_examples[:2000] if chatgpt_examples else ""}

Response format (use HTML):
- Brief summary (2-3 sentences) using <b> for emphasis
- Feature breakdown with time/cost using <b> tags
- Total estimates matching provided breakdown
- Assumptions (brief, bullet points using <ul><li>)
- Timeline

DO NOT:
- Answer questions outside estimation scope
- Include Next Steps
- Use markdown formatting (**text**)
- Add information not in context
- Provide generic estimates without context"""
        
        return system_prompt
    
    def _extract_exact_estimate_from_context(self, query: str, context: str) -> Optional[Dict]:
        """Try to extract exact hour range from context before using AI"""
        if not context:
            return None
        
        query_lower = query.lower()
        # Look for patterns like "38-42 hours", "38 to 42 hours", "Estimated Time: 38-42"
        patterns = [
            r'(\d+)\s*[-–—]\s*(\d+)\s*hours?',
            r'(\d+)\s+to\s+(\d+)\s*hours?',
            r'estimated\s+time[:\s]+(\d+)\s*[-–—]\s*(\d+)',
            r'time\s+estimate[:\s]+(\d+)\s*[-–—]\s*(\d+)',
            r'(\d+)\s*[-–—]\s*(\d+)\s*hrs?',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, context, re.IGNORECASE)
            for match in matches:
                min_hours = int(match.group(1))
                max_hours = int(match.group(2))
                
                # Check if this estimate is relevant to the query
                # Look at surrounding text (100 chars before/after)
                start = max(0, match.start() - 100)
                end = min(len(context), match.end() + 100)
                surrounding = context[start:end].lower()
                
                # Check if query keywords appear near the estimate
                query_keywords = [w for w in query_lower.split() if len(w) > 3]
                if any(keyword in surrounding for keyword in query_keywords):
                    # Extract feature name from context
                    feature_name = self._extract_feature_name(query, surrounding)
                    
                    logger.info(f"Found exact estimate in context: {min_hours}-{max_hours} hours for {feature_name}")
                    return {
                        "name": feature_name,
                        "description": f"Extracted from context",
                        "base_time_hours_min": min_hours,
                        "base_time_hours_max": max_hours,
                        "complexity_level": "medium",
                        "category": "Integration"
                    }
        
        return None
    
    def _extract_feature_name(self, query: str, context_snippet: str) -> str:
        """Extract feature name from query or context intelligently"""
        # Try to extract from context snippet first (more accurate)
        context_lower = context_snippet.lower()
        
        # Look for feature names in context (e.g., "HYP Payment", "User Authentication")
        # Common patterns in context
        if "payment" in context_lower:
            # Try to find the payment method name from context
            payment_match = re.search(r'(\w+)\s+payment', context_lower)
            if payment_match:
                payment_name = payment_match.group(1).title()
                return f"{payment_name} Payment Integration"
            return "Payment Integration"
        elif "authentication" in context_lower or "auth" in context_lower:
            return "User Authentication"
        elif "dashboard" in context_lower:
            return "Dashboard"
        
        # Fallback: extract from query
        query_lower = query.lower()
        if "payment" in query_lower:
            # Extract payment method name from query if present
            words = query.split()
            for i, word in enumerate(words):
                if word.lower() == "payment" and i > 0:
                    method = words[i-1].title()
                    return f"{method} Payment Integration"
            return "Payment Integration"
        elif "authentication" in query_lower or "auth" in query_lower:
            return "User Authentication"
        elif "dashboard" in query_lower:
            return "Dashboard"
        
        # Default: use first few meaningful words of query
        words = [w for w in query.split() if w.lower() not in ["i", "want", "to", "add", "how", "much", "it", "take"]][:4]
        return " ".join(words).title() if words else "Feature Development"
    
    def extract_features_from_query(self, query: str, context: str = "") -> List[Dict]:
        """Use AI to extract features from natural language query based on document context"""
        if not self.client:
            return []
        
        try:
            # Get relevant examples from documents
            examples = self.knowledge_base.get_chatgpt_examples()[:2000] if self.knowledge_base else ""
            
            # Get comprehensive context from vector store - get MORE results for better coverage
            vector_context = ""
            try:
                if self.knowledge_base.vector_store:
                    # Get extensive context to capture all relevant information
                    vector_context = self.knowledge_base.vector_store.get_relevant_context(query, max_length=6000)
            except Exception as e:
                logger.debug(f"Vector context retrieval failed: {e}")
            
            # Also get broader context from knowledge base
            broader_context = ""
            try:
                broader_context = self.knowledge_base.get_context_for_query(query, max_length=4000)
            except:
                pass
            
            # Combine ALL contexts comprehensively - include everything for complete understanding
            context_parts = []
            
            # Primary context from vector search (most relevant)
            if vector_context:
                context_parts.append(f"=== PRIMARY CONTEXT (Most Relevant to Query) ===\n{vector_context[:5000]}")
            
            # Additional broader context (different perspective)
            if broader_context and broader_context != vector_context:
                context_parts.append(f"\n=== ADDITIONAL CONTEXT (Broader View) ===\n{broader_context[:3000]}")
            
            # Example conversations (estimation patterns)
            if examples and examples not in vector_context:
                context_parts.append(f"\n=== ESTIMATION EXAMPLES (Reference Patterns) ===\n{examples[:2000]}")
            
            # Original context if provided
            if context and context not in vector_context and context not in broader_context:
                context_parts.append(f"\n=== SUPPLEMENTARY CONTEXT ===\n{context[:2000]}")
            
            # Combine everything for comprehensive analysis
            combined_context = "\n\n".join(context_parts) if context_parts else (context[:3000] if context else examples[:3000])
            
            logger.info(f"Combined context length: {len(combined_context)} characters from {len(context_parts)} sources for intelligent analysis")
            
            # Use intelligent AI analysis instead of exact extraction
            prompt = f"""You are an expert estimation analyst. Analyze the requirements and generate intelligent time estimates by considering ALL available context including team capabilities, project specifics, and document data.

Requirements: {query}

COMPREHENSIVE CONTEXT FROM ALL DOCUMENTS (study ALL of this carefully):
{combined_context}

ANALYSIS PROCESS:
1. STUDY the requirements thoroughly - understand what needs to be built

2. ANALYZE the context comprehensively:
   - Team composition and capabilities (e.g., "15 full-stack developers", "2 DevOps engineers", "3 QA specialists")
   - Team size and skill levels mentioned
   - Project complexity factors from documents
   - Technology stack and infrastructure details
   - Similar features or projects mentioned in context
   - Any relevant estimation patterns or examples

3. GENERATE intelligent estimates by considering:
   - Team capabilities: How many developers? What skills? What's their capacity?
   - Project complexity: Is this simple, medium, or complex based on context?
   - Similar work: Are there similar features/projects in context? Use them as reference
   - Technology stack: What technologies are mentioned? Factor in learning curve if needed
   - Infrastructure: Consider DevOps, QA, design team availability from context
   - Realistic timelines: Based on team size and capabilities from context

4. DO NOT just copy exact numbers from context. Instead:
   - Use context as REFERENCE to understand team capabilities and project scope
   - Consider if the team is large (15+ developers) vs small
   - Factor in parallel work capabilities
   - Consider team expertise level from context
   - Generate estimates that make sense for THIS team and THIS project

5. Extract features explicitly mentioned in: "{query}"

6. Provide realistic time ranges that reflect:
   - Team capabilities from context
   - Project complexity
   - Similar work patterns from context
   - Realistic development timelines

Return COMPLETE JSON array:
[
  {{
    "name": "Feature Name",
    "description": "Description based on requirements and context analysis",
    "base_time_hours_min": <min_hours - consider team capabilities>,
    "base_time_hours_max": <max_hours - consider team capabilities>,
    "complexity_level": "simple|medium|complex",
    "category": "Category"
  }}
]"""
            
            system_prompt = """You are an expert estimation analyst specializing in software development time estimation.

YOUR ROLE:
- Analyze requirements intelligently
- Study ALL context comprehensively (team, project, documents)
- Generate intelligent estimates based on comprehensive understanding
- Consider team capabilities, project complexity, and realistic timelines

ESTIMATION APPROACH:
1. Study team composition from context (size, skills, roles)
2. Understand project complexity and requirements
3. Reference similar work from context as guidance
4. Generate estimates that reflect:
   - Team capabilities and capacity
   - Project complexity
   - Realistic development timelines
   - Parallel work possibilities

5. DO NOT just extract exact numbers - ANALYZE and ESTIMATE intelligently
6. Consider ALL factors: team size, skills, infrastructure, QA, design, etc.

Return ONLY valid JSON array, no explanations.
Format: [{"name": "...", "description": "...", "base_time_hours_min": <min>, "base_time_hours_max": <max>, "complexity_level": "...", "category": "..."}]"""
            
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Very low for accurate extraction
                max_tokens=2500  # Increased to ensure complete JSON
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean content - remove markdown code blocks if present
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            content = content.strip()
            
            # Try multiple JSON extraction strategies
            # Strategy 1: Direct parse
            try:
                features = json.loads(content)
                if isinstance(features, list):
                    # Normalize features to have min/max hours
                    return self._normalize_features(features)
                elif isinstance(features, dict) and "features" in features:
                    return self._normalize_features(features["features"])
                elif isinstance(features, dict):
                    # If it's a dict with array values, try to find array
                    for key, value in features.items():
                        if isinstance(value, list):
                            return self._normalize_features(value)
            except:
                pass
            
            # Strategy 2: Extract JSON array from text (more lenient)
            json_match = re.search(r'\[[\s\S]*?\]', content, re.MULTILINE | re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group()
                    # Try to fix incomplete JSON by finding the last complete object
                    if json_str.count('{') > json_str.count('}'):
                        # Incomplete JSON - try to extract what we can
                        # Find all complete objects
                        obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                        matches = re.findall(obj_pattern, json_str, re.DOTALL)
                        if matches:
                            features = [json.loads(m) for m in matches]
                            return self._normalize_features(features)
                    else:
                        features = json.loads(json_str)
                        if isinstance(features, list):
                            return self._normalize_features(features)
                except Exception as e:
                    logger.debug(f"Strategy 2 failed: {e}")
                    pass
            
            # Strategy 3: Try to find array-like structure
            try:
                # Look for array pattern
                array_pattern = re.search(r'\[.*?\]', content, re.DOTALL)
                if array_pattern:
                    features = json.loads(array_pattern.group())
                    if isinstance(features, list):
                        return self._normalize_features(features)
            except:
                pass
            
            # Strategy 4: If all parsing fails, try to extract features manually from query
            logger.warning(f"Could not parse JSON, attempting fallback extraction. Content preview: {content[:200]}")
            fallback_result = self._fallback_feature_extraction(query, combined_context)
            if fallback_result:
                return fallback_result
            
            # Final fallback: return empty to trigger proper error handling
            logger.error("All feature extraction methods exhausted")
            return []
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}", exc_info=True)
            fallback_result = self._fallback_feature_extraction(query, combined_context)
            if fallback_result:
                return fallback_result
            
            # Return empty to trigger proper error handling
            return []
    
    def _normalize_features(self, features: List[Dict]) -> List[Dict]:
        """Normalize features to have min/max hours with reasonable ranges"""
        normalized = []
        for feature in features:
            if "base_time_hours_min" in feature and "base_time_hours_max" in feature:
                # Ensure range is reasonable (not more than 50% variance)
                min_h = feature["base_time_hours_min"]
                max_h = feature["base_time_hours_max"]
                # If range is too wide, cap it at 30% variance
                if max_h > min_h * 1.5:
                    max_h = min_h * 1.3
                normalized.append({
                    **feature,
                    "base_time_hours_min": round(min_h, 1),
                    "base_time_hours_max": round(max_h, 1)
                })
            elif "base_time_hours" in feature:
                # Convert single value to range (±15% for tighter range)
                base = feature["base_time_hours"]
                normalized.append({
                    **feature,
                    "base_time_hours_min": round(base * 0.85, 1),
                    "base_time_hours_max": round(base * 1.15, 1)
                })
            else:
                # Estimate based on complexity with tighter ranges
                complexity = feature.get("complexity_level", "medium")
                if complexity == "simple":
                    min_hours, max_hours = 20, 35
                elif complexity == "complex":
                    min_hours, max_hours = 70, 120
                else:  # medium
                    min_hours, max_hours = 40, 65
                
                normalized.append({
                    **feature,
                    "base_time_hours_min": min_hours,
                    "base_time_hours_max": max_hours
                })
        return normalized
    
    def _fallback_feature_extraction(self, query: str, context: str) -> List[Dict]:
        """Fallback: Extract features using intelligent analysis when JSON parsing fails"""
        if not self.client:
            return []
        
        try:
            prompt = f"""Analyze the requirements and generate intelligent time estimates by studying ALL context.

Query: {query}

COMPREHENSIVE CONTEXT (study ALL of this):
{context[:4000] if context else "No context available - use your knowledge"}

ANALYSIS INSTRUCTIONS:
1. Study the requirements - what needs to be built?
2. Analyze context comprehensively:
   - Team composition and capabilities (size, skills, roles)
   - Project complexity and requirements
   - Similar work or patterns from context
   - Technology stack and infrastructure
3. Generate intelligent estimates considering:
   - Team capabilities from context
   - Project complexity
   - Realistic development timelines
   - Parallel work possibilities based on team size

Return JSON array (ONLY JSON, no explanations):
[
  {{"name": "Feature Name", "description": "Description", "base_time_hours_min": <min>, "base_time_hours_max": <max>, "complexity_level": "simple|medium|complex", "category": "Category"}}
]"""
            
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a technical analyst. Return only valid, complete JSON arrays. Ensure all brackets are closed."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2500  # Increased for complete JSON
            )
            
            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            content = content.strip()
            
            # Try to extract JSON array
            json_match = re.search(r'\[[\s\S]*?\]', content, re.DOTALL)
            if json_match:
                try:
                    features = json.loads(json_match.group())
                    return self._normalize_features(features) if isinstance(features, list) else []
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error in fallback: {e}")
                    # Try to extract individual objects
                    obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                    matches = re.findall(obj_pattern, content, re.DOTALL)
                    if matches:
                        try:
                            features = [json.loads(m) for m in matches]
                            return self._normalize_features(features)
                        except:
                            pass
        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
        
        return []
    
    def generate_estimate_response(
        self,
        requirements: str,
        breakdown: List[FeatureBreakdown],
        total_time: float,
        total_cost: float,
        assumptions: List[str],
        timeline: str
    ) -> str:
        """Generate concise natural language response for estimate"""
        if not self.client:
            return self._generate_fallback_response(breakdown, total_time, total_cost, assumptions, timeline)
        
        try:
            # Get relevant context from vector store
            context = ""
            try:
                if self.knowledge_base.vector_store:
                    context = self.knowledge_base.vector_store.get_relevant_context(
                        requirements, 
                        max_length=3000
                    )
            except Exception as e:
                logger.warning(f"Could not get vector context: {e}")
            
            breakdown_text = "\n".join([
                f"- {item.feature}: {item.time_hours} hours, ${item.cost:.2f}"
                for item in breakdown
            ])
            
            assumptions_text = "\n".join([f"- {assumption}" for assumption in assumptions[:5]])  # Limit assumptions
            
            prompt = f"""Generate a CONCISE estimation response using HTML formatting. Match the breakdown EXACTLY.

Client Requirements: {requirements}

Relevant Context from Documents (USE THESE VALUES):
{context[:2500] if context else "Use standard estimation practices"}

Estimate Breakdown (MATCH THESE EXACT VALUES):
{breakdown_text}

Total Time: {total_time} hours
Total Cost: ${total_cost:.2f}
Timeline: {timeline}

Assumptions:
{assumptions_text}

Generate a BRIEF response (max 120 words) using HTML tags:
- Use <b>text</b> for bold (NOT **text**)
- Use <br/> for line breaks  
- Use <ul><li>item</li></ul> for lists
- MUST match breakdown totals: {total_time} hours, ${total_cost:.2f}
- Reference features from breakdown: {', '.join([item.feature for item in breakdown[:3]])}

CRITICAL: 
- Use HTML formatting ONLY
- Match breakdown totals EXACTLY
- Be CONCISE (max 120 words)
- NO "Next Steps"
- Base ONLY on provided context
- Reference the specific features from breakdown"""
            
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Lower temperature for more focused, accurate responses
                max_tokens=600  # Reduced for more concise responses
            )
            
            content = response.choices[0].message.content.strip()
            
            # Convert markdown to HTML if present
            import re
            # Convert **bold** to <b>bold</b>
            content = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', content)
            # Convert * list items to <li>
            lines = content.split('\n')
            html_lines = []
            in_list = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('- ') or stripped.startswith('* '):
                    if not in_list:
                        html_lines.append('<ul>')
                        in_list = True
                    html_lines.append(f'<li>{stripped[2:]}</li>')
                else:
                    if in_list:
                        html_lines.append('</ul>')
                        in_list = False
                    if stripped:
                        html_lines.append(stripped + '<br/>')
            if in_list:
                html_lines.append('</ul>')
            content = '\n'.join(html_lines)
            
            # Remove "Next Steps" section if present
            if "Next Steps" in content or "next steps" in content.lower():
                lines = content.split('\n')
                filtered_lines = []
                skip = False
                for line in lines:
                    if "Next Steps" in line or "next steps" in line.lower():
                        skip = True
                    if not skip:
                        filtered_lines.append(line)
                content = '\n'.join(filtered_lines).strip()
            
            return content
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._generate_fallback_response(breakdown, total_time, total_cost, assumptions, timeline)
    
    def _generate_fallback_response(
        self,
        breakdown: List[FeatureBreakdown],
        total_time: float,
        total_cost: float,
        assumptions: List[str],
        timeline: str
    ) -> str:
        """Generate concise fallback response without AI"""
        response = f"""Based on your requirements:\n\n"""
        
        for item in breakdown:
            response += f"**{item.feature}**: {item.time_hours} hours, ${item.cost:.2f}\n"
        
        response += f"\n**Total**: {total_time} hours, ${total_cost:.2f}\n"
        response += f"**Timeline**: {timeline}\n\n"
        response += "**Assumptions**:\n"
        for assumption in assumptions[:4]:  # Limit to 4 assumptions
            response += f"- {assumption}\n"
        
        return response
    
    def chat(self, message: str, conversation_history: List[Dict] = None) -> str:
        """Handle chat conversation with context from vector store"""
        if not self.client:
            return "OpenAI API is not configured. Please set OPENAI_API_KEY environment variable."
        
        try:
            # Check if this is a greeting or non-estimation query
            message_lower = message.lower().strip()
            greeting_keywords = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon"]
            is_greeting = any(keyword in message_lower for keyword in greeting_keywords) and len(message_lower.split()) < 5
            
            # Check if query is about estimation
            estimation_keywords = ["estimate", "cost", "price", "time", "hours", "budget", "timeline", "feature", "build", "develop", "implement", "authentication", "dashboard", "payment", "system"]
            is_estimation_query = any(keyword in message_lower for keyword in estimation_keywords)
            
            # If greeting, respond warmly
            if is_greeting:
                return "Hello! I'm your Estimation Bot. I specialize in providing time and cost estimates for client onboarding systems. What would you like to estimate today?"
            
            # If not estimation-related, redirect politely
            if not is_estimation_query and not conversation_history:
                return "I specialize in providing time and cost estimates for client onboarding systems. Could you tell me about the features you'd like to estimate?"
            
            # Get relevant context from vector store for this query
            context = ""
            try:
                if self.knowledge_base.vector_store:
                    context = self.knowledge_base.vector_store.get_relevant_context(
                        message, 
                        max_length=2000
                    )
            except Exception as e:
                logger.warning(f"Could not get vector context: {e}")
            
            # Build enhanced system prompt with context
            system_prompt = self._build_system_prompt()
            if context:
                system_prompt += f"\n\nRelevant context for this query:\n{context[:1500]}"
            
            # Add strict role enforcement
            system_prompt += "\n\nREMEMBER: You ONLY provide estimates. If asked about anything else, politely redirect to estimation questions."
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            if conversation_history:
                messages.extend(conversation_history)
            
            messages.append({"role": "user", "content": message})
            
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.2,  # Lower for more focused, role-appropriate responses
                max_tokens=600  # Reduced for concise responses
            )
            
            content = response.choices[0].message.content.strip()
            
            # Convert markdown to HTML
            import re
            content = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', content)
            # Convert line breaks
            content = content.replace('\n\n', '<br/><br/>').replace('\n', '<br/>')
            
            # Remove "Next Steps" if present
            if "Next Steps" in content or "next steps" in content.lower():
                lines = content.split('<br/>')
                filtered_lines = []
                skip = False
                for line in lines:
                    if "Next Steps" in line or "next steps" in line.lower():
                        skip = True
                    if not skip:
                        filtered_lines.append(line)
                content = '<br/>'.join(filtered_lines).strip()
            
            return content
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"
