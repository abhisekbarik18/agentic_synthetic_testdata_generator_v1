"""
Planning Agent
==============
Takes the structured RequirementSpec and produces a GenerationPlan:
entity ordering (topological sort by dependencies), batch sizes,
generation strategies, and special instructions.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.config import settings
from app.llm.provider import get_llm
from app.utils.json_repair import extract_and_parse_json
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a **Data Generation Planner** for a synthetic test-data generator.

Given a requirement specification (JSON), produce a generation plan.

Return ONLY valid JSON matching this schema (no markdown fences, no commentary):

{
  "entity_order": ["parent_entity", "child_entity"],
  "strategies": [
    {
      "entity_name": "entity_name",
      "approach": "llm_generate",
      "batch_size": 50,
      "dependencies": [],
      "special_instructions": "optional notes"
    }
  ],
  "estimated_batches": 2,
  "notes": "optional planning notes"
}

Rules:
1. **Topological order** — entities that are referenced by foreign keys must be generated BEFORE the entities that reference them.
2. **batch_size** — keep batches small enough for reliable LLM generation (≤50 records per batch by default; reduce for complex schemas).
3. **approach** — use "llm_generate" for most entities; use "reference" for join/bridge tables.
4. **estimated_batches** — ceil(record_count / batch_size) summed across entities.
5. **dependencies** — list the entity names this entity depends on (for FK lookups).
"""


def planning_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node — create a generation plan from the requirement spec."""
    logger.info("[Planning] Building generation plan for job %s", state.get("job_id"))

    spec = state.get("requirement_spec")
    if not spec:
        return {
            "status": "failed",
            "error": "Planning agent received no requirement spec.",
            "current_agent": "planning",
            "agent_messages": ["Planning FAILED — no requirement spec."],
        }

    llm = get_llm()

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Requirement specification:\n```json\n{json.dumps(spec, indent=2)}\n```\n\n"
                f"Default batch size from config: {settings.BATCH_SIZE}\n\n"
                "Produce the generation plan now."
            )
        ),
    ]

    response = llm.invoke(messages)
    raw = response.content.strip()

    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines)

    try:
        plan = extract_and_parse_json(raw)
    except Exception as exc:
        logger.error("[Planning] Failed to parse LLM response: %s", exc)
        # Fallback: build a simple sequential plan.
        plan = _build_fallback_plan(spec)
        logger.info("[Planning] Using fallback sequential plan.")

    logger.info(
        "[Planning] Plan ready — entity order: %s, estimated batches: %s",
        plan.get("entity_order", []),
        plan.get("estimated_batches", "?"),
    )

    return {
        "generation_plan": plan,
        "current_agent": "planning",
        "agent_messages": [
            f"Planning completed — order: {plan.get('entity_order', [])}, "
            f"~{plan.get('estimated_batches', '?')} batch(es)."
        ],
    }


def _build_fallback_plan(spec: dict) -> dict:
    """Construct a naive sequential plan when the LLM response fails to parse."""
    entities = spec.get("entities", [])
    order = [e["name"] for e in entities]
    strategies = []
    total_batches = 0

    for entity in entities:
        count = entity.get("record_count", 100)
        bs = settings.BATCH_SIZE
        batches = -(-count // bs)  # ceil division
        total_batches += batches

        deps: list[str] = []
        for rel in entity.get("relationships", []):
            target = rel.get("to_entity", "")
            if target and target != entity["name"] and target not in deps:
                deps.append(target)

        strategies.append({
            "entity_name": entity["name"],
            "approach": "llm_generate",
            "batch_size": bs,
            "dependencies": deps,
            "special_instructions": None,
        })

    return {
        "entity_order": order,
        "strategies": strategies,
        "estimated_batches": total_batches,
        "notes": "Fallback sequential plan (LLM parse error).",
    }

