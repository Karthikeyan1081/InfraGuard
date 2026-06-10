import os
import json
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data_samples")

def create_samples():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 1. Create CMDB Inventory CSV
    cmdb_path = os.path.join(DATA_DIR, "cmdb_inventory.csv")
    cmdb_headers = ["id", "hostname", "ip_address", "cpu", "ram_gb", "os", "status"]
    
    cmdb_rows = [
        ["SRV-001", "db-prod-01", "10.0.1.10", "8", "32", "Ubuntu 22.04 LTS", "Active"],
        ["SRV-002", "web-prod-01", "10.0.1.11", "4", "16", "Ubuntu 22.04", "Active"],
        ["SRV-003", "app-dev-01", "10.0.2.15", "2", "8", "CentOS 7", "Active"],
        ["SRV-004", "cache-prod-01", "10.0.1.12", "4", "8", "Ubuntu 20.04", "Active"],
        ["SRV-005", "mail-server", "10.0.1.13", "4", "16", "Windows Server 2019 Standard", "Inactive"],
        ["SRV-006", "test-vm-01", "10.0.3.5", "2", "4", "Ubuntu 22.04", "Active"],
        ["SRV-007", "db-replica-01", "10.0.1.20", "8", "32", "Ubuntu 22.04", "Active"],
        ["SRV-008", "gateway-prod", "10.0.1.1", "2", "4", "CentOS Linux 7 (Core)", "Active"],
        ["SRV-009", "auth-dev", "10.0.2.20", "2", "4", "CentOS Linux 7", "Active"],
        # Duplicate row in CMDB
        ["SRV-009", "auth-dev", "10.0.2.20", "2", "4", "CentOS Linux 7", "Active"],
    ]
    
    with open(cmdb_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cmdb_headers)
        writer.writerows(cmdb_rows)
        
    print(f"Generated sample CMDB inventory CSV: {cmdb_path}")

    # 2. Create Actual Infrastructure Scan JSON
    # Drift introduction details:
    # - SRV-001 matches perfectly.
    # - SRV-002 hostname is actual: web-prod-01.local (Naming mismatch)
    # - SRV-003 RAM actual: 16384 MB (16 GB) vs CMDB: 8 GB, CPU: 4 vs CMDB: 2 (Attribute mismatch)
    # - SRV-004 cache-prod-01 is missing (Missing)
    # - SRV-005 mail-server status actual: Active vs CMDB: Inactive (Status mismatch - high risk)
    # - SRV-006 test-vm-01 status actual: Inactive vs CMDB: Active (Status mismatch)
    # - SRV-007 RAM actual: 65536 MB (64 GB) vs CMDB: 32 GB (Resource drift)
    # - SRV-008 OS actual: CentOS 8 vs CMDB: CentOS 7 (OS drift)
    # - SRV-009 OS actual: CentOS 8 vs CMDB: CentOS 7 (OS drift)
    # - Untracked subnet 10.0.3.x cluster:
    #   - SRV-020 (untracked-01, 10.0.3.10)
    #   - SRV-021 (untracked-02, 10.0.3.11)
    #   - SRV-022 (untracked-03, 10.0.3.12)
    
    actual_data = [
        {
            "id": "SRV-001",
            "hostname": "db-prod-01",
            "ip_address": " 10.0.1.10 ", # Trailing space to check normalization
            "cpu": 8,
            "ram": 32,
            "os": "Ubuntu 22.04.2 LTS",
            "status": "Active"
        },
        {
            "id": "SRV-002",
            "hostname": "web-prod-01.local", # Hostname drift
            "ip_address": "10.0.1.11",
            "cpu": 4,
            "ram": 16,
            "os": "Ubuntu 22.04 LTS",
            "status": "Active"
        },
        {
            "id": "SRV-003",
            "hostname": "app-dev-01",
            "ip_address": "10.0.2.15",
            "cpu": 4, # Specs upgrade drift
            "ram_size": 16384, # RAM in MB (16384 MB = 16 GB)
            "os": "CentOS Linux release 7.9.2009",
            "status": "Active"
        },
        # SRV-004 is missing
        {
            "id": "SRV-005",
            "hostname": "mail-server",
            "ip_address": "10.0.1.13",
            "cpu": 4,
            "ram": 16,
            "os": "Windows Server 2019 Standard",
            "status": "Active" # Status active mismatch (CMDB has Inactive)
        },
        {
            "id": "SRV-006",
            "hostname": "test-vm-01",
            "ip_address": "10.0.3.5",
            "cpu": 2,
            "ram": 4,
            "os": "Ubuntu 22.04",
            "status": "Inactive" # Status mismatch (CMDB has Active)
        },
        {
            "id": "SRV-007",
            "hostname": "db-replica-01",
            "ip_address": "10.0.1.20",
            "cpu": 8,
            "ram": 65536, # RAM upgrade (64 GB)
            "os": "Ubuntu 22.04",
            "status": "Active"
        },
        {
            "id": "SRV-008",
            "hostname": "gateway-prod",
            "ip_address": "10.0.1.1",
            "cpu": 2,
            "ram": 4,
            "os": "CentOS Linux release 8.2.2004", # OS drift (CentOS 8)
            "status": "Active"
        },
        {
            "id": "SRV-009",
            "hostname": "auth-dev",
            "ip_address": "10.0.2.20",
            "cpu": 2,
            "ram": 4,
            "os": "CentOS Linux release 8.2.2004", # OS drift (CentOS 8)
            "status": "Active"
        },
        # Untracked servers in 10.0.3.x subnet
        {
            "id": "SRV-020",
            "hostname": "untracked-srv-01",
            "ip_address": "10.0.3.10",
            "cpu": 4,
            "ram": 8,
            "os": "Ubuntu 22.04 LTS",
            "status": "Active"
        },
        {
            "id": "SRV-021",
            "hostname": "untracked-srv-02",
            "ip_address": "10.0.3.11",
            "cpu": 2,
            "ram": 4,
            "os": "Ubuntu 22.04",
            "status": "Active"
        },
        {
            "id": "SRV-022",
            "hostname": "untracked-srv-03",
            "ip_address": "10.0.3.12",
            "cpu": 2,
            "ram": 4,
            "os": "Ubuntu 22.04",
            "status": "Active"
        }
    ]
    
    actual_path = os.path.join(DATA_DIR, "actual_infrastructure.json")
    with open(actual_path, "w", encoding="utf-8") as f:
        json.dump(actual_data, f, indent=2)
        
    print(f"Generated sample actual inventory JSON: {actual_path}")

if __name__ == "__main__":
    create_samples()
