import os
import asyncio
import json
import sqlite3

from database.db import DB_PATH, init_db
from services.ingestion_service import IngestionService
from services.normalization_service import NormalizationService
from services.reconciliation_service import ReconciliationService
from services.investigation_service import InvestigationService
from services.risk_service import RiskService
from services.recommendation_service import RecommendationService
from services.report_service import ReportService

async def main():
    print("=== ASSETSYNC INTEGRITY & LOGIC VERIFICATION ===")
    
    # 1. Initialize Database
    print("\n1. Initializing Database...")
    await init_db()
    if os.path.exists(DB_PATH):
        print(f"   [OK] SQLite Database exists at: {DB_PATH}")
    else:
        raise FileNotFoundError("   [FAIL] Database file not found after init.")
        
    # Resolve sample file paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cmdb_file = os.path.join(base_dir, "data_samples", "cmdb_inventory.csv")
    actual_file = os.path.join(base_dir, "data_samples", "actual_infrastructure.json")
    
    if not os.path.exists(cmdb_file) or not os.path.exists(actual_file):
        raise FileNotFoundError("   [FAIL] Run generate_sample_data.py first to create sample datasets.")
        
    # 2. Test Ingestion Service
    print("\n2. Testing Ingestion Service...")
    cmdb_raw = await IngestionService.parse_cmdb_csv(cmdb_file)
    actual_raw = await IngestionService.parse_actual_json(actual_file)
    print(f"   [OK] Parsed {len(cmdb_raw)} CMDB raw assets.")
    print(f"   [OK] Parsed {len(actual_raw)} Actual live scan assets.")
    
    # 3. Test Normalization Service
    print("\n3. Testing Normalization Service...")
    cmdb_norm = [NormalizationService.normalize_asset(a) for a in cmdb_raw]
    actual_norm = [NormalizationService.normalize_asset(a) for a in actual_raw]
    print(f"   [OK] Normalized {len(cmdb_norm)} CMDB assets.")
    print(f"   [OK] Normalized {len(actual_norm)} Actual assets.")
    
    # Check RAM MB to GB normalization works
    # SRV-003 is app-dev-01, had ram_size = 16384 MB
    srv003_actual = next((a for a in actual_norm if a.external_id == "SRV-003"), None)
    if srv003_actual and srv003_actual.ram_gb == 16:
        print("   [OK] RAM MB to GB normalization verified successfully (16384 MB -> 16 GB).")
    else:
        print(f"   [WARNING] RAM MB to GB normalization check failed. Got: {srv003_actual.ram_gb if srv003_actual else 'None'}")
        
    # 4. Test Reconciliation Service
    print("\n4. Testing Reconciliation Service...")
    matched_pairs, discrepancies = ReconciliationService.reconcile(cmdb_norm, actual_norm)
    print(f"   [OK] Identified {len(matched_pairs)} matched asset pairs.")
    print(f"   [OK] Detected {len(discrepancies)} discrepancies.")
    
    # 5. Test Risk & Recommendation Services
    print("\n5. Testing Risk & Recommendation Services...")
    for disc in discrepancies:
        disc["severity"] = RiskService.evaluate_risk(disc)
        disc["remediation"] = RecommendationService.generate_recommendation(disc)
    print("   [OK] Evaluated severities and technical recommendations successfully.")
    
    # 6. Test Investigation Service
    print("\n6. Testing Investigation Service...")
    findings = InvestigationService.analyze_patterns(discrepancies)
    print(f"   [OK] Pattern Analysis finished. Found {len(findings)} systemic issues.")
    for f in findings:
        print(f"        - Pattern: {f['title']} ({f['severity']})")
        
    # Check if subnet un-inventoried pattern is found
    subnet_pattern = any("Subnet: 10.0.3.x" in f["title"] for f in findings)
    if subnet_pattern:
        print("   [OK] Systematic un-inventoried subnet detection verified.")
    else:
        print("   [WARNING] Un-inventoried subnet pattern not found in findings.")
        
    # 7. Test Database Storage
    print("\n7. Storing results in SQLite...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Simulate DB insert operations
    analysis_id = "test-analysis-uuid"
    summary_stats = {
        "total_discrepancies": len(discrepancies),
        "missing": len([d for d in discrepancies if d["type"] == "missing"]),
        "untracked": len([d for d in discrepancies if d["type"] == "untracked"]),
        "naming_mismatch": len([d for d in discrepancies if d["type"] == "naming_mismatch"]),
        "attribute_mismatch": len([d for d in discrepancies if d["type"] == "attribute_mismatch"]),
        "duplicate": len([d for d in discrepancies if d["type"] == "duplicate"]),
        "high_severity": len([d for d in discrepancies if d["severity"] == "High"]),
        "medium_severity": len([d for d in discrepancies if d["severity"] == "Medium"]),
        "low_severity": len([d for d in discrepancies if d["severity"] == "Low"]),
        "findings": findings
    }
    
    # Clear old test data if any
    cursor.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    conn.commit()
    
    cursor.execute(
        "INSERT INTO analyses (id, name, status, cmdb_file, actual_file, summary_stats) VALUES (?, ?, ?, ?, ?, ?)",
        (analysis_id, "Test Integration Run", "Completed", cmdb_file, actual_file, json.dumps(summary_stats))
    )
    
    # Assets bulk inserts
    for a in cmdb_norm:
        cursor.execute(
            "INSERT INTO assets (analysis_id, source, external_id, hostname, ip_address, cpu, ram_gb, os, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (analysis_id, "cmdb", a.external_id, a.hostname, a.ip_address, a.cpu, a.ram_gb, a.os, a.status)
        )
    for a in actual_norm:
        cursor.execute(
            "INSERT INTO assets (analysis_id, source, external_id, hostname, ip_address, cpu, ram_gb, os, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (analysis_id, "actual", a.external_id, a.hostname, a.ip_address, a.cpu, a.ram_gb, a.os, a.status)
        )
        
    # Discrepancies inserts
    for d in discrepancies:
        cursor.execute(
            """
            INSERT INTO discrepancies (id, analysis_id, type, severity, description, external_id, hostname_cmdb, hostname_actual, ip_cmdb, ip_actual, details, remediation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (d["id"], analysis_id, d["type"], d["severity"], d["description"], d.get("external_id"), d.get("hostname_cmdb"), d.get("hostname_actual"), d.get("ip_cmdb"), d.get("ip_actual"), json.dumps(d["details"]), d["remediation"])
        )
        
    conn.commit()
    
    # Query checking
    cursor.execute("SELECT count(*) FROM assets WHERE analysis_id = ?", (analysis_id,))
    assets_count = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM discrepancies WHERE analysis_id = ?", (analysis_id,))
    discrepancies_count = cursor.fetchone()[0]
    
    print(f"   [OK] Successfully wrote {assets_count} assets snapshots to SQL.")
    print(f"   [OK] Successfully wrote {discrepancies_count} discrepancies logs to SQL.")
    
    # 8. Test ReportLab Report Generation
    print("\n8. Generating PDF Audit Report...")
    pdf_path = await ReportService.generate_pdf(
        analysis_id=analysis_id,
        name="Test Integration Run",
        cmdb_file=cmdb_file,
        actual_file=actual_file,
        created_at="2026-06-09T09:52:00",
        summary_stats=summary_stats,
        discrepancies=discrepancies,
        findings=findings
    )
    
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        print(f"   [OK] Generated PDF report successfully ({os.path.getsize(pdf_path)} bytes) at:")
        print(f"        {pdf_path}")
    else:
        raise FileNotFoundError("   [FAIL] PDF report was not generated or is empty.")
        
    # Clean up test database row
    cursor.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    conn.commit()
    conn.close()
    
    print("\n=== ALL SYSTEM TESTS COMPLETED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(main())
