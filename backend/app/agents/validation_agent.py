"""
Validation Agent
================
Validates generated data against the requirement spec:
- Data-type checks
- Constraint enforcement (min/max, pattern, enum, length, uniqueness)
- Required-field (non-nullable) checks
- Referential integrity (foreign-key references)
- Business-rule checks (via LLM for natural-language rules)

Produces a ValidationResult with errors and warnings.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.llm.provider import get_llm
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def validation_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node — validate generated data against the spec."""
    logger.info("[Validation] Starting validation for job %s", state.get("job_id"))

    spec = state.get("requirement_spec")
    data = state.get("generated_data")

    if not spec or not data:
        return {
            "is_valid": False,
            "status": "failed",
            "error": "Validation agent missing spec or data.",
            "current_agent": "validation",
            "agent_messages": ["Validation FAILED — missing inputs."],
        }

    entity_lookup = {e["name"]: e for e in spec.get("entities", [])}
    all_errors: list[dict] = []
    all_warnings: list[dict] = []
    total_checked = 0
    total_passed = 0

    for entity_name, records in data.items():
        entity = entity_lookup.get(entity_name)
        if not entity:
            all_warnings.append({
                "entity": entity_name,
                "error_type": "unknown_entity",
                "message": f"Entity '{entity_name}' not in spec — skipping validation.",
                "severity": "warning",
            })
            continue

        field_lookup = {f["name"]: f for f in entity.get("fields", [])}

        for idx, record in enumerate(records):
            total_checked += 1
            record_errors = []

            # ── Check each field ─────────────────────────────────────────
            for field in entity.get("fields", []):
                fname = field["name"]
                value = record.get(fname)

                # Required check
                if not field.get("nullable", False) and value is None:
                    record_errors.append(_err(entity_name, fname, idx, "missing_required",
                                              f"Required field '{fname}' is null."))
                    continue

                if value is None:
                    continue  # nullable and null — OK

                # Type check
                type_error = _check_type(value, field.get("data_type", "string"), fname, entity_name, idx)
                if type_error:
                    record_errors.append(type_error)

                # Constraint checks
                constraint_errors = _check_constraints(value, field, entity_name, idx)
                record_errors.extend(constraint_errors)

            if record_errors:
                all_errors.extend(record_errors)
            else:
                total_passed += 1

        # ── Uniqueness checks (across all records) ───────────────────────
        for field in entity.get("fields", []):
            if field.get("unique"):
                values = [r.get(field["name"]) for r in records if r.get(field["name"]) is not None]
                dupes = len(values) - len(set(str(v) for v in values))
                if dupes > 0:
                    all_errors.append(_err(entity_name, field["name"], None, "constraint_violation",
                                          f"Unique field '{field['name']}' has {dupes} duplicate(s)."))

    # ── Referential integrity ────────────────────────────────────────────
    for entity in spec.get("entities", []):
        for rel in entity.get("relationships", []):
            ri_errors = _check_referential_integrity(rel, data)
            all_errors.extend(ri_errors)

    all_errors.extend(_validate_financial_consistency(data))

    # ── Business-rule validation via LLM (if rules exist) ────────────────
    business_rules = _collect_business_rules(spec)
    if business_rules and all_errors == []:
        # Only run LLM business-rule check if structural validation passed.
        br_issues = _validate_business_rules(business_rules, data, spec)
        all_warnings.extend(br_issues)

    is_valid = len(all_errors) == 0
    result = {
        "is_valid": is_valid,
        "errors": all_errors,
        "warnings": all_warnings,
        "records_checked": total_checked,
        "records_passed": total_passed,
        "records_failed": total_checked - total_passed,
    }

    logger.info(
        "[Validation] Result: valid=%s, errors=%d, warnings=%d, checked=%d",
        is_valid, len(all_errors), len(all_warnings), total_checked,
    )

    return {
        "validation_result": result,
        "is_valid": is_valid,
        "current_agent": "validation",
        "agent_messages": [
            f"Validation {'PASSED' if is_valid else 'FAILED'} — "
            f"{len(all_errors)} error(s), {len(all_warnings)} warning(s), "
            f"{total_checked} records checked."
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _err(entity: str, field: str | None, idx: int | None, etype: str, msg: str) -> dict:
    return {"entity": entity, "field": field, "record_index": idx, "error_type": etype,
            "message": msg, "severity": "error"}


def _warn(entity: str, field: str | None, idx: int | None, etype: str, msg: str) -> dict:
    return {"entity": entity, "field": field, "record_index": idx, "error_type": etype,
            "message": msg, "severity": "warning"}


def _check_type(value: Any, data_type: str, fname: str, entity: str, idx: int) -> dict | None:
    """Return an error dict if value doesn't match the expected data_type."""
    dt = data_type.lower()
    if dt in ("string", "text", "name", "address", "company", "url", "email", "phone", "ip_address"):
        if not isinstance(value, str):
            return _err(entity, fname, idx, "type_mismatch", f"Expected string for '{fname}', got {type(value).__name__}.")
    elif dt == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            # Allow string-encoded ints.
            try:
                int(value)
            except (ValueError, TypeError):
                return _err(entity, fname, idx, "type_mismatch", f"Expected integer for '{fname}', got {type(value).__name__}.")
    elif dt in ("float", "currency", "percentage"):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            try:
                float(value)
            except (ValueError, TypeError):
                return _err(entity, fname, idx, "type_mismatch", f"Expected number for '{fname}', got {type(value).__name__}.")
    elif dt == "boolean":
        if not isinstance(value, bool):
            return _err(entity, fname, idx, "type_mismatch", f"Expected boolean for '{fname}', got {type(value).__name__}.")
    elif dt in ("date", "datetime"):
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return _err(entity, fname, idx, "type_mismatch", f"Invalid ISO date for '{fname}': {value}")
    elif dt == "enum":
        pass  # handled by constraints
    return None


def _check_constraints(value: Any, field: dict, entity: str, idx: int) -> list[dict]:
    """Check field-level constraints and return a list of errors."""
    errors: list[dict] = []
    constraints = field.get("constraints") or {}
    fname = field["name"]

    if "min" in constraints and isinstance(value, (int, float)):
        if value < constraints["min"]:
            errors.append(_err(entity, fname, idx, "constraint_violation",
                               f"'{fname}' value {value} < min {constraints['min']}."))
    if "max" in constraints and isinstance(value, (int, float)):
        if value > constraints["max"]:
            errors.append(_err(entity, fname, idx, "constraint_violation",
                               f"'{fname}' value {value} > max {constraints['max']}."))
    if "min_length" in constraints and isinstance(value, str):
        if len(value) < constraints["min_length"]:
            errors.append(_err(entity, fname, idx, "constraint_violation",
                               f"'{fname}' length {len(value)} < min_length {constraints['min_length']}."))
    if "max_length" in constraints and isinstance(value, str):
        if len(value) > constraints["max_length"]:
            errors.append(_err(entity, fname, idx, "constraint_violation",
                               f"'{fname}' length {len(value)} > max_length {constraints['max_length']}."))
    if "pattern" in constraints and isinstance(value, str):
        try:
            if not re.match(constraints["pattern"], value):
                errors.append(_err(entity, fname, idx, "constraint_violation",
                                   f"'{fname}' value does not match pattern {constraints['pattern']}."))
        except re.error:
            pass  # skip invalid regex
    if "enum_values" in constraints:
        if value not in constraints["enum_values"]:
            errors.append(_err(entity, fname, idx, "constraint_violation",
                               f"'{fname}' value '{value}' not in enum {constraints['enum_values']}."))
    return errors


def _check_referential_integrity(rel: dict, data: dict) -> list[dict]:
    """Verify all FK values exist in the referenced parent entity."""
    errors: list[dict] = []
    from_entity = rel.get("from_entity", "")
    from_field = rel.get("from_field", "")
    to_entity = rel.get("to_entity", "")
    to_field = rel.get("to_field", "id")

    if from_entity not in data or to_entity not in data:
        return errors  # can't check if data is missing

    parent_values = {str(r.get(to_field)) for r in data[to_entity] if r.get(to_field) is not None}

    for idx, record in enumerate(data[from_entity]):
        fk_value = record.get(from_field)
        if fk_value is not None and str(fk_value) not in parent_values:
            errors.append(_err(from_entity, from_field, idx, "referential_integrity",
                               f"FK value '{fk_value}' not found in {to_entity}.{to_field}."))
    return errors


_FINANCIAL_ENTITY_MARKERS = (
    "financialstatement", "incomestatement", "statementofincome", "profitandloss",
    "balance sheet", "balancesheet", "cashflowstatement", "statementofcashflows",
    "statementofchangesequity", "soi",
)
_ACCOUNT_LABEL_FIELDS = ("line_item", "account", "account_name", "description", "name")
_AMOUNT_FIELDS = ("amount", "balance", "value", "current_period_amount")


def _validate_financial_consistency(data: dict[str, list[dict]]) -> list[dict]:
    """Check statement totals and accounting equations when generated data exposes them."""
    errors: list[dict] = []
    for entity_name, records in data.items():
        normalized_entity = _normalize_financial_label(entity_name)
        if not any(_normalize_financial_label(marker) in normalized_entity for marker in _FINANCIAL_ENTITY_MARKERS):
            continue

        periods: dict[str, dict[str, Decimal]] = {}
        for record in records:
            period = str(
                record.get("period")
                or record.get("fiscal_period")
                or record.get("fiscal_year")
                or "unspecified"
            )
            account_field = next(
                (field for field in _ACCOUNT_LABEL_FIELDS if record.get(field) is not None),
                None,
            )
            amount_field = next(
                (field for field in _AMOUNT_FIELDS if record.get(field) is not None),
                None,
            )

            if account_field and amount_field:
                amount = _to_decimal(record[amount_field])
                if amount is not None:
                    label = _normalize_financial_label(str(record[account_field]))
                    periods.setdefault(period, {})[label] = amount

            values = periods.setdefault(period, {})
            for field, value in record.items():
                amount = _to_decimal(value)
                if amount is not None:
                    values[_normalize_financial_label(field)] = amount

        for period, amounts in periods.items():
            errors.extend(_check_balance_sheet_equation(entity_name, period, amounts))
            errors.extend(_check_income_statement_equations(entity_name, period, amounts))
            errors.extend(_check_cash_flow_equation(entity_name, period, amounts))
            errors.extend(_check_equity_roll_forward(entity_name, period, amounts))

    return errors


def _normalize_financial_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _to_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        if isinstance(value, str):
            cleaned = value.strip().replace(",", "").replace("$", "").replace("€", "").replace("£", "")
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = f"-{cleaned[1:-1]}"
            value = cleaned
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _find_financial_amount(amounts: dict[str, Decimal], *labels: str) -> Decimal | None:
    for label in labels:
        value = amounts.get(_normalize_financial_label(label))
        if value is not None:
            return value
    return None


def _check_equation(
    entity: str,
    period: str,
    description: str,
    actual: Decimal,
    expected: Decimal,
) -> list[dict]:
    tolerance = max(Decimal("0.01"), abs(expected) * Decimal("0.0001"))
    if abs(actual - expected) <= tolerance:
        return []
    return [
        _err(
            entity,
            "amount",
            None,
            "accounting_reconciliation",
            f"{description} does not reconcile for period '{period}': "
            f"actual {actual}, expected {expected}.",
        )
    ]


def _expense_deducted(income: Decimal, expense: Decimal) -> Decimal:
    return income + expense if expense < 0 else income - expense


def _check_balance_sheet_equation(
    entity: str, period: str, amounts: dict[str, Decimal]
) -> list[dict]:
    assets = _find_financial_amount(amounts, "total assets", "assets")
    liabilities_and_equity = _find_financial_amount(
        amounts, "total liabilities and equity", "liabilities and equity",
    )
    liabilities = _find_financial_amount(amounts, "total liabilities", "liabilities")
    equity = _find_financial_amount(amounts, "total equity", "equity", "total stockholders equity")

    if assets is None:
        return []
    if liabilities_and_equity is not None:
        return _check_equation(
            entity, period, "Balance sheet equation (assets = liabilities + equity)",
            assets, liabilities_and_equity,
        )
    if liabilities is not None and equity is not None:
        return _check_equation(
            entity, period, "Balance sheet equation (assets = liabilities + equity)",
            assets, liabilities + equity,
        )
    return []


def _check_income_statement_equations(
    entity: str, period: str, amounts: dict[str, Decimal]
) -> list[dict]:
    errors: list[dict] = []
    revenue = _find_financial_amount(amounts, "total revenue", "revenue", "net sales", "sales")
    cost_of_sales = _find_financial_amount(
        amounts, "cost of goods sold", "cost of sales", "cogs",
    )
    gross_profit = _find_financial_amount(amounts, "gross profit")
    operating_expenses = _find_financial_amount(
        amounts, "total operating expenses", "operating expenses",
    )
    operating_income = _find_financial_amount(amounts, "operating income", "operating profit")
    pretax_income = _find_financial_amount(
        amounts, "income before tax", "income before taxes", "pretax income",
    )
    tax = _find_financial_amount(amounts, "income tax expense", "tax expense", "income taxes")
    net_income = _find_financial_amount(amounts, "net income", "net profit")

    if revenue is not None and cost_of_sales is not None and gross_profit is not None:
        errors.extend(_check_equation(
            entity, period, "Gross profit (revenue less cost of sales)", gross_profit,
            _expense_deducted(revenue, cost_of_sales),
        ))
    if gross_profit is not None and operating_expenses is not None and operating_income is not None:
        errors.extend(_check_equation(
            entity, period, "Operating income (gross profit less operating expenses)",
            operating_income, _expense_deducted(gross_profit, operating_expenses),
        ))

    income_before_tax = pretax_income or operating_income
    if income_before_tax is not None and tax is not None and net_income is not None:
        errors.extend(_check_equation(
            entity, period, "Net income (income before tax less tax)", net_income,
            _expense_deducted(income_before_tax, tax),
        ))
    return errors


def _check_cash_flow_equation(
    entity: str, period: str, amounts: dict[str, Decimal]
) -> list[dict]:
    opening_cash = _find_financial_amount(
        amounts, "beginning cash", "opening cash", "cash at beginning of period",
        "cash and cash equivalents at beginning of period",
    )
    net_change = _find_financial_amount(
        amounts, "net change in cash", "net increase decrease in cash",
        "increase decrease in cash", "change in cash",
    )
    ending_cash = _find_financial_amount(
        amounts, "ending cash", "closing cash", "cash at end of period",
        "cash and cash equivalents at end of period",
    )
    if opening_cash is None or net_change is None or ending_cash is None:
        return []
    return _check_equation(
        entity, period, "Cash flow reconciliation (opening cash + net change = ending cash)",
        ending_cash, opening_cash + net_change,
    )


def _check_equity_roll_forward(
    entity: str, period: str, amounts: dict[str, Decimal]
) -> list[dict]:
    beginning_equity = _find_financial_amount(
        amounts, "beginning equity", "opening equity", "equity at beginning of period",
    )
    ending_equity = _find_financial_amount(
        amounts, "ending equity", "closing equity", "equity at end of period",
    )
    net_income = _find_financial_amount(amounts, "net income", "net profit")
    contributions = _find_financial_amount(
        amounts, "owner contributions", "capital contributions", "share issuances",
    ) or Decimal(0)
    distributions = _find_financial_amount(
        amounts, "dividends", "owner distributions", "distributions",
    ) or Decimal(0)
    if beginning_equity is None or ending_equity is None or net_income is None:
        return []
    expected = (
        beginning_equity
        + net_income
        + abs(contributions)
        + (distributions if distributions < 0 else -distributions)
    )
    return _check_equation(
        entity, period, "Equity roll-forward", ending_equity, expected,
    )


def _collect_business_rules(spec: dict) -> list[str]:
    """Gather all business rules from entities and global rules."""
    rules: list[str] = list(spec.get("global_rules", []))
    for entity in spec.get("entities", []):
        for rule in entity.get("business_rules", []):
            rules.append(f"[{entity['name']}] {rule}")
    return rules


def _validate_business_rules(rules: list[str], data: dict, spec: dict) -> list[dict]:
    """Use the LLM to check whether generated data violates business rules."""
    if not rules:
        return []

    llm = get_llm()

    # Build a compact sample of the data (first 10 records per entity).
    sample: dict[str, list] = {}
    for name, records in data.items():
        sample[name] = records[:10]

    prompt = (
        "You are a data-quality auditor. Check if the following sample data "
        "violates any of the listed business rules.\n\n"
        f"Business rules:\n" + "\n".join(f"- {r}" for r in rules) + "\n\n"
        f"Data sample (first 10 records per entity):\n```json\n{json.dumps(sample, indent=2, default=str)}\n```\n\n"
        "Return a JSON array of issues found. Each issue: "
        '{"entity": "name", "error_type": "business_rule", "message": "description", "severity": "warning"}.\n'
        "If no issues, return an empty array: []\n"
        "Return ONLY the JSON array."
    )

    try:
        response = llm.invoke([
            SystemMessage(content="You are a data-quality auditor. Return only JSON."),
            HumanMessage(content=prompt),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw = "\n".join(lines).strip()
        issues = json.loads(raw)
        if isinstance(issues, list):
            return issues
    except Exception as exc:
        logger.warning("[Validation] Business-rule LLM check failed: %s", exc)

    return []
