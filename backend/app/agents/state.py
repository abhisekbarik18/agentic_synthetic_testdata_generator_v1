"""
Shared agent state — the TypedDict that flows through the LangGraph pipeline.

Every node reads from / writes to this structure.  Fields use ``Annotated``
with ``operator.add`` where values should be *appended* across node
invocations (e.g. log messages) rather than replaced.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    """
    Shared state flowing through the LangGraph pipeline.

    All fields are optional (total=False) so each node only needs to
    return the keys it modifies.
    """

    # ── Inputs (set once at graph entry) ─────────────────────────────────
    job_id: str
    user_prompt: str
    requested_formats: list[str]

    # ── Scenario exploration output ─────────────────────────────────────
    scenario_context: dict[str, Any] | None

    # ── Requirement Analysis output ──────────────────────────────────────
    requirement_spec: dict[str, Any] | None

    # ── Planning output ──────────────────────────────────────────────────
    generation_plan: dict[str, Any] | None

    # ── Data Generation output ───────────────────────────────────────────
    generated_data: dict[str, list[dict[str, Any]]] | None  # entity → rows

    # ── Validation output ────────────────────────────────────────────────
    validation_result: dict[str, Any] | None
    is_valid: bool
    retry_count: int
    max_retries: int

    # ── Export output ────────────────────────────────────────────────────
    export_files: list[dict[str, Any]]

    # ── Orchestration bookkeeping ────────────────────────────────────────
    current_agent: str
    status: str  # pending | running | completed | failed
    error: str | None
    agent_messages: Annotated[list[str], operator.add]
