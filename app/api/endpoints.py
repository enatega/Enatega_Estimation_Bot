from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from app.models.schemas import (
    EstimateRequest, EstimateResponse, ChatRequest, ChatResponse,
    FeatureListResponse, Feature
)
from app.services.estimation_engine import EstimationEngine
from app.services.openai_service import OpenAIService
from app.services.knowledge_base import KnowledgeBase
from app.utils.document_extractor import DocumentExtractor
from app.core.config import settings
import logging
import uuid
import tempfile
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services (singleton pattern) - loaded once at startup
# These are set in main.py startup event
_knowledge_base = None
_openai_service = None
_estimation_engine = None

def get_knowledge_base():
    """Get cached knowledge base instance"""
    global _knowledge_base
    if _knowledge_base is None:
        # This should only happen if not initialized at startup
        logger.warning("Knowledge base not initialized at startup, loading now...")
        _knowledge_base = KnowledgeBase(settings.DATA_DIR)
    return _knowledge_base

def get_openai_service():
    """Get cached OpenAI service instance"""
    global _openai_service
    if _openai_service is None:
        kb = get_knowledge_base()
        _openai_service = OpenAIService(kb)
    return _openai_service

def get_estimation_engine(hourly_rate: float = None):
    return EstimationEngine(hourly_rate)

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Estimation Bot API",
        "version": settings.VERSION
    }

@router.post("/estimate", response_model=EstimateResponse)
async def create_estimate(
    requirements: str = Form(None),
    hourly_rate: float = Form(None),
    file: UploadFile = File(None),
    kb: KnowledgeBase = Depends(get_knowledge_base),
    openai_service: OpenAIService = Depends(get_openai_service)
):
    """
    Generate time and cost estimate based on client requirements.
    Accepts text requirements, PDF/DOCX/DOC/TXT file, or both.
    Returns only Estimated Time and Estimated Cost.
    """
    try:
        # Combine text and file content
        combined_requirements = ""
        
        # Add text requirements if provided
        if requirements:
            combined_requirements += requirements + "\n\n"
        
        # Extract text from uploaded file if provided
        if file:
            logger.info(f"Processing uploaded file: {file.filename}")
            extractor = DocumentExtractor()
            
            # Save uploaded file temporarily
            file_extension = os.path.splitext(file.filename)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            try:
                # Extract text based on file type
                if file_extension == '.pdf':
                    file_text = extractor.extract_pdf_text(tmp_path)
                elif file_extension in ['.docx', '.doc']:
                    file_text = extractor.extract_docx_text(tmp_path)
                elif file_extension == '.txt':
                    file_text = extractor.extract_txt_text(tmp_path)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported file type: {file_extension}. Please upload PDF, DOCX, DOC, or TXT files."
                    )
                
                combined_requirements += f"Content from {file.filename}:\n{file_text}\n\n"
                logger.info(f"Extracted {len(file_text)} characters from {file.filename}")
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        if not combined_requirements.strip():
            raise HTTPException(
                status_code=400,
                detail="Please provide either text requirements or upload a PDF/DOCX/DOC/TXT file (or both)."
            )
        
        logger.info(f"Processing estimate request (text length: {len(combined_requirements)})...")
        
        # Get relevant context from documents for better feature extraction
        # Note: Estimates.txt is ALWAYS included in extract_features_from_query
        context = kb.get_context_for_query(combined_requirements, max_length=3000)
        features = openai_service.extract_features_from_query(combined_requirements, context)
        
        if not features:
            logger.warning("No features extracted - trying with more context")
            # Try again with more context
            context = kb.get_context_for_query(combined_requirements, max_length=5000)
            features = openai_service.extract_features_from_query(combined_requirements, context)
            
            if not features:
                logger.error("Feature extraction failed after retry - final fallback should have worked")
                # This should never happen now as we have a final fallback that always returns something
                # But if it does, return a generic estimate
                logger.warning("Using emergency fallback - generating basic estimate")
                features = [{
                    "name": combined_requirements[:50] if len(combined_requirements) > 50 else combined_requirements,
                    "description": "Estimate based on requirements",
                    "base_time_hours_min": 30.0,
                    "base_time_hours_max": 60.0,
                    "complexity_level": "medium",
                    "category": "Feature Development"
                }]
        
        # Create estimation engine - use $30/hour as default (company rate)
        engine = get_estimation_engine(hourly_rate or 30.0)
        
        # Create breakdown
        breakdown = engine.create_breakdown(features)
        
        # Calculate totals (returns min/max ranges)
        total_time_min, total_time_max, total_cost_min, total_cost_max = engine.calculate_total(breakdown)
        
        # Return simplified response with time and cost ranges
        return EstimateResponse(
            estimated_time_hours_min=total_time_min,
            estimated_time_hours_max=total_time_max,
            estimated_cost_min=total_cost_min,
            estimated_cost_max=total_cost_max
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating estimate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating estimate: {str(e)}")

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    openai_service: OpenAIService = Depends(get_openai_service)
):
    """
    Chat endpoint for conversational interaction
    """
    try:
        # Convert conversation history to OpenAI format
        history = []
        for msg in request.conversation_history:
            history.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Generate response
        response_text = openai_service.chat(request.message, history)
        
        # Check if the message is asking for an estimate - always try to generate estimate
        estimate = None
        try:
            from app.models.schemas import EstimateRequest
            estimate_req = EstimateRequest(requirements=request.message)
            estimate_response = await create_estimate(estimate_req, get_knowledge_base(), openai_service)
            estimate = estimate_response
        except Exception as e:
            logger.warning(f"Could not generate estimate in chat: {e}")
            # Continue without estimate
        
        return ChatResponse(
            response=response_text,
            estimate=estimate,
            conversation_id=str(uuid.uuid4())
        )
    
    except Exception as e:
        logger.error(f"Error in chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@router.get("/features", response_model=FeatureListResponse)
async def get_features(
    kb: KnowledgeBase = Depends(get_knowledge_base)
):
    """
    Get list of available features
    """
    try:
        features_data = kb.extract_features()
        features = [Feature(**f) for f in features_data]
        
        return FeatureListResponse(
            features=features,
            total_count=len(features)
        )
    except Exception as e:
        logger.error(f"Error getting features: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving features: {str(e)}")
