import os
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import aiosqlite

from database.db import get_db
from services.report_service import ReportService

router = APIRouter(prefix="/api", tags=["Reports"])

@router.get("/reports/{id}")
@router.get("/reports/{id}/download.pdf")
async def get_pdf_report(
    id: str,
    db: aiosqlite.Connection = Depends(get_db)
):
    """
    Generates and downloads the PDF Audit reconciliation report for a given analysis run ID.
    """
    # 1. Fetch analysis metadata
    async with db.execute("SELECT * FROM analyses WHERE id = ?", (id,)) as cursor:
        analysis = await cursor.fetchone()
        
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis run not found.")
        
    if analysis["status"] != "Completed":
        raise HTTPException(status_code=400, detail="Cannot generate report for failed or running analysis.")
        
    summary_stats = json.loads(analysis["summary_stats"] or "{}")
    findings = summary_stats.get("findings", [])

    # 2. Fetch discrepancies list
    async with db.execute("SELECT * FROM discrepancies WHERE analysis_id = ?", (id,)) as cursor:
        rows = await cursor.fetchall()
        
    discrepancies = []
    for r in rows:
        discrepancies.append({
            "id": r["id"],
            "type": r["type"],
            "severity": r["severity"],
            "description": r["description"],
            "external_id": r["external_id"],
            "hostname_cmdb": r["hostname_cmdb"],
            "hostname_actual": r["hostname_actual"],
            "ip_cmdb": r["ip_cmdb"],
            "ip_actual": r["ip_actual"],
            "details": json.loads(r["details"] or "{}"),
            "remediation": r["remediation"]
        })
        
    # 3. Generate PDF file (cached/saved locally in reports/)
    try:
        pdf_path = await ReportService.generate_pdf(
            analysis_id=id,
            name=analysis["name"],
            cmdb_file=analysis["cmdb_file"],
            actual_file=analysis["actual_file"],
            created_at=analysis["created_at"],
            summary_stats=summary_stats,
            discrepancies=discrepancies,
            findings=findings
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF report: {str(e)}")
        
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="PDF report generation succeeded but file was not found.")
        
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"AssetSync_Report_{id}.pdf"
    )
