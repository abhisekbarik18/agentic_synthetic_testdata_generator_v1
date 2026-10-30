"""
Requirement Analysis Agent
==========================
Extracts structured specifications from the user's natural-language prompt:
entities, fields, data types, constraints, relationships, business rules,
record counts, and requested output formats.
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.llm.provider import get_llm
from app.utils.json_repair import extract_and_parse_json
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are an expert **Requirements Analyst** for synthetic test-data generation.

Given a user's natural-language description, extract a structured JSON specification.

Return ONLY valid JSON matching this schema (no markdown fences, no conversational filler):

{
  "entities": [
    {
      "name": "entity_name",
      "description": "Short 1-sentence description",
      "record_count": 100,
      "fields": [
        {
          "name": "field_name",
          "data_type": "string|integer|float|date|datetime|email|phone|boolean|uuid|enum|address|name|company|url|currency|percentage|text",
          "constraints": {"min": 0, "max": 100, "enum_values": ["val1", "val2"]},
          "nullable": false,
          "unique": false,
          "description": "Short explanation",
          "example": "sample_val"
        }
      ],
      "relationships": [
        {
          "from_entity": "this_entity",
          "from_field": "fk_field",
          "to_entity": "other_entity",
          "to_field": "pk_field",
          "relationship_type": "many_to_one"
        }
      ],
      "business_rules": ["rule 1", "rule 2"]
    }
  ],
  "global_rules": ["cross-entity rule"],
  "include_edge_cases": true,
  "include_nulls": true,
  "include_duplicates": false,
  "output_formats": ["csv", "pdf"]
}

CRITICAL RULES:
- Keep all descriptions CONCISE (1 sentence max) to prevent token truncation.
- Limit to essential fields and realistic constraints.
- For financial statements, model rows as line items with period, statement_section,
  line_item, amount, and currency. Include meaningful subtotals and totals rather
  than unrelated sample rows; preserve user-requested entities and comparative periods.
- Add explicit business rules for applicable reconciliations, including assets =
  liabilities + equity and income-statement subtotals.
- Output ONLY the raw JSON object. Ensure all strings, brackets, and braces are fully closed.
"""


def requirement_analysis_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node — analyse the user prompt and produce a RequirementSpec."""
    logger.info("[RequirementAnalysis] Starting analysis for job %s", state.get("job_id"))

    llm = get_llm()
    user_prompt = state["user_prompt"]
    requested_formats = state.get("requested_formats", ["csv"])
    scenario_context = state.get("scenario_context")

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"User request:\n{user_prompt}\n\n"
                f"Scenario exploration brief:\n{json.dumps(scenario_context or {}, indent=2)}\n\n"
                f"Requested export formats: {', '.join(requested_formats)}\n\n"
                "Use the scenario brief to model realistic entities, line items, periods, "
                "and accounting/workflow relationships without overriding explicit user requirements. "
                "Extract the concise JSON specification now."
            )
        ),
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content.strip()
    except Exception as exc:
        logger.error("[RequirementAnalysis] LLM invocation failed: %s", exc)
        return {
            "status": "failed",
            "error": f"LLM invocation failed: {exc}",
            "current_agent": "requirement_analysis",
            "agent_messages": [f"RequirementAnalysis FAILED: {exc}"],
        }

    try:
        spec = extract_and_parse_json(raw)
        if not isinstance(spec, dict) or "entities" not in spec or not spec["entities"]:
            raise ValueError("Specification must contain a non-empty 'entities' list.")
    except Exception as exc:
        logger.error("[RequirementAnalysis] Failed to parse LLM response: %s", exc)
        # Attempt fallback rule extraction so the pipeline can still succeed
        spec = _build_fallback_spec(user_prompt, requested_formats)
        logger.info("[RequirementAnalysis] Generated fallback specification from user prompt.")

    # Ensure requested_formats are included
    if "output_formats" not in spec or not spec["output_formats"]:
        spec["output_formats"] = requested_formats
    if scenario_context:
        spec["scenario_context"] = scenario_context

    logger.info(
        "[RequirementAnalysis] Extracted %d entity(ies): %s",
        len(spec.get("entities", [])),
        [e["name"] for e in spec.get("entities", [])],
    )

    return {
        "requirement_spec": spec,
        "current_agent": "requirement_analysis",
        "agent_messages": [
            f"RequirementAnalysis completed — {len(spec.get('entities', []))} entity(ies) identified."
        ],
    }


def _build_fallback_spec(prompt: str, formats: list[str]) -> dict[str, Any]:
    """Build a sensible basic specification when the LLM output is unrecoverably malformed."""
    # Look for record count in prompt
    count_match = re.search(r"(\d+)\s*(?:records?|rows?|items?|users?|employees?|records|transactions?)", prompt, re.I)
    record_count = int(count_match.group(1)) if count_match else 50
    record_count = min(max(record_count, 10), 1000)

    # Basic entity guess
    entity_name = "records"
    if "employee" in prompt.lower():
        entity_name = "employees"
    elif "transaction" in prompt.lower():
        entity_name = "transactions"
    elif "customer" in prompt.lower() or "user" in prompt.lower():
        entity_name = "customers"
    elif "order" in prompt.lower():
        entity_name = "orders"
    elif "patient" in prompt.lower():
        entity_name = "patients"

    return {
        "entities": [
            {
                "name": entity_name,
                "description": f"Generated dataset based on: {prompt[:80]}...",
                "record_count": record_count,
                "fields": [
                    {"name": "id", "data_type": "integer", "unique": True, "nullable": False},
                    {"name": "name", "data_type": "name", "unique": False, "nullable": False},
                    {"name": "email", "data_type": "email", "unique": True, "nullable": False},
                    {"name": "created_at", "data_type": "datetime", "unique": False, "nullable": False},
                    {"name": "status", "data_type": "enum", "constraints": {"enum_values": ["active", "inactive", "pending"]}},
                ],
                "relationships": [],
                "business_rules": [],
            }
        ],
        "global_rules": [],
        "include_edge_cases": True,
        "include_nulls": True,
        "include_duplicates": False,
        "output_formats": formats,
    }
