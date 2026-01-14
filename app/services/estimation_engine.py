from typing import List, Dict, Optional
from app.models.schemas import FeatureBreakdown, EstimateResponse
from app.core.config import settings
import logging
import re

logger = logging.getLogger(__name__)

class EstimationEngine:
    """Core estimation logic for time and cost calculations"""
    
    def __init__(self, hourly_rate: Optional[float] = None):
        self.hourly_rate = hourly_rate or settings.DEFAULT_HOURLY_RATE
        self.buffer_percentage = settings.BUFFER_PERCENTAGE
        
        # Complexity multipliers
        self.complexity_multipliers = {
            "simple": 1.0,
            "medium": 1.3,
            "complex": 1.8
        }
    
    def calculate_feature_time(self, base_hours: float, complexity: str = "medium") -> float:
        """Calculate time for a feature based on complexity"""
        multiplier = self.complexity_multipliers.get(complexity.lower(), 1.3)
        return base_hours * multiplier
    
    def calculate_feature_cost(self, time_hours: float) -> float:
        """Calculate cost for a feature"""
        return time_hours * self.hourly_rate
    
    def apply_buffer(self, time_hours: float) -> float:
        """Apply buffer percentage to time estimate"""
        return time_hours * (1 + self.buffer_percentage)
    
    def create_breakdown(self, features: List[Dict]) -> List[FeatureBreakdown]:
        """Create detailed breakdown from features with ranges"""
        breakdown = []
        
        for feature in features:
            # Get min and max hours
            base_time_min = feature.get("base_time_hours_min", feature.get("base_time_hours", 0))
            base_time_max = feature.get("base_time_hours_max", base_time_min * 1.2)
            
            complexity = feature.get("complexity_level", "medium")
            
            # Don't apply complexity multiplier if ranges already account for it
            # The ranges from AI already include complexity considerations
            # Only apply buffer for unforeseen issues
            final_time_min = base_time_min * (1 + self.buffer_percentage)
            final_time_max = base_time_max * (1 + self.buffer_percentage)
            
            # Calculate cost ranges
            cost_min = final_time_min * self.hourly_rate
            cost_max = final_time_max * self.hourly_rate
            
            breakdown.append(FeatureBreakdown(
                feature=feature.get("name", "Unknown"),
                description=feature.get("description"),
                time_hours=round((final_time_min + final_time_max) / 2, 2),  # Average for display
                cost=round((cost_min + cost_max) / 2, 2),  # Average for display
                complexity=complexity,
                time_min=round(final_time_min, 2),
                time_max=round(final_time_max, 2),
                cost_min=round(cost_min, 2),
                cost_max=round(cost_max, 2)
            ))
        
        return breakdown
    
    def calculate_total(self, breakdown: List[FeatureBreakdown]) -> tuple:
        """Calculate total time and cost ranges"""
        total_time_min = sum(getattr(item, 'time_min', item.time_hours * 0.9) for item in breakdown)
        total_time_max = sum(getattr(item, 'time_max', item.time_hours * 1.1) for item in breakdown)
        total_cost_min = sum(getattr(item, 'cost_min', item.cost * 0.9) for item in breakdown)
        total_cost_max = sum(getattr(item, 'cost_max', item.cost * 1.1) for item in breakdown)
        
        return (
            round(total_time_min, 2),
            round(total_time_max, 2),
            round(total_cost_min, 2),
            round(total_cost_max, 2)
        )
    
    def generate_assumptions(self, breakdown: List[FeatureBreakdown]) -> List[str]:
        """Generate assumptions list"""
        assumptions = [
            "Estimates are based on standard implementation practices",
            "Time includes development, testing, and basic documentation",
            "A 20% buffer has been included for unforeseen complexities",
            "Costs assume standard hourly rate",
            "Timeline assumes dedicated development resources",
            "Does not include third-party service costs unless specified",
            "Assumes clear requirements and minimal scope changes"
        ]
        return assumptions
    
    def estimate_timeline(self, total_hours: float) -> str:
        """Estimate project timeline"""
        # Assuming 8 hours per day, 5 days per week
        days = total_hours / 8
        weeks = days / 5
        
        if weeks < 1:
            return f"Approximately {int(days)} working days"
        elif weeks < 4:
            return f"Approximately {int(weeks)} weeks"
        else:
            months = weeks / 4
            return f"Approximately {int(months)} months ({int(weeks)} weeks)"
