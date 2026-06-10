"""Risk Analysis Agent – identifies high-risk assets and compliance issues."""
import json
import logging
from typing import Any, Dict, List, Optional

from services.agent_llm import AgentLLM

logger = logging.getLogger(__name__)


class RiskAnalysisService:
    """Analyzes uploaded infrastructure for compliance, security, and operational risks."""

    def __init__(self, llm: Optional[AgentLLM] = None):
        self.llm = llm or AgentLLM()

    def analyze_risks(self, infrastructure_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze infrastructure for risks.

        Args:
            infrastructure_data: Asset inventory or reconciliation results.

        Returns:
            Risk assessment with categories, scores, and recommendations.
        """
        logger.info("Starting risk analysis.")
        try:
            assets = infrastructure_data.get("assets", [])
            mismatches = infrastructure_data.get("mismatches", [])

            # Build risk summary
            risk_prompt = self._build_risk_prompt(assets, mismatches)
            risk_assessment = self.llm.summarize(risk_prompt)

            return {
                "status": "success",
                "risk_assessment": risk_assessment,
                "asset_count": len(assets),
                "mismatch_count": len(mismatches),
            }
        except Exception as e:
            logger.exception("Risk analysis failed")
            return {"status": "error", "error": str(e)}

    def _build_risk_prompt(self, assets: List[Dict], mismatches: List[Dict]) -> str:
        """Build prompt for risk analysis."""
        prompt = "Analyze the following infrastructure for compliance, security, and operational risks:\n\n"
        prompt += f"Total Assets: {len(assets)}\n"
        prompt += f"Known Mismatches: {len(mismatches)}\n\n"

        if mismatches:
            prompt += "Reconciliation Mismatches (high-risk indicators):\n"
            for mismatch in mismatches[:5]:
                prompt += f"  - {mismatch.get('asset_id', 'N/A')}: {mismatch.get('reason', 'unknown')}\n"

        prompt += "\nProvide a risk assessment with:\n"
        prompt += "1. Critical risks (must address immediately)\n"
        prompt += "2. High risks (address within 30 days)\n"
        prompt += "3. Medium risks (address within 90 days)\n"
        prompt += "4. Compliance gaps\n"
        prompt += "5. Remediation priority list\n"

        return prompt
