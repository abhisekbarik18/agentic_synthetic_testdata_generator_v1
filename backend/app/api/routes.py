"""
REST API routes for the Test Data Simulator.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.websocket import manager as ws_manager
from app.config import settings
from app.database import get_db
from app.models.db_models import Job
from app.models.schemas import (
    AgentStatusInfo,
    DataPreviewResponse,
    ExportFile,
    ExportRequest,
    FollowUpRequest,
    GenerateRequest,
    JobListResponse,
    JobResponse,
)
from app.services.export_service import export_job_data
from app.services.generation_service import start_generation
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["generation"])

_FOLLOWUP_FORMAT_PATTERNS: dict[str, tuple[str, ...]] = {
    "csv": (r"\bcsv\b", r"\.csv\b", r"\bcomma[- ]separated\b"),
    "json": (r"\bjson\b", r"\.json\b"),
    "xlsx": (r"\bxlsx?\b", r"\.xlsx?\b", r"\bexcel\b", r"\bspreadsheet\b"),
    "sql": (r"\bsql\b", r"\.sql\b", r"\bsql inserts?\b"),
    "parquet": (r"\bparquet\b", r"\.parquet\b"),
    "xml": (r"\bxml\b", r"\.xml\b"),
    "pdf": (r"\bpdf\b", r"\.pdf\b"),
    "html": (r"\bhtml\b", r"\.html?\b"),
    "markdown": (r"\bmarkdown\b", r"\.md\b"),
    "docx": (r"\bdocx\b", r"\.docx\b", r"\bword document\b", r"\bmicrosoft word\b"),
}


def _formats_in_followup(prompt: str) -> list[str]:
    """Find explicitly requested export formats in a follow-up instruction."""
    matches: list[tuple[int, int, str]] = []
    for order, (fmt, patterns) in enumerate(_FOLLOWUP_FORMAT_PATTERNS.items()):
        positions = [
            match.start()
            for pattern in patterns
            for match in re.finditer(pattern, prompt, re.IGNORECASE)
        ]
        if positions:
            matches.append((min(positions), order, fmt))
    return [fmt for _, _, fmt in sorted(matches)]


# ═══════════════════════════════════════════════════════════════════════════════
# Jobs
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/generate", response_model=JobResponse, status_code=202)
def create_generation_job(req: GenerateRequest, db: Session = Depends(get_db)):
    """Start a new data-generation job from a natural-language prompt."""
    formats = [f.value for f in req.formats]
    job_id = start_generation(req.prompt, formats, db)

    job = db.query(Job).filter(Job.id == job_id).first()
    return _to_job_response(job)


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """List all jobs, newest first."""
    total = db.query(Job).count()
    jobs = db.query(Job).order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
    return JobListResponse(jobs=[_to_job_response(j) for j in jobs], total=total)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get the current status and details of a job."""
    job = _get_job_or_404(job_id, db)
    return _to_job_response(job)


@router.get("/jobs/{job_id}/data", response_model=DataPreviewResponse)
def get_job_data(job_id: str, limit: int = 100, db: Session = Depends(get_db)):
    """Return a preview of the generated data (first N records per entity)."""
    job = _get_job_or_404(job_id, db)
    if not job.generated_data:
        raise HTTPException(404, "No data generated yet.")

    entities: dict[str, list[dict]] = {}
    totals: dict[str, int] = {}
    for name, records in job.generated_data.items():
        totals[name] = len(records)
        entities[name] = records[:limit]

    return DataPreviewResponse(entities=entities, total_records=totals, preview_limit=limit)


# ═══════════════════════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/jobs/{job_id}/export")
def export_data(job_id: str, req: ExportRequest, db: Session = Depends(get_db)):
    """Export the job's data in additional formats."""
    _get_job_or_404(job_id, db)
    try:
        files = export_job_data(db, job_id, [f.value for f in req.formats], req.filters)
        return {"files": files}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/jobs/{job_id}/export/{filename}")
def download_export(job_id: str, filename: str, db: Session = Depends(get_db)):
    """Download an exported file."""
    _get_job_or_404(job_id, db)
    path = Path(settings.EXPORT_DIR) / job_id / filename
    if not path.exists():
        raise HTTPException(404, f"File '{filename}' not found.")
    return FileResponse(path, filename=filename, media_type="application/octet-stream")


# ═══════════════════════════════════════════════════════════════════════════════
# Follow-up
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/jobs/{job_id}/followup", response_model=JobResponse, status_code=202)
def followup(job_id: str, req: FollowUpRequest, db: Session = Depends(get_db)):
    """
    Follow-up prompt: modify, regenerate, or re-export.

    If ``regenerate`` is True, a brand-new pipeline run is started using the
    follow-up prompt.  Otherwise, the existing validated data is re-exported.
    """
    original = _get_job_or_404(job_id, db)

    if req.regenerate:
        # Start a new job that references the original prompt for context.
        combined_prompt = (
            f"Original request:\n{original.prompt}\n\n"
            f"Follow-up instruction:\n{req.prompt}"
        )
        formats = list(dict.fromkeys([
            *(original.requested_formats or ["csv"]),
            *_formats_in_followup(req.prompt),
        ]))
        new_job_id = start_generation(combined_prompt, formats, db)
        new_job = db.query(Job).filter(Job.id == new_job_id).first()
        return _to_job_response(new_job)
    else:
        formats = _formats_in_followup(req.prompt)
        if not formats and re.search(r"\b(re-?export|export again|same formats?)\b", req.prompt, re.IGNORECASE):
            formats = original.requested_formats or ["csv"]
        if not formats:
            raise HTTPException(
                400,
                "No supported export format was found in the instruction. "
                "Name a format such as CSV, JSON, Excel, SQL, Parquet, XML, PDF, HTML, Markdown, or Word, "
                "or enable Regenerate Records to change the data or schema.",
            )
        try:
            export_job_data(db, job_id, formats)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        db.refresh(original)
        return _to_job_response(original)


# ═══════════════════════════════════════════════════════════════════════════════
# WebSocket
# ═══════════════════════════════════════════════════════════════════════════════

@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job progress updates."""
    await ws_manager.connect(websocket, job_id)
    try:
        while True:
            # Keep the connection alive; the client can also send messages.
            data = await websocket.receive_text()
            logger.debug("WS received from client: %s", data)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, job_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _get_job_or_404(job_id: str, db: Session) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found.")
    return job


def _to_job_response(job: Job) -> JobResponse:
    """Convert a Job ORM instance to a JobResponse schema."""
    agent_statuses = []
    for name in ("exploration", "requirement_analysis", "planning", "generation", "validation", "export"):
        status = (job.agent_statuses or {}).get(name, "pending")
        agent_statuses.append(AgentStatusInfo(name=name, status=status))

    export_files = []
    for ef in (job.export_files or []):
        export_files.append(ExportFile(**ef))

    return JobResponse(
        job_id=job.id,
        status=job.status,
        prompt=job.prompt,
        formats=job.requested_formats or [],
        agent_statuses=agent_statuses,
        record_count=job.record_count or 0,
        requirement_spec=job.requirement_spec,
        validation_result=job.validation_result,
        export_files=export_files,
        error=job.error,
        created_at=job.created_at.isoformat() if job.created_at else None,
        updated_at=job.updated_at.isoformat() if job.updated_at else None,
    )
