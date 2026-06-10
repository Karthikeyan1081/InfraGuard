"""Recommendation Generation API endpoint."""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


class RecommendationRequest(BaseModel):
    infrastructure_data: Dict[str, Any]
    risk_assessment: Optional[str] = None


class RecommendationResponse(BaseModel):
    status: str
    recommendations: str
    asset_count: int
    mismatch_count: int


@router.post("/generate", response_model=RecommendationResponse)
async def generate_recommendations(req: RecommendationRequest):
    """
    Generate remediation recommendations based on infrastructure analysis.

    Args:
        req: Infrastructure data and optional risk assessment.

    Returns:
        Structured recommendations with timelines and effort estimates.
    """
    try:
        svc = RecommendationService()
        result = svc.generate_recommendations(
            req.infrastructure_data, req.risk_assessment
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error"))
        return result
    except Exception as exc:
        logger.exception("Recommendation generation endpoint failed")
        raise HTTPException(status_code=500, detail=str(exc))
