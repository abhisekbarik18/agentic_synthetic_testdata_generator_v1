"""
Export Service
==============
Handles on-demand re-export of an existing job's data into additional formats.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.agents.export_agent import _export_entity
from app.config import settings
from app.models.db_models import Job
from app.utils.logging_config import get_logger
from app.utils.security import check_export_file_size, safe_filename

logger = get_logger(__name__)


def export_job_data(
    db: Session,
    job_id: str,
    formats: list[str],
    filters: dict[str, Any] | None = None,
) -> list[dict]:
    """
    Re-export a completed job's data into the requested formats.

    Returns a list of ExportFile dicts.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job {job_id} not found.")
    if not job.generated_data:
        raise ValueError(f"Job {job_id} has no generated data.")

    data: dict[str, list[dict]] = job.generated_data
    export_dir = Path(settings.EXPORT_DIR) / job_id
    export_dir.mkdir(parents=True, exist_ok=True)

    new_files: list[dict] = []

    for fmt in formats:
        fmt_lower = fmt.lower().strip()
        for entity_name, records in data.items():
            if not records:
                continue

            # Apply optional filters (simple field-value equality).
            filtered = records
            if filters and entity_name in filters:
                entity_filters = filters[entity_name]
                if isinstance(entity_filters, dict):
                    filtered = [
                        r for r in records
                        if all(r.get(k) == v for k, v in entity_filters.items())
                    ]

            df = pd.DataFrame(filtered)
            safe_entity = safe_filename(entity_name)

            try:
                file_info = _export_entity(df, safe_entity, fmt_lower, export_dir, entity_name)
            except Exception as exc:
                for created_file in new_files:
                    Path(created_file["path"]).unlink(missing_ok=True)
                db.rollback()
                logger.exception("Export failed for %s/%s.", entity_name, fmt)
                raise ValueError(f"Export failed for {entity_name} as {fmt}: {exc}") from exc

            if file_info:
                fpath = Path(file_info["path"])
                if not check_export_file_size(fpath):
                    logger.warning("Export file %s exceeds size limit.", fpath)
                new_files.append(file_info)

    # Persist the new export files to the job.
    existing = list(job.export_files or [])
    existing.extend(new_files)
    job.export_files = existing
    job.requested_formats = list(dict.fromkeys([
        *(job.requested_formats or []),
        *(fmt.lower().strip() for fmt in formats),
    ]))
    db.commit()

    return new_files
