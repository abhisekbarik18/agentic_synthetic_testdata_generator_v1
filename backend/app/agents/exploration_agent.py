"""
Scenario Exploration Agent
==========================
Builds a domain-specific scenario brief before schema extraction and generation.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.llm.provider import get_llm
from app.utils.json_repair import extract_and_parse_json
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a domain scenario analyst for synthetic data generation.
Analyze the request and produce a practical, internally consistent scenario brief.
Do not claim to have browsed external sources or cite unverifiable sources.
State assumptions explicitly. Prefer common operational conventions over invented
company-specific facts. For financial requests, identify the requested statements,
their normal line items, period/currency assumptions, accounting relationships,
and plausible operating drivers. Do not invent actual-company data.

Return only JSON with this shape:
{
  "domain": "short domain name",
  "scenario": "concise description of the scenario",
  "assumptions": ["explicit assumption"],
  "realism_rules": ["observable rule for generated records"],
  "relationships": ["cross-entity or workflow relationship"],
  "accounting_checks": ["equation or reconciliation, if applicable"]
}
"""


def exploration_node(state: AgentState) -> dict[str, Any]:
    """Analyze the request into realistic domain rules for downstream agents."""
    logger.info("[Exploration] Analyzing scenario for job %s", state.get("job_id"))
    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"User scenario request:\n{state['user_prompt']}"),
    ])
    brief = extract_and_parse_json(response.content)

    required_lists = ("assumptions", "realism_rules", "relationships", "accounting_checks")
    if not isinstance(brief, dict) or any(
        not isinstance(brief.get(key), list) for key in required_lists
    ):
        raise ValueError("Exploration response must contain the scenario brief lists.")

    logger.info(
        "[Exploration] Scenario brief created for domain %s",
        brief.get("domain", "unspecified"),
    )
    return {
        "scenario_context": brief,
        "current_agent": "exploration",
        "agent_messages": [
            f"Scenario exploration completed — domain: {brief.get('domain', 'unspecified')}."
        ],
    }
