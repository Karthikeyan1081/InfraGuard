from typing import Dict, Any

class RiskService:
    @staticmethod
    def is_production(hostname: str, ip_address: str) -> bool:
        """
        Helper checking if host or IP points to a production environment.
        - Hostname includes keywords like 'prod', 'db', 'sql', 'replica', 'mail', 'gateway'.
        - IP belongs to 10.0.1.x segment (prod subnet).
        """
        host_lower = (hostname or "").lower()
        ip_str = ip_address or ""
        
        # Rule 1: Hostname checks
        prod_keywords = {"prod", "db", "sql", "replica", "mail", "gateway", "ldap", "auth"}
        for key in prod_keywords:
            if key in host_lower:
                return True
                
        # Rule 2: IP subnet checks (production subnet: 10.0.1.x)
        if ip_str.startswith("10.0.1."):
            return True
            
        return False

    @classmethod
    def evaluate_risk(cls, discrepancy: Dict[str, Any]) -> str:
        """
        Evaluates discrepancy type, metadata, and asset characteristics to assign
        severity ('High', 'Medium', 'Low').
        """
        disc_type = discrepancy["type"]
        details = discrepancy.get("details", {})
        
        # Resolve name and IP to check if it's a prod target
        hostname = discrepancy.get("hostname_cmdb") or discrepancy.get("hostname_actual") or ""
        ip_addr = discrepancy.get("ip_cmdb") or discrepancy.get("ip_actual") or ""
        is_prod = cls.is_production(hostname, ip_addr)

        if disc_type == "missing":
            expected_status = details.get("expected_status", "Active")
            expected_ram = details.get("expected_ram_gb", 0) or 0
            expected_cpu = details.get("expected_cpu", 0) or 0
            
            # Scenario A: Inactive asset in CMDB is missing -> Low
            if expected_status == "Inactive":
                return "Low"
            # Scenario B: Active Production server missing -> High
            if is_prod or expected_ram >= 16 or expected_cpu >= 8:
                return "High"
            # Scenario C: Active Dev/Test server missing -> Medium
            return "Medium"

        elif disc_type == "untracked":
            actual_ram = details.get("actual_ram_gb", 0) or 0
            # Scenario A: Untracked asset in production subnet/name or large hardware -> Medium
            if is_prod or actual_ram >= 16:
                return "Medium"
            # Scenario B: Dev subnet untracked asset -> Low
            return "Low"

        elif disc_type == "naming_mismatch":
            # Scenario A: Naming standards broken on Production node -> Medium
            if is_prod:
                return "Medium"
            # Scenario B: Dev node naming mismatch -> Low
            return "Low"

        elif disc_type == "attribute_mismatch":
            # Check for Status mismatches
            if "status" in details:
                cmdb_status = details["status"].get("cmdb")
                actual_status = details["status"].get("actual")
                
                # Active in CMDB but Inactive in reality on production server -> High
                if cmdb_status == "Active" and actual_status == "Inactive":
                    return "High" if is_prod else "Medium"
                    
            # Resource drifts (CPU/RAM/OS)
            if is_prod:
                return "Medium"
            return "Low"

        elif disc_type == "duplicate":
            return "Low"

        return "Low"
