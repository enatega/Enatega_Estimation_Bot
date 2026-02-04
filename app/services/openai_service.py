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
    
    def _get_max_tokens_param(self, max_tokens_value: int) -> dict:
        """Get the correct max tokens parameter based on model type"""
        model = settings.OPENAI_MODEL.lower()
        
        # Models that require max_completion_tokens:
        # - o1, o3 series (reasoning models)
        # - gpt-4-turbo-preview and newer gpt-4 models
        # - gpt-5.x series (all versions)
        # - Any model that the API says requires it
        # The API will accept max_completion_tokens even if SDK version is old
        
        # Check for models that definitely need max_completion_tokens
        needs_completion_tokens = (
            model.startswith('o1') or 
            model.startswith('o3') or 
            model.startswith('gpt-5') or  # GPT-5.x series (including 5.2)
            'gpt-5' in model or
            'turbo' in model or 
            'preview' in model or 
            'gpt-4' in model or
            model.startswith('gpt-4')
        )
        
        if needs_completion_tokens:
            # Use max_completion_tokens for newer models
            # The API requires it, even if SDK doesn't officially support it
            logger.info(f"Using max_completion_tokens for model: {model}")
            return {"max_completion_tokens": max_tokens_value}
        
        # For older models (gpt-3.5, etc.), use max_tokens
        logger.info(f"Using max_tokens for model: {model}")
        return {"max_tokens": max_tokens_value}
    
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
        """Disabled - now using intelligent AI analysis instead of regex extraction"""
        # This method is kept for compatibility but always returns None
        # We now rely on AI to intelligently analyze all context including Estimates.txt
        return None
    
    def _extract_from_estimates_txt(self, query: str, context: str) -> Optional[Dict]:
        """Use AI to intelligently extract feature estimate from Estimates.txt"""
        if not context or not self.client:
            return None
        
        # Let AI analyze Estimates.txt and extract relevant feature
        try:
            # Extract Estimates.txt section from context
            estimates_section = ""
            if "ESTIMATES.TXT" in context:
                parts = context.split("===")
                for i, part in enumerate(parts):
                    if "ESTIMATES.TXT" in part and i + 1 < len(parts):
                        estimates_section = parts[i + 1]
                        break
            else:
                estimates_section = context[:3000]
            
            prompt = f"""Analyze the query and find the matching feature in Estimates.txt.

Query: {query}

Estimates.txt Content:
{estimates_section[:3000] if estimates_section else context[:2000]}

Find the feature that matches the query. Look intelligently for:
- "rating and review" or "rider rating" → find review/rating features
- "payment" or "HYP payment" → find payment gateway features
- Similar semantic matches

Return JSON:
{{"name": "Feature Name from Estimates.txt", "hours": <number>}}

Return ONLY valid JSON."""
            
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a feature matcher. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                **self._get_max_tokens_param(500)
            )
            
            content = response.choices[0].message.content.strip()
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            
            try:
                result = json.loads(content)
                if "hours" in result and "name" in result:
                    hours = int(result["hours"])
                    min_hours = max(1, int(hours * 0.85))
                    max_hours = int(hours * 1.15)
                    
                    logger.info(f"AI found feature '{result['name']}' in Estimates.txt: {hours} hrs")
                    return {
                        "name": result["name"],
                        "description": f"Based on Estimates.txt",
                        "base_time_hours_min": min_hours,
                        "base_time_hours_max": max_hours,
                        "complexity_level": "medium",
                        "category": "Feature Development"
                    }
            except:
                pass
        except Exception as e:
            logger.debug(f"AI extraction from Estimates.txt failed: {e}")
        
        return None
    
    def _extract_from_estimates_txt_direct(self, query: str, estimates_txt: str) -> Optional[Dict]:
        """Direct fallback: Use AI to extract from Estimates.txt when all else fails"""
        if not self.client or not estimates_txt:
            return None
        
        try:
            prompt = f"""You MUST find a matching feature in Estimates.txt for this query.

Query: {query}

Estimates.txt Content:
{estimates_txt[:4000]}

Find the BEST matching feature from Estimates.txt. Look for:
- Exact matches
- Similar features
- Related functionality

Return JSON with the feature name and hours:
{{"name": "Feature Name from Estimates.txt", "hours": <number>}}

Return ONLY valid JSON."""
            
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a feature matcher. Find the best match in Estimates.txt. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                **self._get_max_tokens_param(500)
            )
            
            content = response.choices[0].message.content.strip()
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            
            try:
                result = json.loads(content)
                if "hours" in result and "name" in result:
                    hours = int(result["hours"])
                    min_hours = max(1, int(hours * 0.85))
                    max_hours = int(hours * 1.15)
                    
                    logger.info(f"Direct fallback found feature '{result['name']}' in Estimates.txt: {hours} hrs")
                    return {
                        "name": result["name"],
                        "description": f"Based on Estimates.txt (direct fallback)",
                        "base_time_hours_min": min_hours,
                        "base_time_hours_max": max_hours,
                        "complexity_level": "medium",
                        "category": "Feature Development"
                    }
            except:
                pass
        except Exception as e:
            logger.debug(f"Direct Estimates.txt extraction failed: {e}")
        
        return None
    
    def _generate_estimate_from_knowledge(self, query: str, context: str, estimates_txt: str = "") -> List[Dict]:
        """FINAL FALLBACK: Generate estimate using model's own knowledge with context"""
        if not self.client:
            return []
        
        try:
            # Prepare context for the model
            context_parts = []
            
            # Parse Estimates.txt JSON schema dynamically - no hardcoded keys
            estimates_schema_info = ""
            if estimates_txt:
                try:
                    # Try to parse as JSON to extract structure
                    estimates_json = json.loads(estimates_txt)
                    # Dynamically extract all sections from the schema
                    schema_parts = []
                    
                    # Dynamically process all top-level keys in the JSON
                    for key, value in estimates_json.items():
                        # Skip metadata as it's not feature estimates
                        if key == "metadata":
                            continue
                        
                        # Special handling for estimation rules (important for new features)
                        if key == "estimation_rules_for_new_features":
                            schema_parts.append(f"=== ESTIMATION RULES FOR NEW FEATURES (PRIMARY GUIDE) ===\n{json.dumps(value, indent=2)}")
                        else:
                            # Dynamically format any other section
                            # Convert key to readable title (e.g., "customer_app_and_web" -> "Customer App And Web")
                            section_title = key.replace("_", " ").title()
                            schema_parts.append(f"\n=== {section_title.upper()} ===\n{json.dumps(value, indent=2)}")
                    
                    estimates_schema_info = "\n\n".join(schema_parts)
                    logger.info(f"Parsed Estimates.txt JSON schema dynamically - {len(schema_parts)} sections found")
                except Exception as e:
                    # If JSON parsing fails, use full raw text
                    logger.warning(f"Could not parse Estimates.txt as JSON: {e} - using raw text")
                    estimates_schema_info = estimates_txt
            
            # Include Enatega product context
            if context:
                context_parts = [f"\n=== ENATEGA PRODUCT CONTEXT ===\n{context[:3000]}"]
            else:
                context_parts = []
            
            combined_context = "\n\n".join(context_parts) if context_parts else ""
            
            prompt = f"""You are an expert estimation analyst. Generate a time estimate for this feature using the Estimates.txt JSON schema as your PRIMARY reference.

Query: {query}

=== ESTIMATES.TXT JSON SCHEMA (PRIMARY REFERENCE - BUILD FROM THIS) ===
{estimates_schema_info if estimates_schema_info else estimates_txt if estimates_txt else "No schema available"}

=== ADDITIONAL CONTEXT ===
{combined_context if combined_context else "No additional context available"}

CRITICAL ESTIMATION INSTRUCTIONS:

1. PRIMARY METHOD - USE ESTIMATES.TXT JSON SCHEMA:
   - Study the JSON schema structure carefully (all sections are provided above)
   - Find the MOST SIMILAR feature in ANY section of the schema to the requested feature
   - Use the hours from that similar feature as your BASE reference
   - If exact match exists, use those hours directly (create ±10% range for min/max)
   - If similar feature exists, adjust hours based on complexity difference (±20% range)
   - Check "estimation_rules_for_new_features" section for guidance on feature types

2. ESTIMATION RULES FROM SCHEMA (if feature type matches):
   - Study the "estimation_rules_for_new_features" section in the schema
   - Use the rules that match your feature type (the rules are provided in the schema above)
   - The rules provide hour ranges for different feature complexities

3. TEAM CONTEXT:
   - Team: 15-20 full-stack developers and engineers
   - Location: Pakistan (efficient, fast delivery)
   - Team works FAST and efficiently
   - Multiple developers can work in parallel
   - Default hourly rate: $30/hour

4. ESTIMATE GENERATION (LOWER/OPTIMISTIC SIDE):
   - ALWAYS provide estimates on the LOWER/OPTIMISTIC side
   - If schema shows 50 hours for similar feature, use 40-55 hours (lower end)
   - Factor in parallel work: With 15-20 developers, work can be divided efficiently
   - Be OPTIMISTIC but realistic - team is experienced and efficient
   - Don't overestimate - consider team size and parallel capacity
   - If schema has range (min/max), use the LOWER end as your base

5. FEATURE MAPPING:
   - Map the requested feature to the closest match in ANY section of the schema
   - Search through ALL sections dynamically (don't limit to specific section names)
   - Find similar features by understanding the feature's purpose and scope
   - Use semantic matching - look for features with similar functionality

Return JSON:
{{
  "name": "Feature Name",
  "description": "Description of what needs to be built",
  "base_time_hours_min": <min_hours>,
  "base_time_hours_max": <max_hours>,
  "complexity_level": "simple|medium|complex",
  "category": "Integration"
}}

Return ONLY valid JSON, no explanations. Base your estimate on the schema values."""
            
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert estimation analyst. Always provide estimates based on your knowledge and context. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                **self._get_max_tokens_param(1000)
            )
            
            content = response.choices[0].message.content.strip()
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            
            try:
                result = json.loads(content)
                # Handle both dict and list responses
                if isinstance(result, dict):
                    features = [result]
                elif isinstance(result, list):
                    features = result
                else:
                    return []
                
                # Normalize and return
                normalized = self._normalize_features(features)
                if normalized:
                    logger.info(f"Generated estimate from model knowledge: {normalized[0].get('name', 'Unknown')} - {normalized[0].get('base_time_hours_min', 0)}-{normalized[0].get('base_time_hours_max', 0)} hours")
                    return normalized
            except Exception as e:
                logger.debug(f"Failed to parse model knowledge response: {e}")
                # Try to extract just the numbers if JSON parsing fails
                try:
                    # Look for hour ranges in the text
                    hour_pattern = r'(\d+)\s*[-–—]\s*(\d+)\s*hours?'
                    match = re.search(hour_pattern, content, re.IGNORECASE)
                    if match:
                        min_hours = int(match.group(1))
                        max_hours = int(match.group(2))
                        return [{
                            "name": query[:50] if len(query) > 50 else query,
                            "description": "Estimate generated from model knowledge",
                            "base_time_hours_min": float(min_hours),
                            "base_time_hours_max": float(max_hours),
                            "complexity_level": "medium",
                            "category": "Integration"
                        }]
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Error generating estimate from knowledge: {e}")
        
        # Return a basic estimate if everything fails
        return [{
            "name": query[:50] if len(query) > 50 else query,
            "description": "Estimate based on general knowledge and context",
            "base_time_hours_min": 25.0,
            "base_time_hours_max": 50.0,
            "complexity_level": "medium",
            "category": "Integration"
        }]
    
    def _extract_feature_name(self, query: str, context_snippet: str) -> str:
        """Extract feature name intelligently - no hardcoded patterns"""
        # Simple extraction - AI handles intelligent naming in main extraction
        words = [w for w in query.split() if w.lower() not in ["i", "want", "to", "add", "how", "much", "it", "take", "in", "enatega"]]
        if words:
            return " ".join(words[:5]).title()
        return "Feature Development"
    
    def extract_features_from_query(self, query: str, context: str = "") -> List[Dict]:
        """Use AI to extract features from natural language query based on document context"""
        if not self.client:
            return []
        
        # FIRST: Check if query is vague/irrelevant before doing expensive extraction
        if self._is_query_vague_or_irrelevant(query):
            logger.info("Query is vague/irrelevant - returning empty list (no feature extraction needed)")
            return []
        
        try:
            # ALWAYS get Estimates.txt as primary reference - this is critical
            estimates_txt = ""
            if self.knowledge_base:
                estimates_txt = self.knowledge_base.get_chatgpt_examples()
                if estimates_txt:
                    # Get FULL Estimates.txt (it's a JSON schema, we need the complete structure)
                    # Don't truncate - we need the full schema for proper parsing
                    logger.info(f"Loaded Estimates.txt ({len(estimates_txt)} chars) as primary reference - FULL JSON SCHEMA")
            
            if not estimates_txt:
                logger.warning("Estimates.txt not available - this should not happen!")
            
            # STEP 1: First try to retrieve information from context (if present)
            # Get comprehensive context from vector store and knowledge base
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
            
            # Combine all context sources
            all_context_sources = []
            if vector_context:
                all_context_sources.append(vector_context)
            if broader_context and broader_context != vector_context:
                all_context_sources.append(broader_context)
            if context and context not in all_context_sources:
                all_context_sources.append(context)
            
            # Check if context has relevant information about the feature
            combined_context_text = "\n\n".join(all_context_sources) if all_context_sources else ""
            context_has_info = False
            if combined_context_text:
                # Check if context mentions the feature or related terms
                query_lower = query.lower()
                query_keywords = [w for w in query_lower.split() if len(w) > 3]
                context_lower = combined_context_text.lower()
                # Check if context contains relevant information
                matches = sum(1 for keyword in query_keywords if keyword in context_lower)
                if matches > 0 or len(combined_context_text) > 500:
                    context_has_info = True
                    logger.info(f"Context contains relevant information ({matches} keyword matches, {len(combined_context_text)} chars)")
            
            # STEP 2: Build context with priority: Context first (if present), then Estimates.txt
            context_parts = []
            
            if context_has_info and combined_context_text:
                # PRIMARY: Use context if it has relevant information
                context_parts.append(f"=== RELEVANT CONTEXT (PRIMARY - USE THIS IF IT HAS FEATURE INFO) ===\n{combined_context_text}")
                logger.info("Using context as PRIMARY source (contains relevant information)")
            
            # SECONDARY: Estimates.txt (fallback if context doesn't have info, or as reference)
            if estimates_txt:
                if context_has_info:
                    # Include Estimates.txt as reference/fallback
                    context_parts.append(f"\n=== ESTIMATES.TXT JSON SCHEMA (REFERENCE/FALLBACK - FULL SCHEMA) ===\n{estimates_txt}")
                    logger.info(f"Estimates.txt included as reference/fallback ({len(estimates_txt)} chars)")
                else:
                    # No context info, use Estimates.txt as primary
                    context_parts.append(f"=== ESTIMATES.TXT JSON SCHEMA (PRIMARY - NO CONTEXT INFO FOUND) ===\n{estimates_txt}")
                    logger.info(f"Using Estimates.txt as PRIMARY source (no relevant context found) ({len(estimates_txt)} chars)")
            else:
                logger.error("CRITICAL: Estimates.txt not available!")
            
            # Combine everything - Context first (if present), then Estimates.txt
            combined_context = "\n\n".join(context_parts) if context_parts else estimates_txt if estimates_txt else ""
            
            if not combined_context:
                logger.error("No context available - checking if query is vague/irrelevant")
                # If no context and no features extracted, verify if query is vague
                if self._is_query_vague_or_irrelevant(query):
                    logger.info("Query is vague/irrelevant - returning empty list")
                    return []
                logger.warning("No context but query seems relevant - returning empty (should not happen)")
                return []
            
            logger.info(f"Combined context length: {len(combined_context)} characters from {len(context_parts)} sources (Estimates.txt MANDATORY)")
            
            # Parse Estimates.txt JSON schema if available
            estimates_schema_info = ""
            if estimates_txt:
                try:
                    # Try to parse as JSON to extract structure
                    estimates_json = json.loads(estimates_txt)
                    # Dynamically extract all sections from the schema
                    schema_parts = []
                    
                    # Dynamically process all top-level keys in the JSON
                    for key, value in estimates_json.items():
                        # Skip metadata as it's not feature estimates
                        if key == "metadata":
                            continue
                        
                        # Special handling for estimation rules (important for new features)
                        if key == "estimation_rules_for_new_features":
                            schema_parts.append(f"=== ESTIMATION RULES FOR NEW FEATURES (PRIMARY GUIDE) ===\n{json.dumps(value, indent=2)}")
                        else:
                            # Dynamically format any other section
                            # Convert key to readable title (e.g., "customer_app_and_web" -> "Customer App And Web")
                            section_title = key.replace("_", " ").title()
                            schema_parts.append(f"\n=== {section_title.upper()} ===\n{json.dumps(value, indent=2)}")
                    
                    estimates_schema_info = "\n\n".join(schema_parts)
                    logger.info(f"Parsed Estimates.txt JSON schema dynamically - {len(schema_parts)} sections found")
                except Exception as e:
                    # If JSON parsing fails, use full raw text
                    logger.warning(f"Could not parse Estimates.txt as JSON: {e} - using raw text")
                    estimates_schema_info = estimates_txt
            
            # Use intelligent AI analysis - prioritize context first, then Estimates.txt
            prompt = f"""You are an expert estimation analyst. Analyze the requirements and generate intelligent time estimates.

Requirements: {query}

=== AVAILABLE CONTEXT (PRIORITY ORDER) ===
{combined_context}

CRITICAL ESTIMATION INSTRUCTIONS:

1. PRIORITY METHOD - CHECK CONTEXT FIRST:
   - FIRST: Check if the context above contains information about the requested feature
   - If context has relevant feature information (hours, estimates, similar features), USE THAT as PRIMARY reference
   - Extract hours/estimates directly from context if available
   - If context has similar features, use those as base reference
   
2. FALLBACK METHOD - USE ESTIMATES.TXT JSON SCHEMA (CRITICAL - USE EXACT VALUES):
   - If context does NOT have relevant information, use Estimates.txt JSON schema
   - The Estimates.txt contains a JSON schema with feature estimates in hours
   - Study ALL sections in the schema dynamically (the schema structure is provided above)
   - Find the EXACT or MOST SIMILAR feature in the schema to the requested feature
   
   CRITICAL: When you find a matching feature in Estimates.txt:
   - If the feature has "min" and "max" values, USE THOSE EXACT VALUES
   - Example: "uber_eats_style_delivery_integration": {{"min": 78, "max": 100}}
     → Use 78-100 hours DIRECTLY (apply lower/optimistic range: 70-95 hours)
   - Example: "ai_orchestration_for_integrations": {{"min": 82, "max": 90}}
     → Use 82-90 hours DIRECTLY (apply lower/optimistic range: 75-85 hours)
   - DO NOT multiply or add these values - use them as base
   - Apply 40-45% LOWER/OPTIMISTIC reduction for Pakistan-based team efficiency
   - If exact match exists, use those min/max values directly with optimistic reduction
   - If similar feature exists, use those values as reference with small adjustment
   - Check "estimation_rules_for_new_features" section for guidance on feature types

2. ESTIMATION RULES FROM SCHEMA (if feature type matches):
   - Study the "estimation_rules_for_new_features" section in the schema
   - Use the rules that match your feature type (the rules are provided in the schema above)
   - The rules provide hour ranges for different feature complexities

3. TEAM CONTEXT (ALWAYS CONSIDER):
   - Team: 15-20 full-stack developers and engineers
   - Location: Pakistan (efficient, fast delivery)
   - Team works FAST and efficiently
   - Multiple developers can work in parallel
   - Default hourly rate: $30/hour

4. ESTIMATE GENERATION (LOWER/OPTIMISTIC SIDE - PAKISTAN-BASED TEAM):
   - CRITICAL: ALWAYS provide estimates on the LOWER/OPTIMISTIC side
   - This is for a Pakistan-based team (20-25 developers, fast and efficient)
   - If context or Estimates.txt shows 50 hours for similar feature, use 40-55 hours (lower end)
   - Factor in parallel work: With 15-20 developers, work can be divided efficiently
   - Be OPTIMISTIC but realistic - Pakistan-based team is experienced, fast, and efficient
   - Don't overestimate - consider team size, parallel capacity, and Pakistan-based efficiency
   - If schema has range (min/max), use the LOWER end as your base
   - Apply 40-45% reduction for Pakistan-based team efficiency and parallel work capacity

5. FEATURE MAPPING:
   - Map the requested feature to the closest match in the schema
   - Search through ALL sections dynamically (don't limit to specific section names)
   - Find similar features by understanding the feature's purpose and scope
   - Use semantic matching - look for features with similar functionality

6. FINAL ESTIMATE (LOWER/OPTIMISTIC - PAKISTAN-BASED):
   - Base your estimate on context (if available) OR schema value (if context doesn't have info)
   
   CRITICAL FOR ESTIMATES.TXT VALUES:
   - If you found exact match in Estimates.txt with min/max values, use those EXACTLY
   - Example: "uber_eats_style_delivery_integration": {{"min": 78, "max": 100}}
     → Return: base_time_hours_min: 70, base_time_hours_max: 95 (10-15% lower/optimistic)
   - DO NOT combine multiple features unless user explicitly asks for multiple features
   - If user asks for ONE feature, return estimate for THAT ONE feature only
   
   GENERAL RULES:
   - Apply ±10-15% range for min/max (lean toward LOWER side)
   - Consider Pakistan-based team efficiency (20-25 developers, fast, efficient)
   - Factor in parallel work capacity
   - Provide OPTIMISTIC but realistic estimate - always on the lower side
   - Remember: Pakistan-based teams are efficient and can work in parallel effectively

Return COMPLETE JSON array (ensure valid JSON, all brackets closed):
[
  {{
    "name": "Feature Name",
    "description": "Description based on requirements and context analysis",
    "base_time_hours_min": <min_hours>,
    "base_time_hours_max": <max_hours>,
    "complexity_level": "simple|medium|complex",
    "category": "Category"
  }}
]"""
            
            system_prompt = """You are an expert estimation analyst specializing in software development time estimation.

YOUR ROLE:
- Analyze requirements intelligently
- FIRST: Check context for relevant feature information (if present)
- SECOND: Use Estimates.txt JSON SCHEMA as fallback (if context doesn't have info)
- Build estimates FROM context OR schema structure
- Generate estimates on the LOWER/OPTIMISTIC side for Pakistan-based team

ESTIMATION APPROACH:
1. PRIORITY: Check context first
   - If context has relevant feature information, USE THAT as PRIMARY
   - Extract hours/estimates directly from context if available
   - If context has similar features, use those as base reference

2. FALLBACK: Study Estimates.txt JSON schema structure (if context doesn't have info)
   - Find the EXACT or MOST SIMILAR feature in the schema
   - CRITICAL: If feature has "min" and "max" values, USE THOSE EXACT VALUES
   - Example: "uber_eats_style_delivery_integration": {{"min": 78, "max": 100}}
     → Use 78-100 hours DIRECTLY, then apply 40-45% lower/optimistic (70-95 hours)
   - DO NOT multiply or combine multiple features unless explicitly requested
   - Apply ±40-45% range (lean toward LOWER side) for Pakistan-based team
   - Check "estimation_rules_for_new_features" for feature type guidance

3. ESTIMATION RULES (from schema):
   - Study the "estimation_rules_for_new_features" section in the schema
   - Use the rules that match your feature type (the rules are provided in the schema above)
   - The rules provide hour ranges for different feature complexities

4. TEAM CONTEXT (always consider):
   - 15-20 full-stack developers available
   - Pakistan-based, efficient team
   - Parallel work capacity
   - Lower estimates due to team size and efficiency
   - Apply 40-45% reduction for Pakistan-based team efficiency

5. ESTIMATE GENERATION (LOWER/OPTIMISTIC):
   - ALWAYS provide estimates on the LOWER/OPTIMISTIC side
   
   CRITICAL FOR ESTIMATES.TXT:
   - If Estimates.txt shows {{"min": 78, "max": 100}}, use those EXACT values
   - Apply 40-45% LOWER reduction: 78-100 → 70-95 hours
   - DO NOT combine multiple features - use only the matching feature
   - If user asks for "uber eats integration", return ONLY that feature's estimate
   
   GENERAL RULES:
   - If context or schema shows 50 hours, use 40-55 hours (lower end)
   - Factor in parallel work with 15-20 developers
   - Be OPTIMISTIC but realistic
   - Apply 40-50% reduction for Pakistan-based team efficiency

6. FEATURE MAPPING:
   - Map to closest feature in context (if available) OR schema category
   - Use similar features as reference
   - Apply appropriate estimation rules

Return ONLY valid JSON array, no explanations.
Format: [{"name": "...", "description": "...", "base_time_hours_min": <min>, "base_time_hours_max": <max>, "complexity_level": "...", "category": "..."}]
ALWAYS base estimates on context (if available) OR schema values - build FROM context first, then schema."""
            
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Very low for accurate extraction
                **self._get_max_tokens_param(2500)  # Increased to ensure complete JSON
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
            
            # Strategy 4: Try to extract from Estimates.txt directly if JSON parsing fails
            logger.warning(f"Could not parse JSON, attempting to extract from Estimates.txt. Content preview: {content[:200]}")
            
            # Try to find feature in Estimates.txt context
            estimates_match = self._extract_from_estimates_txt(query, combined_context)
            if estimates_match:
                logger.info(f"Found feature in Estimates.txt: {estimates_match['base_time_hours_min']}-{estimates_match['base_time_hours_max']} hours")
                return [estimates_match]
            
            # Strategy 5: Direct Estimates.txt fallback (use Estimates.txt directly)
            if estimates_txt:
                logger.warning("Using direct Estimates.txt fallback")
                direct_result = self._extract_from_estimates_txt_direct(query, estimates_txt)
                if direct_result:
                    logger.info("Successfully extracted from Estimates.txt using direct fallback")
                    return [direct_result]
            
            # Try fallback extraction
            fallback_result = self._fallback_feature_extraction(query, combined_context)
            if fallback_result:
                return fallback_result
            
            # FINAL FALLBACK: Use model's own knowledge with context
            logger.warning("All extraction methods failed, using model's own knowledge as final fallback")
            final_fallback = self._generate_estimate_from_knowledge(query, combined_context, estimates_txt)
            if final_fallback:
                logger.info("Successfully generated estimate using model's own knowledge")
                return final_fallback
            
            # This should never happen, but if it does, return a basic estimate
            logger.error("Even final fallback failed - returning basic estimate")
            return [{
                "name": query[:50] if len(query) > 50 else query,
                "description": "Estimate based on general knowledge",
                "base_time_hours_min": 20.0,
                "base_time_hours_max": 40.0,
                "complexity_level": "medium",
                "category": "Integration"
            }]
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}", exc_info=True)
            
            # Try Estimates.txt extraction first
            estimates_match = self._extract_from_estimates_txt(query, combined_context)
            if estimates_match:
                logger.info(f"Found feature in Estimates.txt during error handling: {estimates_match['base_time_hours_min']}-{estimates_match['base_time_hours_max']} hours")
                return [estimates_match]
            
            # Direct Estimates.txt fallback (use Estimates.txt directly)
            if estimates_txt:
                logger.warning("Using direct Estimates.txt fallback after exception")
                direct_result = self._extract_from_estimates_txt_direct(query, estimates_txt)
                if direct_result:
                    logger.info("Successfully extracted from Estimates.txt using direct fallback after exception")
                    return [direct_result]
            
            # Try fallback extraction
            fallback_result = self._fallback_feature_extraction(query, combined_context)
            if fallback_result:
                return fallback_result
            
            # FINAL FALLBACK: Use model's own knowledge with context
            logger.warning("All extraction methods failed after exception, using model's own knowledge as final fallback")
            final_fallback = self._generate_estimate_from_knowledge(query, combined_context, estimates_txt)
            if final_fallback:
                logger.info("Successfully generated estimate using model's own knowledge after exception")
                return final_fallback
            
            # Before returning basic estimate, check if query is vague/irrelevant
            if self._is_query_vague_or_irrelevant(query):
                logger.info("Query is vague/irrelevant - returning empty list")
                return []
            
            # This should never happen, but if it does, return a basic estimate
            logger.error("Even final fallback failed after exception - returning basic estimate")
            return [{
                "name": query[:50] if len(query) > 50 else query,
                "description": "Estimate based on general knowledge",
                "base_time_hours_min": 20.0,
                "base_time_hours_max": 40.0,
                "complexity_level": "medium",
                "category": "Integration"
            }]
    
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
    
    def _is_query_vague_or_irrelevant(self, query: str) -> bool:
        """Use LLM to determine if query is vague or irrelevant (not asking for feature estimate)"""
        if not self.client:
            return False
        
        try:
            prompt = f"""Analyze the following user query and determine if it is asking for a feature development estimate.

Query: "{query}"

CRITICAL: Determine if this query is:
1. ASKING FOR A FEATURE ESTIMATE (relevant):
   - Examples: "add payment integration", "uber eats integration", "AWS integration", "add HYP payment method"
   - These queries describe a specific feature/functionality to be built
   - Set "is_vague_or_irrelevant" to FALSE
   - If the attached file has multiple features, then too query is not Vague

2. VAGUE/IRRELEVANT (not asking for estimate):
   - Examples: "requirements are in file attached", "see attached file", "check the document", "requirements in file", "see document", "hello", "how are you", "what can you do"
   - These queries are just references to files, greetings, or general questions
   - They do NOT describe what feature needs to be built
   - Set "is_vague_or_irrelevant" to TRUE
   - If the attached file has multiple relevant features then query is not vague.

IMPORTANT: If query or file has relevant features then query is not vague, else vague.
If the query describes a specific feature/functionality to estimate, it is RELEVANT.

Respond with ONLY a JSON object:
{{
    "is_vague_or_irrelevant": true/false,
    "reason": "brief explanation"
}}"""

            max_tokens_param = self._get_max_tokens_param(100)
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that analyzes queries to determine if they are asking for feature development estimates."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                **max_tokens_param
            )
            
            content = response.choices[0].message.content.strip()
            logger.debug(f"LLM vague query check response: {content}")
            
            # Try to parse JSON response
            try:
                # Remove markdown code blocks if present
                content = re.sub(r'```json\s*', '', content)
                content = re.sub(r'```\s*', '', content)
                result = json.loads(content)
                is_vague = result.get("is_vague_or_irrelevant", False)
                reason = result.get("reason", "")
                logger.info(f"Query vague check: {is_vague} - {reason}")
                return is_vague
            except json.JSONDecodeError:
                # If JSON parsing fails, check if response contains keywords
                content_lower = content.lower()
                if "true" in content_lower or "vague" in content_lower or "irrelevant" in content_lower:
                    logger.info("LLM indicated query is vague (from text analysis)")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error checking if query is vague: {e}")
            # On error, assume query is relevant (don't block legitimate queries)
            return False
    
    def _fallback_feature_extraction(self, query: str, context: str) -> List[Dict]:
        """Fallback: Extract features using intelligent analysis when JSON parsing fails"""
        if not self.client:
            return []
        
        try:
            # First try Estimates.txt extraction
            estimates_match = self._extract_from_estimates_txt(query, context)
            if estimates_match:
                return [estimates_match]
            
            prompt = f"""Analyze the requirements and generate intelligent time estimates by studying ALL context, especially Estimates.txt.

Query: {query}

COMPREHENSIVE CONTEXT (study ALL of this, prioritize Estimates.txt):
{context[:4000] if context else "No context available - use your knowledge"}

ANALYSIS INSTRUCTIONS:
1. Study the requirements - what needs to be built?
2. Search Estimates.txt in context for matching features (PRIMARY REFERENCE)
3. Analyze context comprehensively:
   - Estimates.txt feature estimates
   - Team composition and capabilities (size, skills, roles)
   - Project complexity and requirements
   - Similar work or patterns from context
   - Technology stack and infrastructure
4. Generate intelligent estimates considering:
   - Estimates.txt values (if feature exists) as base reference
   - Team capabilities: 15-20 full-stack developers and engineers available
   - Team efficiency: FAST, experienced, Pakistan-based team
   - Project complexity
   - Realistic but OPTIMISTIC development timelines (with 15-20 developers in parallel)
   - Parallel work possibilities: Divide work across 15-20 developers efficiently
   - When predicting from own knowledge: Be OPTIMISTIC - with large team, estimates should be efficient

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
                **self._get_max_tokens_param(2500)  # Increased for complete JSON
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
                **self._get_max_tokens_param(600)  # Reduced for more concise responses
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
                **self._get_max_tokens_param(600)  # Reduced for concise responses
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
