"""
Generation Service
==================
Orchestrates job lifecycle: creates the DB record, launches the LangGraph
pipeline in a background thread, updates the DB with results, and pushes
WebSocket progress events.
"""

from __future__ import annotations

import threading
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.agents.orchestrator import run_generation_pipeline
from app.api.websocket import manager as ws_manager
from app.models.db_models import Job
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def start_generation(prompt: str, formats: list[str], db: Session) -> str:
    """
    Create a new job and start the generation pipeline in a background thread.

    Returns the job_id.
    """
    job_id = str(uuid.uuid4())

    job = Job(
        id=job_id,
        prompt=prompt,
        status="pending",
        requested_formats=formats,
        agent_statuses={
            "exploration": "pending",
            "requirement_analysis": "pending",
            "planning": "pending",
            "generation": "pending",
            "validation": "pending",
            "export": "pending",
        },
    )
    db.add(job)
    db.commit()

    # Launch pipeline in a background thread so the API returns immediately.
    thread = threading.Thread(
        target=_run_pipeline_thread,
        args=(job_id, prompt, formats),
        daemon=True,
        name=f"pipeline-{job_id[:8]}",
    )
    thread.start()

    logger.info("Job %s created and pipeline thread started.", job_id)
    return job_id


def _run_pipeline_thread(job_id: str, prompt: str, formats: list[str]) -> None:
    """Run the LangGraph pipeline and persist results (executed in a thread)."""
    # Import here to get a fresh session for this thread.
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        _update_job(db, job_id, status="running")
        _broadcast(job_id, "job_status", status="running", message="Pipeline started.")

        def on_status(agent: str, status: str, message: str):
            """Callback fired by the orchestrator after each node."""
            _update_agent_status(db, job_id, agent, "completed" if status != "failed" else "failed")
            _broadcast(job_id, "agent_status", agent=agent, status="completed", message=message)

        final_state = run_generation_pipeline(
            job_id=job_id,
            user_prompt=prompt,
            requested_formats=formats,
            on_status=on_status,
        )

        # Persist results.
        updates: dict[str, Any] = {
            "status": final_state.get("status", "completed"),
            "requirement_spec": final_state.get("requirement_spec"),
            "generation_plan": final_state.get("generation_plan"),
            "generated_data": final_state.get("generated_data"),
            "validation_result": final_state.get("validation_result"),
            "export_files": final_state.get("export_files", []),
            "error": final_state.get("error"),
        }

        # Compute total record count.
        gen_data = final_state.get("generated_data") or {}
        updates["record_count"] = sum(len(v) for v in gen_data.values())

        _update_job(db, job_id, **updates)
        _broadcast(
            job_id, "job_status",
            status=updates["status"],
            message=f"Pipeline {updates['status']}.",
            data={"record_count": updates["record_count"], "export_files": updates["export_files"]},
        )

    except Exception as exc:
        logger.exception("Pipeline thread for job %s failed.", job_id)
        _update_job(db, job_id, status="failed", error=str(exc))
        _broadcast(job_id, "job_status", status="failed", message=str(exc))
    finally:
        db.close()


# ── DB helpers ───────────────────────────────────────────────────────────────

def _update_job(db: Session, job_id: str, **fields: Any) -> None:
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        for k, v in fields.items():
            setattr(job, k, v)
        db.commit()


def _update_agent_status(db: Session, job_id: str, agent: str, status: str) -> None:
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        statuses = dict(job.agent_statuses or {})
        statuses[agent] = status
        job.agent_statuses = statuses
        db.commit()


# ── WebSocket broadcast ─────────────────────────────────────────────────────

def _broadcast(job_id: str, msg_type: str, **kwargs: Any) -> None:
    """Best-effort broadcast a WebSocket message."""
    try:
        import asyncio
        msg = {"type": msg_type, "job_id": job_id, **kwargs}
        loop = asyncio.new_event_loop()
        loop.run_until_complete(ws_manager.broadcast_to_job(job_id, msg))
        loop.close()
    except Exception:
        pass  # WebSocket delivery is best-effort.
