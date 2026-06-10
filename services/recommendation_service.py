"""Recommendation Agent – generates actionable remediation strategies."""
import json
import logging
from typing import Any, Dict, List, Optional

from services.agent_llm import AgentLLM

logger = logging.getLogger(__name__)


class RecommendationService:
    """Generates remediation strategies and optimization recommendations."""

    def __init__(self, llm: Optional[AgentLLM] = None):
        self.llm = llm or AgentLLM()

    def generate_recommendations(
        self,
        infrastructure_data: Dict[str, Any],
        risk_assessment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate actionable recommendations based on infrastructure and risks.

        Args:
            infrastructure_data: Asset inventory or reconciliation results.
            risk_assessment: Optional risk assessment output to factor into recommendations.

        Returns:
            Structured recommendations with actions, timeline, and effort estimates.
        """
        logger.info("Generating recommendations.")
        try:
            assets = infrastructure_data.get("assets", [])
            mismatches = infrastructure_data.get("mismatches", [])

            recommendation_prompt = self._build_recommendation_prompt(
                assets, mismatches, risk_assessment
            )
            recommendations = self.llm.summarize(recommendation_prompt)

            return {
                "status": "success",
                "recommendations": recommendations,
                "asset_count": len(assets),
                "mismatch_count": len(mismatches),
            }
        except Exception as e:
            logger.exception("Recommendation generation failed")
            return {"status": "error", "error": str(e)}

    def _build_recommendation_prompt(
        self, assets: List[Dict], mismatches: List[Dict], risk_assessment: Optional[str]
    ) -> str:
        """Build prompt for recommendation generation."""
        prompt = "Based on the infrastructure analysis, generate prioritized remediation recommendations:\n\n"
        prompt += f"Total Assets: {len(assets)}\n"
        prompt += f"Reconciliation Mismatches: {len(mismatches)}\n\n"

        if risk_assessment:
            prompt += f"Risk Assessment Context:\n{risk_assessment}\n\n"

        if mismatches:
            prompt += "Top Mismatches to Address:\n"
            for mismatch in mismatches[:5]:
                prompt += f"  - {mismatch.get('asset_id', 'N/A')}: {mismatch.get('reason', 'unknown')}\n"

        prompt += "\nProvide recommendations with:\n"
        prompt += "1. Immediate actions (next 7 days)\n"
        prompt += "2. Short-term fixes (next 30 days)\n"
        prompt += "3. Medium-term improvements (60-90 days)\n"
        prompt += "4. Long-term strategy (90+ days)\n"
        prompt += "5. Effort estimates (hours/days) for each action\n"
        prompt += "6. Expected outcomes and benefits\n"

        return prompt

    @classmethod
    def generate_recommendation(cls, discrepancy: Dict[str, Any]) -> str:
        """
        Generates actionable technical remediation steps for a given discrepancy.
        """
        disc_type = discrepancy["type"]
        details = discrepancy.get("details", {})
        
        hostname_cmdb = discrepancy.get("hostname_cmdb")
        hostname_actual = discrepancy.get("hostname_actual")
        
        if disc_type == "missing":
            expected_status = details.get("expected_status", "Active")
            name = hostname_cmdb or discrepancy.get("external_id") or "unnamed"
            if expected_status == "Active":
                return (
                    f"Asset '{name}' is active in CMDB but was not found in the infrastructure scan. "
                    "Remediation: 1) Verify physical/virtual power state. 2) Confirm host agent health and "
                    "firewall network permissions. 3) If retired, update CMDB status to 'Inactive'."
                )
            else:
                return (
                    f"Asset '{name}' is marked as Inactive in CMDB and is missing from actual scans. "
                    "Remediation: Confirm that decommissioning is complete. No further action is required."
                )

        elif disc_type == "untracked":
            name = hostname_actual or discrepancy.get("external_id") or discrepancy.get("ip_actual") or "unnamed"
            ip = discrepancy.get("ip_actual") or "unknown IP"
            return (
                f"Untracked active host '{name}' ({ip}) detected in environment but not registered in CMDB. "
                "Remediation: 1) Identify server owner and business application. 2) Register this server "
                "in CMDB with correct subnet, CPU, RAM, and OS metadata. 3) Enforce deployment inventory policies."
            )

        elif disc_type == "naming_mismatch":
            h_cmdb = hostname_cmdb or "N/A"
            h_actual = hostname_actual or "N/A"
            return (
                f"Hostname discrepancy: CMDB records name '{h_cmdb}' but actual host reports '{h_actual}'. "
                "Remediation: Update CMDB record to match the active host name, or rename the server to follow standard "
                "enterprise inventory conventions. Update local DNS pointer records if required."
            )

        elif disc_type == "attribute_mismatch":
            remediations = []
            
            # Status mismatches
            if "status" in details:
                cmdb_s = details["status"].get("cmdb")
                act_s = details["status"].get("actual")
                if cmdb_s == "Active" and act_s == "Inactive":
                    remediations.append(
                        "System is offline or stopped but marked as Active in CMDB. Verify if decommissioning occurred or "
                        "if server suffered an unplanned crash. Update CMDB to match."
                    )
                elif cmdb_s == "Inactive" and act_s == "Active":
                    remediations.append(
                        "CRITICAL: System is active in infrastructure but marked Inactive/Retired in CMDB. "
                        "Re-enable inventory billing and update status to Active immediately."
                    )
                else:
                    remediations.append(
                        f"Status mismatch (CMDB: {cmdb_s}, Actual: {act_s}). Sync status attributes."
                    )
                    
            # Resource mismatches (RAM/CPU/OS)
            resource_mismatch = False
            r_details = []
            for attr in ("cpu", "ram_gb", "os"):
                if attr in details:
                    resource_mismatch = True
                    label = "CPU Cores" if attr == "cpu" else "RAM GB" if attr == "ram_gb" else "Operating System"
                    r_details.append(f"{label} (CMDB: {details[attr].get('cmdb')}, Actual: {details[attr].get('actual')})")
                    
            if resource_mismatch:
                remediations.append(
                    f"Specs drift detected: {', '.join(r_details)}. Action: Update CMDB specs to reflect "
                    "actual virtual machine hypervisor allocations, or verify if unauthorized hardware resize was performed."
                )
                
            return " | ".join(remediations) if remediations else "Investigate resource configuration drift."

        elif disc_type == "duplicate":
            field = details.get("duplicate_field", "identifier")
            val = details.get("duplicate_value", "unknown")
            src = details.get("source", "unknown").upper()
            return (
                f"Duplicate record detected on {field} '{val}' in {src} source file. "
                "Remediation: Consolidate asset records. Purge redundant rows from the data ingestion source."
            )

        return "Verify asset configurations and update inventory database."
