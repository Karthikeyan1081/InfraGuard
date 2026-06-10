import uuid
from typing import List, Dict, Any, Tuple
from services.normalization_service import NormalizedAsset

class ReconciliationService:
    @classmethod
    def detect_duplicates(cls, assets: List[NormalizedAsset], source: str) -> List[Dict[str, Any]]:
        """
        Finds duplicates within a single inventory list.
        Checks for duplicate external_ids, ip_addresses, and hostnames.
        """
        duplicates = []
        
        # Track IDs, IPs, Hostnames seen so far
        ids: Dict[str, List[NormalizedAsset]] = {}
        ips: Dict[str, List[NormalizedAsset]] = {}
        hosts: Dict[str, List[NormalizedAsset]] = {}
        
        for asset in assets:
            if asset.external_id:
                ids.setdefault(asset.external_id, []).append(asset)
            if asset.ip_address:
                ips.setdefault(asset.ip_address, []).append(asset)
            if asset.hostname:
                hosts.setdefault(asset.hostname, []).append(asset)
                
        # Helper to generate duplicate discrepancy dicts
        def add_dup_records(grouped_dict: Dict[str, List[NormalizedAsset]], field_name: str):
            for value, items in grouped_dict.items():
                if len(items) > 1:
                    item_details = [
                        f"[ID: {i.external_id or 'N/A'}, Host: {i.hostname or 'N/A'}, IP: {i.ip_address or 'N/A'}]"
                        for i in items
                    ]
                    duplicates.append({
                        "id": f"dup-{source}-{field_name}-{uuid.uuid4().hex[:8]}",
                        "type": "duplicate",
                        "description": f"Duplicate entries ({len(items)}) detected for {field_name} '{value}' in {source.upper()} data.",
                        "external_id": items[0].external_id,
                        "hostname_cmdb": items[0].hostname if source == "cmdb" else None,
                        "hostname_actual": items[0].hostname if source == "actual" else None,
                        "ip_cmdb": items[0].ip_address if source == "cmdb" else None,
                        "ip_actual": items[0].ip_address if source == "actual" else None,
                        "details": {
                            "source": source,
                            "duplicate_field": field_name,
                            "duplicate_value": value,
                            "occurrences": item_details
                        }
                    })

        add_dup_records(ids, "external_id")
        add_dup_records(ips, "ip_address")
        add_dup_records(hosts, "hostname")
        
        return duplicates

    @classmethod
    def reconcile(
        cls, 
        cmdb_assets: List[NormalizedAsset], 
        actual_assets: List[NormalizedAsset]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Reconciles expected (CMDB) against actual infrastructure.
        Returns:
            - matched_pairs: List of dicts with CMDB and Actual matching asset data.
            - discrepancies: List of detailed discrepancy dictionary records.
        """
        discrepancies = []
        matched_pairs = []
        
        # 1. Run duplicate checks on both sources
        cmdb_dups = cls.detect_duplicates(cmdb_assets, "cmdb")
        actual_dups = cls.detect_duplicates(actual_assets, "actual")
        discrepancies.extend(cmdb_dups)
        discrepancies.extend(actual_dups)
        
        # Build indexes of Actual assets for fast lookup
        actual_by_id = {a.external_id: a for a in actual_assets if a.external_id}
        actual_by_ip = {a.ip_address: a for a in actual_assets if a.ip_address}
        actual_by_host = {a.hostname: a for a in actual_assets if a.hostname}
        
        matched_actual_ids = set()
        
        # Iterate and match CMDB assets
        for cmdb in cmdb_assets:
            matched_actual: NormalizedAsset = None
            match_method = None
            
            # Step A: Match by external ID
            if cmdb.external_id and cmdb.external_id in actual_by_id:
                matched_actual = actual_by_id[cmdb.external_id]
                match_method = "external_id"
            # Step B: Match by IP address
            elif cmdb.ip_address and cmdb.ip_address in actual_by_ip:
                matched_actual = actual_by_ip[cmdb.ip_address]
                match_method = "ip_address"
            # Step C: Match by Hostname
            elif cmdb.hostname and cmdb.hostname in actual_by_host:
                matched_actual = actual_by_host[cmdb.hostname]
                match_method = "hostname"
                
            if matched_actual:
                # Track that this actual asset has been successfully matched
                matched_actual_ids.add(id(matched_actual))
                matched_pairs.append({"cmdb": cmdb, "actual": matched_actual})
                
                # Check for Naming Mismatch
                if cmdb.hostname != matched_actual.hostname:
                    discrepancies.append({
                        "id": f"disc-nm-{uuid.uuid4().hex[:8]}",
                        "type": "naming_mismatch",
                        "description": f"Hostname mismatch. CMDB: '{cmdb.hostname or 'N/A'}', Actual: '{matched_actual.hostname or 'N/A'}'",
                        "external_id": cmdb.external_id or matched_actual.external_id,
                        "hostname_cmdb": cmdb.hostname,
                        "hostname_actual": matched_actual.hostname,
                        "ip_cmdb": cmdb.ip_address,
                        "ip_actual": matched_actual.ip_address,
                        "details": {
                            "match_method": match_method,
                            "cmdb_hostname": cmdb.hostname,
                            "actual_hostname": matched_actual.hostname
                        }
                    })
                    
                # Check for Attribute/Resource Mismatch
                attrs_to_check = [
                    ("cpu", "CPU Cores"),
                    ("ram_gb", "RAM (GB)"),
                    ("os", "Operating System"),
                    ("status", "Status")
                ]
                mismatched_attrs = {}
                for attr, label in attrs_to_check:
                    cmdb_val = getattr(cmdb, attr)
                    act_val = getattr(matched_actual, attr)
                    if cmdb_val != act_val:
                        mismatched_attrs[attr] = {"cmdb": cmdb_val, "actual": act_val, "label": label}
                        
                if mismatched_attrs:
                    desc_parts = [
                        f"{info['label']} differs (CMDB: {info['cmdb']}, Actual: {info['actual']})"
                        for info in mismatched_attrs.values()
                    ]
                    discrepancies.append({
                        "id": f"disc-am-{uuid.uuid4().hex[:8]}",
                        "type": "attribute_mismatch",
                        "description": f"Attribute mismatch: {'; '.join(desc_parts)}",
                        "external_id": cmdb.external_id or matched_actual.external_id,
                        "hostname_cmdb": cmdb.hostname,
                        "hostname_actual": matched_actual.hostname,
                        "ip_cmdb": cmdb.ip_address,
                        "ip_actual": matched_actual.ip_address,
                        "details": mismatched_attrs
                    })
            else:
                # CMDB Asset is missing from Actual Scan
                discrepancies.append({
                    "id": f"disc-ms-{uuid.uuid4().hex[:8]}",
                    "type": "missing",
                    "description": f"Asset '{cmdb.hostname or cmdb.external_id or cmdb.ip_address}' registered in CMDB is missing from the actual environment scan.",
                    "external_id": cmdb.external_id,
                    "hostname_cmdb": cmdb.hostname,
                    "hostname_actual": None,
                    "ip_cmdb": cmdb.ip_address,
                    "ip_actual": None,
                    "details": {
                        "expected_cpu": cmdb.cpu,
                        "expected_ram_gb": cmdb.ram_gb,
                        "expected_os": cmdb.os,
                        "expected_status": cmdb.status
                    }
                })
                
        # 3. Find Untracked Actual Assets (actual assets not matched to any CMDB asset)
        for act in actual_assets:
            if id(act) not in matched_actual_ids:
                discrepancies.append({
                    "id": f"disc-ut-{uuid.uuid4().hex[:8]}",
                    "type": "untracked",
                    "description": f"Untracked asset '{act.hostname or act.external_id or act.ip_address}' detected in actual environment but missing from CMDB.",
                    "external_id": act.external_id,
                    "hostname_cmdb": None,
                    "hostname_actual": act.hostname,
                    "ip_cmdb": None,
                    "ip_actual": act.ip_address,
                    "details": {
                        "actual_cpu": act.cpu,
                        "actual_ram_gb": act.ram_gb,
                        "actual_os": act.os,
                        "actual_status": act.status
                    }
                })
                
        return matched_pairs, discrepancies
