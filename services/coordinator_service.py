"""Coordinator Agent – orchestrates multiple agents and synthesizes outputs."""
import json
import logging
from typing import Any, Dict, Optional

from services.agent_service import AgentService
from services.risk_analysis_service import RiskAnalysisService
from services.recommendation_service import RecommendationService
from services.planning_service import PlanningService

logger = logging.getLogger(__name__)


class CoordinatorService:
    """Orchestrates all agents and synthesizes their outputs into a cohesive strategy."""

    def __init__(self):
        self.reconciliation_svc = AgentService()
        self.risk_svc = RiskAnalysisService()
        self.recommendation_svc = RecommendationService()
        self.planning_svc = PlanningService()

    async def run_full_analysis(
        self, infrastructure_data: Dict[str, Any], include_planning: bool = True
    ) -> Dict[str, Any]:
        """
        Run all agents in sequence: reconciliation → risk → recommendations → planning.

        Args:
            infrastructure_data: Asset inventory data.
            include_planning: Whether to run planning phase (slower).

        Returns:
            Comprehensive analysis with outputs from all agents.
        """
        logger.info("Starting full orchestrated analysis.")
        results = {"status": "in_progress", "phases": {}}

        try:
            # Phase 1: Reconciliation
            logger.info("Phase 1: Running reconciliation agent.")
            reconciliation_result = await self.reconciliation_svc.run_and_summarize(
                infrastructure_data
            )
            results["phases"]["reconciliation"] = reconciliation_result
            if reconciliation_result.get("status") != "success":
                results["status"] = "partial"
                return results

            # Phase 2: Risk Analysis
            logger.info("Phase 2: Running risk analysis agent.")
            risk_result = self.risk_svc.analyze_risks(infrastructure_data)
            results["phases"]["risk_analysis"] = risk_result
            risk_assessment = risk_result.get("risk_assessment", "")

            # Phase 3: Recommendations
            logger.info("Phase 3: Running recommendation agent.")
            rec_result = self.recommendation_svc.generate_recommendations(
                infrastructure_data, risk_assessment
            )
            results["phases"]["recommendations"] = rec_result
            recommendations = rec_result.get("recommendations", "")

            # Phase 4: Planning (optional, slower)
            if include_planning:
                logger.info("Phase 4: Running planning agent.")
                plan_result = self.planning_svc.create_execution_plan(
                    infrastructure_data, risk_assessment, recommendations
                )
                results["phases"]["execution_plan"] = plan_result

            # Synthesize summary
            results["status"] = "success"
            results["summary"] = self._synthesize_summary(results)

            logger.info("Full analysis completed successfully.")
            return results

        except Exception as e:
            logger.exception("Full analysis failed")
            results["status"] = "error"
            results["error"] = str(e)
            return results

    def _synthesize_summary(self, results: Dict[str, Any]) -> str:
        """Create a high-level executive summary from all agent outputs."""
        phases = results.get("phases", {})
        summary_lines = ["=== EXECUTIVE SUMMARY ===\n"]

        if "reconciliation" in phases:
            recon = phases["reconciliation"].get("summary", "")
            if recon:
                summary_lines.append(f"Reconciliation:\n{recon[:200]}...\n")

        if "risk_analysis" in phases:
            risk = phases["risk_analysis"].get("risk_assessment", "")
            if risk:
                summary_lines.append(f"Risk Assessment:\n{risk[:200]}...\n")

        if "recommendations" in phases:
            rec = phases["recommendations"].get("recommendations", "")
            if rec:
                summary_lines.append(f"Recommendations:\n{rec[:200]}...\n")

        if "execution_plan" in phases:
            plan = phases["execution_plan"].get("execution_plan", "")
            if plan:
                summary_lines.append(f"Execution Plan:\n{plan[:200]}...\n")

        return "".join(summary_lines)

    def get_agent_status(self) -> Dict[str, str]:
        """Return status of all agents."""
        return {
            "reconciliation": "active",
            "risk_analysis": "active",
            "recommendations": "active",
            "planning": "active",
            "coordinator": "active",
        }
