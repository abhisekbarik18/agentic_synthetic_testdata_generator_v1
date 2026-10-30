"""
Data Generation Agent
=====================
Generates realistic synthetic records in batches using the LLM, following the
generation plan and requirement spec.  Handles edge cases, boundary values,
nulls, and optional duplicates.
"""

from __future__ import annotations

import json
import math
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.llm.provider import get_llm
from app.utils.json_repair import extract_and_parse_json
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

_GENERATION_SYSTEM = """\
You are a **Synthetic Data Generator**. Given a schema and constraints you
produce realistic, varied test data as a JSON array of objects.

Rules:
1. Return ONLY a valid JSON array — no markdown fences, no commentary.
2. Every object must have exactly the fields listed in the schema.
3. Respect ALL constraints (min/max, enum_values, patterns, uniqueness, nullable).
4. Generate realistic, varied values — avoid obvious patterns like "test1, test2 …".
5. Use culturally diverse names, addresses, and company names where appropriate.
6. For edge cases: include boundary values (e.g. min/max of ranges), empty strings
   for nullable string fields (sparingly), and realistic outliers.
7. For date fields use ISO-8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).
8. For email fields use realistic-looking but clearly fake domains (e.g. @example.com).
9. Ensure unique fields have no duplicates within this batch AND across the
   previously generated IDs supplied below.
10. Foreign-key fields must reference values from the supplied parent-entity IDs.
11. For financial records, use the scenario's business drivers and periods, not
    arbitrary values. Preserve line-item names and sign conventions. Reconcile
    subtotals and totals mathematically; balance-sheet assets must equal
    liabilities plus equity, and cash flows/equity roll-forwards must reconcile
    when those statements are requested.
"""


def generation_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node — generate synthetic data according to the plan."""
    logger.info("[Generation] Starting data generation for job %s", state.get("job_id"))

    spec = state.get("requirement_spec")
    plan = state.get("generation_plan")

    if not spec or not plan:
        return {
            "status": "failed",
            "error": "Generation agent missing requirement spec or plan.",
            "current_agent": "generation",
            "agent_messages": ["Generation FAILED — missing inputs."],
        }

    # On retry, start from the previously generated data (if any) so we only
    # regenerate entities that had validation errors.
    existing_data: dict[str, list[dict]] = state.get("generated_data") or {}
    validation_result = state.get("validation_result")
    entities_to_regenerate = _entities_needing_regen(validation_result, spec)

    entity_lookup: dict[str, dict] = {e["name"]: e for e in spec["entities"]}
    entity_order: list[str] = plan.get("entity_order", list(entity_lookup.keys()))
    strategy_lookup = {s["entity_name"]: s for s in plan.get("strategies", [])}

    llm = get_llm()
    all_data: dict[str, list[dict]] = dict(existing_data)
    messages_log: list[str] = []

    for entity_name in entity_order:
        entity = entity_lookup.get(entity_name)
        if not entity:
            continue

        # Skip entities that passed validation on a previous attempt.
        if entity_name in existing_data and entity_name not in entities_to_regenerate:
            logger.info("[Generation] Skipping %s (already valid).", entity_name)
            continue

        strategy = strategy_lookup.get(entity_name, {})
        batch_size = strategy.get("batch_size", 50)
        record_count = entity.get("record_count", 100)
        total_batches = math.ceil(record_count / batch_size)

        logger.info(
            "[Generation] Generating %d records for '%s' in %d batch(es).",
            record_count, entity_name, total_batches,
        )

        entity_records: list[dict] = []
        used_ids: dict[str, set] = {}  # field_name -> set of values (for uniqueness)

        for batch_idx in range(total_batches):
            remaining = record_count - len(entity_records)
            current_batch_size = min(batch_size, remaining)
            if current_batch_size <= 0:
                break

            prompt = _build_batch_prompt(
                entity=entity,
                batch_size=current_batch_size,
                batch_index=batch_idx,
                total_batches=total_batches,
                used_ids=used_ids,
                parent_data=all_data,
                include_edge_cases=spec.get("include_edge_cases", True),
                include_nulls=spec.get("include_nulls", True),
                scenario_context=state.get("scenario_context"),
            )

            try:
                response = llm.invoke([
                    SystemMessage(content=_GENERATION_SYSTEM),
                    HumanMessage(content=prompt),
                ])
                batch_records = _parse_json_array(response.content)

                # Track unique values for deduplication across batches.
                for rec in batch_records:
                    for field in entity.get("fields", []):
                        if field.get("unique") and field["name"] in rec:
                            used_ids.setdefault(field["name"], set()).add(rec[field["name"]])

                entity_records.extend(batch_records)
                logger.info(
                    "[Generation] %s batch %d/%d — got %d records (total %d).",
                    entity_name, batch_idx + 1, total_batches,
                    len(batch_records), len(entity_records),
                )
            except Exception as exc:
                logger.error("[Generation] Batch %d for %s failed: %s", batch_idx, entity_name, exc)
                messages_log.append(f"Generation batch {batch_idx} for {entity_name} error: {exc}")

        all_data[entity_name] = entity_records[:record_count]
        messages_log.append(f"Generated {len(all_data[entity_name])} records for {entity_name}.")

    total_records = sum(len(v) for v in all_data.values())
    logger.info("[Generation] Completed — %d total records across %d entities.", total_records, len(all_data))

    return {
        "generated_data": all_data,
        "current_agent": "generation",
        "agent_messages": [f"Generation completed — {total_records} total records."] + messages_log,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _entities_needing_regen(validation_result: dict | None, spec: dict) -> set[str]:
    """Identify entities that need regeneration based on validation errors."""
    if not validation_result:
        return set()
    errors = validation_result.get("errors", [])
    return {e.get("entity", "") for e in errors if e.get("entity")}


def _build_batch_prompt(
    *,
    entity: dict,
    batch_size: int,
    batch_index: int,
    total_batches: int,
    used_ids: dict[str, set],
    parent_data: dict[str, list[dict]],
    include_edge_cases: bool,
    include_nulls: bool,
    scenario_context: dict[str, Any] | None = None,
) -> str:
    """Construct the user prompt for a single generation batch."""
    fields_desc = json.dumps(entity.get("fields", []), indent=2)
    rules = entity.get("business_rules", [])
    relationships = entity.get("relationships", [])

    parts: list[str] = [
        f"Entity: {entity['name']}",
        f"Description: {entity.get('description', 'N/A')}",
        f"Generate exactly {batch_size} records (batch {batch_index + 1}/{total_batches}).",
        f"\nField schema:\n{fields_desc}",
    ]

    if scenario_context:
        parts.append(
            "\nScenario realism brief:\n"
            + json.dumps(scenario_context, indent=2, default=str)
            + "\nFollow these scenario assumptions and consistency rules. "
            "Do not replace user-specified facts or invent real-company data."
        )

    if rules:
        parts.append(f"\nBusiness rules:\n" + "\n".join(f"- {r}" for r in rules))

    if include_edge_cases and batch_index == total_batches - 1:
        parts.append(
            "\nInclude 2-3 edge-case records: boundary values, minimum/maximum "
            "constraint values, and realistic outliers."
        )

    if include_nulls:
        parts.append(
            "\nFor nullable fields, set ~10 % of values to null."
        )

    # Provide parent-entity IDs for FK references.
    for rel in relationships:
        parent_name = rel.get("to_entity", "")
        parent_field = rel.get("to_field", "id")
        if parent_name in parent_data:
            parent_ids = [r.get(parent_field) for r in parent_data[parent_name] if r.get(parent_field) is not None]
            if parent_ids:
                sample = parent_ids[:200]  # cap sample size for context window
                parts.append(
                    f"\nFor field '{rel.get('from_field')}', use values from this list "
                    f"(parent {parent_name}.{parent_field}):\n{json.dumps(sample)}"
                )

    # Provide already-used unique IDs to avoid collisions.
    for field_name, ids in used_ids.items():
        if ids:
            sample = list(ids)[:200]
            parts.append(f"\nAlready-used values for unique field '{field_name}' (do NOT reuse): {json.dumps(sample)}")

    return "\n".join(parts)


def _parse_json_array(text: str) -> list[dict]:
    """Best-effort parse of a JSON array from LLM output with truncation repair."""
    try:
        parsed = extract_and_parse_json(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            if "data" in parsed and isinstance(parsed["data"], list):
                return parsed["data"]
            if "records" in parsed and isinstance(parsed["records"], list):
                return parsed["records"]
            return [parsed]
    except Exception as exc:
        logger.warning("[Generation] Error extracting array via repair: %s", exc)

    raise ValueError(f"Could not parse JSON array from LLM response (first 200 chars): {text[:200]}")
