"""Coordinator/Orchestration API endpoint."""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.coordinator_service import CoordinatorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orchestration", tags=["Orchestration"])


class OrchestrationRequest(BaseModel):
    infrastructure_data: Dict[str, Any]
    include_planning: bool = True


class OrchestrationResponse(BaseModel):
    status: str
    phases: Dict[str, Any]
    summary: Optional[str] = None
    error: Optional[str] = None


@router.post("/analyze", response_model=OrchestrationResponse)
async def run_full_analysis(req: OrchestrationRequest):
    """
    Run complete analysis orchestration: reconciliation → risk → recommendations → planning.

    Args:
        req: Infrastructure data and orchestration options.

    Returns:
        Comprehensive analysis with outputs from all agents and executive summary.
    """
    try:
        coordinator = CoordinatorService()
        result = await coordinator.run_full_analysis(
            req.infrastructure_data, req.include_planning
        )
        return result
    except Exception as exc:
        logger.exception("Orchestration endpoint failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status")
async def get_orchestration_status():
    """Get status of all orchestrated agents."""
    try:
        coordinator = CoordinatorService()
        return {"agents": coordinator.get_agent_status()}
    except Exception as exc:
        logger.exception("Status endpoint failed")
        raise HTTPException(status_code=500, detail=str(exc))
