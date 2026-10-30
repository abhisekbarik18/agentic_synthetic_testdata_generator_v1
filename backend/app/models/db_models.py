"""
SQLAlchemy ORM models for persistent job tracking.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.types import JSON

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    """Represents a single data-generation job."""

    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True)
    prompt = Column(Text, nullable=False)
    status = Column(String(20), default="pending", nullable=False, index=True)
    requested_formats = Column(JSON, default=list)

    # Agent outputs (stored as JSON blobs)
    requirement_spec = Column(JSON, nullable=True)
    generation_plan = Column(JSON, nullable=True)
    generated_data = Column(JSON, nullable=True)
    validation_result = Column(JSON, nullable=True)
    export_files = Column(JSON, nullable=True)

    # Per-agent status tracker:  { "requirement_analysis": "completed", ... }
    agent_statuses = Column(JSON, default=dict)

    error = Column(Text, nullable=True)
    record_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    def to_dict(self) -> dict:
        """Serialise to a plain dictionary for API responses."""
        return {
            "job_id": self.id,
            "prompt": self.prompt,
            "status": self.status,
            "formats": self.requested_formats or [],
            "agent_statuses": self.agent_statuses or {},
            "record_count": self.record_count or 0,
            "requirement_spec": self.requirement_spec,
            "generation_plan": self.generation_plan,
            "validation_result": self.validation_result,
            "export_files": self.export_files or [],
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

