from typing import List, Dict, Any

class InvestigationService:
    @classmethod
    def analyze_patterns(cls, discrepancies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyzes the list of individual discrepancies to detect systematic patterns
        and adds structural warning findings.
        """
        findings = []
        
        # 1. Subnet clustering for untracked assets
        untracked_ips = []
        for disc in discrepancies:
            if disc["type"] == "untracked" and disc.get("ip_actual"):
                untracked_ips.append(disc["ip_actual"])
                
        subnets: Dict[str, int] = {}
        for ip in untracked_ips:
            parts = ip.split(".")
            if len(parts) == 4:
                subnet = f"{parts[0]}.{parts[1]}.{parts[2]}.x"
                subnets[subnet] = subnets.get(subnet, 0) + 1
                
        for subnet, count in subnets.items():
            if count >= 3:
                findings.append({
                    "pattern_type": "uninventoried_subnet",
                    "severity": "High" if "10.0.1" in subnet else "Medium",
                    "title": f"Potential Un-inventoried Subnet: {subnet}",
                    "description": f"Detected {count} untracked assets on the subnet '{subnet}'. This subnet may have been deployed without proper inventory syncing configurations."
                })
                
        # 2. OS drift analysis (newer OS deployed in environment but not recorded in CMDB)
        os_upgrade_count = 0
        for disc in discrepancies:
            if disc["type"] == "attribute_mismatch":
                details = disc.get("details", {})
                if "os" in details:
                    os_upgrade_count += 1
                    
        if os_upgrade_count >= 3:
            findings.append({
                "pattern_type": "systematic_os_drift",
                "severity": "Medium",
                "title": "Systematic OS Version Drift",
                "description": f"Detected {os_upgrade_count} systems where the installed Operating System version on Actual does not match the CMDB records. This suggest an OS upgrade cycle occurred without registering updates in CMDB."
            })
            
        # 3. Domain suffix drifts (e.g. server1 vs server1.company.corp)
        suffix_drift_count = 0
        for disc in discrepancies:
            if disc["type"] == "naming_mismatch":
                h_cmdb = disc.get("hostname_cmdb") or ""
                h_actual = disc.get("hostname_actual") or ""
                if h_cmdb and h_actual:
                    # check if base hostname is identical
                    base_cmdb = h_cmdb.split(".")[0]
                    base_actual = h_actual.split(".")[0]
                    if base_cmdb == base_actual:
                        suffix_drift_count += 1
                        
        if suffix_drift_count >= 2:
            findings.append({
                "pattern_type": "domain_suffix_drift",
                "severity": "Low",
                "title": "Systematic Domain Suffix Mismatches",
                "description": f"Detected {suffix_drift_count} servers matching on base hostname but differing in domain suffix. Review naming schemas in CMDB and local server domain configuration."
            })

        # 4. Resource upgrade drift (actual hardware resources > CMDB resources)
        resource_drift_up_count = 0
        for disc in discrepancies:
            if disc["type"] == "attribute_mismatch":
                details = disc.get("details", {})
                for attr in ("ram_gb", "cpu"):
                    if attr in details:
                        cmdb_v = details[attr].get("cmdb")
                        act_v = details[attr].get("actual")
                        if cmdb_v is not None and act_v is not None and act_v > cmdb_v:
                            resource_drift_up_count += 1
                            
        if resource_drift_up_count >= 3:
            findings.append({
                "pattern_type": "resource_capacity_drift",
                "severity": "Medium",
                "title": "Systematic Hardware Capacity Drift",
                "description": f"Detected {resource_drift_up_count} instances where actual server hardware capacity (CPU/RAM) exceeds CMDB records. Resource scaling is occurring without configuration updates."
            })

        return findings
