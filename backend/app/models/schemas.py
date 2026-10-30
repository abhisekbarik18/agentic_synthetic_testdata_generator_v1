"""
Pydantic schemas for API request / response payloads and internal data models.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class ExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"
    XML = "xml"
    SQL = "sql"
    PARQUET = "parquet"
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    DOCX = "docx"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ═══════════════════════════════════════════════════════════════════════════════
# Requirement Spec Models (produced by Requirement Analysis Agent)
# ═══════════════════════════════════════════════════════════════════════════════

class FieldSpec(BaseModel):
    """Describes a single field / column in an entity."""
    name: str
    data_type: str  # string, integer, float, date, datetime, email, phone, boolean, uuid, enum, etc.
    constraints: Optional[dict[str, Any]] = None  # min, max, pattern, enum_values, min_length, max_length …
    nullable: bool = False
    unique: bool = False
    description: Optional[str] = None
    example: Optional[Any] = None


class RelationshipSpec(BaseModel):
    """Describes a foreign-key / referential relationship between entities."""
    from_entity: str
    from_field: str
    to_entity: str
    to_field: str
    relationship_type: str = "many_to_one"  # one_to_one | one_to_many | many_to_one


class EntitySpec(BaseModel):
    """Describes a single table / entity to generate."""
    name: str
    fields: list[FieldSpec]
    record_count: int = 100
    relationships: list[RelationshipSpec] = Field(default_factory=list)
    business_rules: list[str] = Field(default_factory=list)
    description: Optional[str] = None


class RequirementSpec(BaseModel):
    """Complete structured specification extracted from the user prompt."""
    entities: list[EntitySpec]
    global_rules: list[str] = Field(default_factory=list)
    include_edge_cases: bool = True
    include_nulls: bool = True
    include_duplicates: bool = False
    output_formats: list[str] = Field(default_factory=lambda: ["csv"])


# ═══════════════════════════════════════════════════════════════════════════════
# Planning Models (produced by Planning Agent)
# ═══════════════════════════════════════════════════════════════════════════════

class GenerationStrategy(BaseModel):
    entity_name: str
    approach: str = "llm_generate"  # llm_generate | faker | pattern | reference
    batch_size: int = 50
    dependencies: list[str] = Field(default_factory=list)
    special_instructions: Optional[str] = None


class GenerationPlan(BaseModel):
    entity_order: list[str]
    strategies: list[GenerationStrategy]
    estimated_batches: int = 1
    notes: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Validation Models (produced by Validation Agent)
# ═══════════════════════════════════════════════════════════════════════════════

class ValidationError(BaseModel):
    entity: str
    field: Optional[str] = None
    record_index: Optional[int] = None
    error_type: str  # type_mismatch | constraint_violation | missing_required | referential_integrity | business_rule
    message: str
    severity: str = "error"  # error | warning


class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[ValidationError] = Field(default_factory=list)
    records_checked: int = 0
    records_passed: int = 0
    records_failed: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# Export Models (produced by Export Agent)
# ═══════════════════════════════════════════════════════════════════════════════

class ExportFile(BaseModel):
    filename: str
    format: str
    path: str
    size_bytes: int
    record_count: int
    entity_name: Optional[str] = None
    created_at: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# API Request / Response Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class GenerateRequest(BaseModel):
    """POST /api/generate — kick off a new generation job."""
    prompt: str = Field(..., min_length=10, max_length=10_000, description="Natural-language description of the desired test data.")
    formats: list[ExportFormat] = Field(default=[ExportFormat.CSV], description="Export formats to produce.")


class ExportRequest(BaseModel):
    """POST /api/jobs/{id}/export — request additional export formats."""
    formats: list[ExportFormat]
    filters: Optional[dict[str, Any]] = None


class FollowUpRequest(BaseModel):
    """POST /api/jobs/{id}/followup — modify or regenerate data."""
    prompt: str = Field(..., min_length=5, max_length=10_000)
    regenerate: bool = False


class AgentStatusInfo(BaseModel):
    name: str
    status: str = "pending"  # pending | running | completed | failed
    message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    status: str
    prompt: str
    formats: list[str]
    agent_statuses: list[AgentStatusInfo] = Field(default_factory=list)
    record_count: int = 0
    requirement_spec: Optional[dict[str, Any]] = None
    validation_result: Optional[dict[str, Any]] = None
    export_files: list[ExportFile] = Field(default_factory=list)
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


class DataPreviewResponse(BaseModel):
    entities: dict[str, list[dict[str, Any]]]
    total_records: dict[str, int]
    preview_limit: int = 100


# ═══════════════════════════════════════════════════════════════════════════════
# WebSocket Message Schema
# ═══════════════════════════════════════════════════════════════════════════════

class WSMessage(BaseModel):
    """Message pushed over the WebSocket to the frontend."""
    type: str  # agent_status | job_status | error | progress
    agent: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    progress: Optional[float] = None  # 0.0 – 1.0
    data: Optional[dict[str, Any]] = None
