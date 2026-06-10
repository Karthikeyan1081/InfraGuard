"""Planning/Execution Plan API endpoint."""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.planning_service import PlanningService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/planning", tags=["Planning"])


class PlanningRequest(BaseModel):
    infrastructure_data: Dict[str, Any]
    risk_assessment: Optional[str] = None
    recommendations: Optional[str] = None


class PlanningResponse(BaseModel):
    status: str
    execution_plan: str
    asset_count: int
    mismatch_count: int


@router.post("/create-plan", response_model=PlanningResponse)
async def create_execution_plan(req: PlanningRequest):
    """
    Create detailed execution plan for remediation actions.

    Args:
        req: Infrastructure data, risk assessment, and recommendations.

    Returns:
        Phase-based execution plan with timelines and resource requirements.
    """
    try:
        svc = PlanningService()
        result = svc.create_execution_plan(
            req.infrastructure_data, req.risk_assessment, req.recommendations
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error"))
        return result
    except Exception as exc:
        logger.exception("Planning endpoint failed")
        raise HTTPException(status_code=500, detail=str(exc))
