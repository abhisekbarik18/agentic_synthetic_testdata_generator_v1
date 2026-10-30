"""
LangGraph Orchestrator
======================
Defines the multi-agent pipeline as a LangGraph StateGraph with:
- Sequential flow: requirement → planning → generation → validation → export
- Error halting: if any stage fails, routes cleanly to END
- Conditional retry loop: validation → generation (up to max_retries)
- Status tracking and error propagation
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.export_agent import export_node
from app.agents.exploration_agent import exploration_node
from app.agents.generation_agent import generation_node
from app.agents.planning_agent import planning_node
from app.agents.requirement_agent import requirement_analysis_node
from app.agents.state import AgentState
from app.agents.validation_agent import validation_node
from app.config import settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Graph construction
# ═══════════════════════════════════════════════════════════════════════════════

def _build_graph() -> StateGraph:
    """Construct and compile the LangGraph StateGraph with robust error routing."""
    graph = StateGraph(AgentState)

    # ── Add nodes ────────────────────────────────────────────────────────
    graph.add_node("exploration", _wrap_node("exploration", exploration_node))
    graph.add_node("requirement_analysis", _wrap_node("requirement_analysis", requirement_analysis_node))
    graph.add_node("planning", _wrap_node("planning", planning_node))
    graph.add_node("generation", _wrap_node("generation", generation_node))
    graph.add_node("validation", _wrap_node("validation", validation_node))
    graph.add_node("export", _wrap_node("export", export_node))

    # ── Define edges with conditional error checks ───────────────────────
    graph.set_entry_point("exploration")

    # Step 1: exploration -> requirement_analysis (or END on failure)
    graph.add_conditional_edges(
        "exploration",
        _route_after_node("requirement_analysis"),
        {"next": "requirement_analysis", "fail": END},
    )

    # Step 2: requirement_analysis -> planning (or END on failure)
    graph.add_conditional_edges(
        "requirement_analysis",
        _route_after_node("planning"),
        {"next": "planning", "fail": END},
    )

    # Step 3: planning -> generation (or END on failure)
    graph.add_conditional_edges(
        "planning",
        _route_after_node("generation"),
        {"next": "generation", "fail": END},
    )

    # Step 4: generation -> validation (or END on failure)
    graph.add_conditional_edges(
        "generation",
        _route_after_node("validation"),
        {"next": "validation", "fail": END},
    )

    # Step 5: validation -> export (if valid) or -> generation (retry) or -> fail
    graph.add_conditional_edges(
        "validation",
        _validation_router,
        {
            "export": "export",
            "retry_generation": "generation",
            "fail": END,
        },
    )

    graph.add_edge("export", END)

    return graph


def _route_after_node(next_node: str):
    """Return a router that halts immediately if the current node flagged a failure."""
    def router(state: AgentState) -> str:
        if state.get("status") == "failed" or state.get("error"):
            logger.warning("[Orchestrator] Halting execution early due to failure before node '%s'.", next_node)
            return "fail"
        return "next"
    return router


def _validation_router(state: AgentState) -> str:
    """Decide the next step after validation."""
    if state.get("status") == "failed":
        return "fail"

    if state.get("is_valid", False):
        return "export"

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", settings.MAX_RETRIES)

    if retry_count < max_retries:
        logger.info(
            "[Orchestrator] Validation failed — retrying generation (attempt %d/%d).",
            retry_count + 1, max_retries,
        )
        return "retry_generation"

    logger.warning("[Orchestrator] Max retries (%d) exceeded — failing.", max_retries)
    return "fail"


def _wrap_node(name: str, fn):
    """Wrap a node function to inject status tracking and error handling."""

    def wrapper(state: AgentState) -> dict[str, Any]:
        logger.info("[Orchestrator] ▶ Running node: %s", name)
        try:
            result = fn(state)

            # Handle early failure from the node itself.
            if result.get("status") == "failed":
                return result

            # Bump retry_count when re-entering generation after a validation failure.
            if name == "generation" and state.get("validation_result") is not None:
                result["retry_count"] = state.get("retry_count", 0) + 1

            return result

        except Exception as exc:
            logger.exception("[Orchestrator] ✖ Node '%s' raised an exception.", name)
            return {
                "status": "failed",
                "error": f"Agent '{name}' error: {exc}",
                "current_agent": name,
                "agent_messages": [f"{name} EXCEPTION: {exc}"],
            }

    return wrapper


# ═══════════════════════════════════════════════════════════════════════════════
# Public interface
# ═══════════════════════════════════════════════════════════════════════════════

# Compile once at module load.
_compiled_graph = _build_graph().compile()


def run_generation_pipeline(
    job_id: str,
    user_prompt: str,
    requested_formats: list[str] | None = None,
    max_retries: int | None = None,
    *,
    on_status: Any | None = None,
) -> AgentState:
    """
    Execute the full generation pipeline synchronously.

    Parameters
    ----------
    job_id : str
        Unique job identifier.
    user_prompt : str
        The user's natural-language description.
    requested_formats : list[str], optional
        Export formats (default: ["csv"]).
    max_retries : int, optional
        Max validation→generation retries (default from config).
    on_status : callable, optional
        Callback ``(agent_name, status, message)`` for real-time updates.

    Returns
    -------
    AgentState
        Final state after the pipeline completes.
    """
    initial_state: AgentState = {
        "job_id": job_id,
        "user_prompt": user_prompt,
        "requested_formats": requested_formats or ["csv"],
        "scenario_context": None,
        "requirement_spec": None,
        "generation_plan": None,
        "generated_data": None,
        "validation_result": None,
        "is_valid": False,
        "retry_count": 0,
        "max_retries": max_retries if max_retries is not None else settings.MAX_RETRIES,
        "export_files": [],
        "current_agent": "",
        "status": "running",
        "error": None,
        "agent_messages": [],
    }

    logger.info("[Orchestrator] ═══ Starting pipeline for job %s ═══", job_id)

    # Stream the graph to get intermediate states for real-time updates.
    final_state: dict = dict(initial_state)
    for event in _compiled_graph.stream(initial_state, {"recursion_limit": 25}):
        for node_name, update in event.items():
            if isinstance(update, dict):
                msgs = update.pop("agent_messages", [])
                final_state.update(update)
                final_state.setdefault("agent_messages", [])
                final_state["agent_messages"].extend(msgs)

                if on_status and callable(on_status):
                    try:
                        on_status(
                            update.get("current_agent", node_name),
                            update.get("status", "running"),
                            msgs[-1] if msgs else "",
                        )
                    except Exception:
                        pass

    # Mark final status.
    if final_state.get("status") != "failed":
        if final_state.get("export_files"):
            final_state["status"] = "completed"
        elif final_state.get("is_valid") is False:
            final_state["status"] = "failed"
            final_state["error"] = final_state.get("error") or "Validation failed after max retries."

    logger.info(
        "[Orchestrator] ═══ Pipeline finished for job %s — status: %s ═══",
        job_id, final_state.get("status"),
    )

    return final_state  # type: ignore[return-value]
