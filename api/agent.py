import asyncio
import os
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import aiosqlite

from services.agent_service import AgentService
from services.agent_llm import AgentLLM
from database.db import get_db

router = APIRouter(prefix="/api/agent", tags=["Agent"])


class RunRequest(BaseModel):
    cmdb_file_path: str
    actual_file_path: str


@router.post("/run")
async def run_agent(req: RunRequest):
    svc = AgentService()
    result = await svc.run_and_summarize(req.cmdb_file_path, req.actual_file_path)
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result)
    return result

@router.get("/summary/{analysis_id}")
async def get_summary(analysis_id: str, db: aiosqlite.Connection = Depends(get_db)):
    """Fetch an AI-generated Executive Summary for a specific analysis run."""
    async with db.execute("SELECT * FROM discrepancies WHERE analysis_id = ?", (analysis_id,)) as cursor:
        rows = await cursor.fetchall()
    
    if not rows:
        # If there are no discrepancies, it means it's a perfect match
        return {"summary": "No discrepancies found in this audit. The expected CMDB inventory perfectly matches the live discovery scan."}
        
    discrepancies = []
    for r in rows:
        discrepancies.append({
            "id": r["id"],
            "type": r["type"],
            "description": r["description"],
            "severity": r["severity"]
        })
        
    try:
        agent_llm = AgentLLM()
        # Optionally index them (could be slow, but let's do it as the original workflow did)
        # agent_llm.index_discrepancies(discrepancies) 
        
        # We really just need the summary for the UI right now
        summary = agent_llm.summarize_discrepancies(discrepancies)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")
