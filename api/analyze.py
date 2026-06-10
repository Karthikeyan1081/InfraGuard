import os
import json
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import aiosqlite

from database.db import get_db
from services.ingestion_service import IngestionService
from services.normalization_service import NormalizationService
from services.reconciliation_service import ReconciliationService
from services.investigation_service import InvestigationService
from services.risk_service import RiskService
from services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api", tags=["Analysis"])

class AnalyzeRequest(BaseModel):
    name: str
    cmdb_file_path: str
    actual_file_path: str

class AnalysisSummary(BaseModel):
    id: str
    name: str
    status: str
    cmdb_file: str
    actual_file: str
    created_at: str
    summary_stats: Dict[str, Any]

class DiscrepancyResponse(BaseModel):
    id: str
    type: str
    severity: str
    description: str
    external_id: Optional[str]
    hostname_cmdb: Optional[str]
    hostname_actual: Optional[str]
    ip_cmdb: Optional[str]
    ip_actual: Optional[str]
    details: Dict[str, Any]
    remediation: str

class AnalysisDetailResponse(BaseModel):
    id: str
    name: str
    status: str
    cmdb_file: str
    actual_file: str
    created_at: str
    summary_stats: Dict[str, Any]
    discrepancies: List[DiscrepancyResponse]

@router.post("/analyze", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def analyze_reconciliation(
    req: AnalyzeRequest,
    db: aiosqlite.Connection = Depends(get_db)
):
    """
    Triggers inventory reconciliation between the specified CMDB CSV and Actual JSON files.
    Calculates discrepancies, risks, remediation guides, groups them into patterns, and commits to DB.
    """
    # 1. Verify files exist
    if not os.path.exists(req.cmdb_file_path):
        raise HTTPException(status_code=400, detail=f"CMDB file not found: {req.cmdb_file_path}")
    if not os.path.exists(req.actual_file_path):
        raise HTTPException(status_code=400, detail=f"Actual inventory file not found: {req.actual_file_path}")
        
    try:
        # 2. Ingest
        cmdb_raw = await IngestionService.parse_cmdb_csv(req.cmdb_file_path)
        actual_raw = await IngestionService.parse_actual_json(req.actual_file_path)
        
        # 3. Normalize
        cmdb_norm = [NormalizationService.normalize_asset(a) for a in cmdb_raw]
        actual_norm = [NormalizationService.normalize_asset(a) for a in actual_raw]
        
        # 4. Compare
        matched_pairs, discrepancies = ReconciliationService.reconcile(cmdb_norm, actual_norm)
        
        # 5. Enrich with Risk and Recommendation
        for disc in discrepancies:
            disc["severity"] = RiskService.evaluate_risk(disc)
            disc["remediation"] = RecommendationService.generate_recommendation(disc)
            
        # 6. Higher-level Investigations
        findings = InvestigationService.analyze_patterns(discrepancies)
        
        # 7. Calculate stats
        summary = {
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
        
        # 8. Store in Database
        analysis_id = str(uuid.uuid4())
        
        await db.execute(
            """
            INSERT INTO analyses (id, name, status, cmdb_file, actual_file, summary_stats)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (analysis_id, req.name, "Completed", req.cmdb_file_path, req.actual_file_path, json.dumps(summary))
        )
        
        # Insert Assets Snapshots for audit trails
        asset_tuples = []
        for a in cmdb_norm:
            asset_tuples.append((analysis_id, "cmdb", a.external_id, a.hostname, a.ip_address, a.cpu, a.ram_gb, a.os, a.status))
        for a in actual_norm:
            asset_tuples.append((analysis_id, "actual", a.external_id, a.hostname, a.ip_address, a.cpu, a.ram_gb, a.os, a.status))
        
        if asset_tuples:
            await db.executemany(
                """
                INSERT INTO assets (analysis_id, source, external_id, hostname, ip_address, cpu, ram_gb, os, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                asset_tuples
            )
            
        # Insert Discrepancies
        disc_tuples = []
        for d in discrepancies:
            disc_tuples.append((
                d["id"],
                analysis_id,
                d["type"],
                d["severity"],
                d["description"],
                d.get("external_id"),
                d.get("hostname_cmdb"),
                d.get("hostname_actual"),
                d.get("ip_cmdb"),
                d.get("ip_actual"),
                json.dumps(d["details"]),
                d["remediation"]
            ))
            
        if disc_tuples:
            await db.executemany(
                """
                INSERT INTO discrepancies (id, analysis_id, type, severity, description, external_id, hostname_cmdb, hostname_actual, ip_cmdb, ip_actual, details, remediation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                disc_tuples
            )
            
        await db.commit()
        
    except Exception as e:
        await db.rollback()
        # Create a failed analysis record
        failed_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO analyses (id, name, status, cmdb_file, actual_file, summary_stats)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (failed_id, req.name, "Failed", req.cmdb_file_path, req.actual_file_path, json.dumps({"error": str(e)}))
        )
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
        
    return {"analysis_id": analysis_id}

@router.get("/analyses", response_model=List[AnalysisSummary])
async def list_analyses(db: aiosqlite.Connection = Depends(get_db)):
    """
    Returns lists of all past reconciliation analyses.
    """
    async with db.execute("SELECT * FROM analyses ORDER BY created_at DESC") as cursor:
        rows = await cursor.fetchall()
        
    results = []
    for r in rows:
        results.append(AnalysisSummary(
            id=r["id"],
            name=r["name"],
            status=r["status"],
            cmdb_file=r["cmdb_file"],
            actual_file=r["actual_file"],
            created_at=r["created_at"],
            summary_stats=json.loads(r["summary_stats"] or "{}")
        ))
    return results

@router.get("/analyses/{id}", response_model=AnalysisDetailResponse)
async def get_analysis_details(id: str, db: aiosqlite.Connection = Depends(get_db)):
    """
    Returns comprehensive details of a single analysis, including all detailed discrepancy logs.
    """
    # 1. Get analysis run
    async with db.execute("SELECT * FROM analyses WHERE id = ?", (id,)) as cursor:
        r = await cursor.fetchone()
        
    if not r:
        raise HTTPException(status_code=404, detail="Analysis run not found.")
        
    # 2. Get discrepancies
    async with db.execute("SELECT * FROM discrepancies WHERE analysis_id = ?", (id,)) as cursor:
        disc_rows = await cursor.fetchall()
        
    discrepancies = []
    for d in disc_rows:
        discrepancies.append(DiscrepancyResponse(
            id=d["id"],
            type=d["type"],
            severity=d["severity"],
            description=d["description"],
            external_id=d["external_id"],
            hostname_cmdb=d["hostname_cmdb"],
            hostname_actual=d["hostname_actual"],
            ip_cmdb=d["ip_cmdb"],
            ip_actual=d["ip_actual"],
            details=json.loads(d["details"] or "{}"),
            remediation=d["remediation"]
        ))
        
    return AnalysisDetailResponse(
        id=r["id"],
        name=r["name"],
        status=r["status"],
        cmdb_file=r["cmdb_file"],
        actual_file=r["actual_file"],
        created_at=r["created_at"],
        summary_stats=json.loads(r["summary_stats"] or "{}"),
        discrepancies=discrepancies
    )

@router.get("/analyses/{id}/stats", response_model=Dict[str, Any])
async def get_analysis_stats(id: str, db: aiosqlite.Connection = Depends(get_db)):
    """
    Returns summary statistics for a single analysis, useful for frontend dashboard graphs.
    """
    async with db.execute("SELECT summary_stats FROM analyses WHERE id = ?", (id,)) as cursor:
        row = await cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Analysis run not found.")
        
    return json.loads(row["summary_stats"] or "{}")
