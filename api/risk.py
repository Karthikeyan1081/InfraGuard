"""Risk Analysis API endpoint."""
import logging
from typing import Any, Dict

from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel

from services.risk_analysis_service import RiskAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/risk", tags=["Risk Analysis"])


class RiskRequest(BaseModel):
    infrastructure_data: Dict[str, Any]


class RiskResponse(BaseModel):
    status: str
    risk_assessment: str
    asset_count: int
    mismatch_count: int


@router.post("/analyze", response_model=RiskResponse)
async def analyze_risk(req: RiskRequest):
    """
    Run risk analysis on infrastructure data.

    Args:
        req: Infrastructure data to analyze.

    Returns:
        Risk assessment with identified risks and priority levels.
    """
    try:
        svc = RiskAnalysisService()
        result = svc.analyze_risks(req.infrastructure_data)
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error"))
        return result
    except Exception as exc:
        logger.exception("Risk analysis endpoint failed")
        raise HTTPException(status_code=500, detail=str(exc))
