"""Planning Agent – creates execution timelines and resource allocation plans."""
import json
import logging
from typing import Any, Dict, List, Optional

from services.agent_llm import AgentLLM

logger = logging.getLogger(__name__)


class PlanningService:
    """Creates detailed execution plans and resource allocation strategies."""

    def __init__(self, llm: Optional[AgentLLM] = None):
        self.llm = llm or AgentLLM()

    def create_execution_plan(
        self,
        infrastructure_data: Dict[str, Any],
        risk_assessment: Optional[str] = None,
        recommendations: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a detailed execution plan with timelines and resource allocation.

        Args:
            infrastructure_data: Asset inventory or reconciliation results.
            risk_assessment: Optional risk assessment output.
            recommendations: Optional recommendations output.

        Returns:
            Structured execution plan with phases, timelines, and resource requirements.
        """
        logger.info("Creating execution plan.")
        try:
            assets = infrastructure_data.get("assets", [])
            mismatches = infrastructure_data.get("mismatches", [])

            plan_prompt = self._build_planning_prompt(
                assets, mismatches, risk_assessment, recommendations
            )
            execution_plan = self.llm.summarize(plan_prompt)

            return {
                "status": "success",
                "execution_plan": execution_plan,
                "asset_count": len(assets),
                "mismatch_count": len(mismatches),
            }
        except Exception as e:
            logger.exception("Planning failed")
            return {"status": "error", "error": str(e)}

    def _build_planning_prompt(
        self,
        assets: List[Dict],
        mismatches: List[Dict],
        risk_assessment: Optional[str],
        recommendations: Optional[str],
    ) -> str:
        """Build prompt for execution planning."""
        prompt = "Create a detailed execution plan for remediation and optimization:\n\n"
        prompt += f"Total Assets: {len(assets)}\n"
        prompt += f"Reconciliation Mismatches: {len(mismatches)}\n\n"

        if risk_assessment:
            prompt += f"Risk Assessment Summary:\n{risk_assessment[:500]}...\n\n"

        if recommendations:
            prompt += f"Recommendations Summary:\n{recommendations[:500]}...\n\n"

        prompt += "Create an execution plan including:\n"
        prompt += "1. Phase-based breakdown (discovery, planning, execution, validation)\n"
        prompt += "2. Detailed timeline with milestones (weeks/months)\n"
        prompt += "3. Resource requirements (team members, skills, tools)\n"
        prompt += "4. Dependencies and critical path\n"
        prompt += "5. Risk mitigation during execution\n"
        prompt += "6. Success metrics and KPIs\n"
        prompt += "7. Communication and governance structure\n"

        return prompt
