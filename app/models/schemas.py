from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Feature(BaseModel):
    name: str
    description: Optional[str] = None
    base_time_hours: float = 0.0
    base_cost: float = 0.0
    complexity_level: str = "medium"  # simple, medium, complex
    dependencies: List[str] = []
    category: Optional[str] = None

class SubFeature(BaseModel):
    name: str
    time_min: float
    time_max: float

class FeatureBreakdown(BaseModel):
    feature: str
    description: Optional[str] = None
    time_hours: float  # Average for backward compatibility
    cost: float  # Average for backward compatibility
    complexity: Optional[str] = None
    time_min: Optional[float] = None
    time_max: Optional[float] = None
    cost_min: Optional[float] = None
    cost_max: Optional[float] = None
    sub_features: Optional[List[SubFeature]] = None

class EstimateRequest(BaseModel):
    requirements: Optional[str] = Field(None, description="Client requirements in natural language (optional if file provided)")
    hourly_rate: Optional[float] = Field(None, description="Custom hourly rate (optional)")

class FeatureDescription(BaseModel):
    feature: str
    description: Optional[str] = None

class EstimateResponse(BaseModel):
    estimated_time_hours_min: float = Field(..., description="Minimum estimated time in hours")
    estimated_time_hours_max: float = Field(..., description="Maximum estimated time in hours")
    estimated_cost_min: float = Field(..., description="Minimum estimated cost in dollars")
    estimated_cost_max: float = Field(..., description="Maximum estimated cost in dollars")
    feature_breakdown: Optional[str] = Field(None, description="Detailed feature breakdown with time ranges in bullet points format")
    features_description: Optional[List[FeatureDescription]] = Field(None, description="AI-generated description for each identified feature")

class ChatMessage(BaseModel):
    role: str  # user, assistant, system
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    context: Optional[Dict[str, Any]] = {}

class ChatResponse(BaseModel):
    response: str
    estimate: Optional[EstimateResponse] = None
    conversation_id: Optional[str] = None

class FeatureListResponse(BaseModel):
    features: List[Feature]
    total_count: int
