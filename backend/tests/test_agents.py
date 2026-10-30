"""
Unit tests for specialized agents and validation logic.
"""

from types import SimpleNamespace

from app.agents.exploration_agent import exploration_node
from app.agents.planning_agent import _build_fallback_plan
from app.agents.validation_agent import (
    _check_constraints,
    _check_type,
    _check_referential_integrity,
    _validate_financial_consistency,
)


def test_exploration_agent_returns_structured_scenario_context(monkeypatch):
    brief = {
        "domain": "corporate finance",
        "scenario": "A fictional company reporting annual results.",
        "assumptions": ["USD reporting currency"],
        "realism_rules": ["Revenue should be supported by operating drivers."],
        "relationships": ["Net income rolls into retained earnings."],
        "accounting_checks": ["Assets equal liabilities plus equity."],
    }

    class FakeLLM:
        def invoke(self, messages):
            import json

            return SimpleNamespace(content=json.dumps(brief))

    monkeypatch.setattr("app.agents.exploration_agent.get_llm", lambda: FakeLLM())
    result = exploration_node({"job_id": "test", "user_prompt": "Create annual financial statements"})

    assert result["scenario_context"] == brief
    assert result["current_agent"] == "exploration"


def test_fallback_plan_generation():
    spec = {
        "entities": [
            {
                "name": "departments",
                "record_count": 10,
                "fields": [{"name": "id", "data_type": "string"}]
            },
            {
                "name": "employees",
                "record_count": 100,
                "relationships": [
                    {"from_entity": "employees", "from_field": "dept_id", "to_entity": "departments", "to_field": "id"}
                ]
            }
        ]
    }
    plan = _build_fallback_plan(spec)
    assert plan["entity_order"] == ["departments", "employees"]
    assert len(plan["strategies"]) == 2
    assert plan["strategies"][1]["dependencies"] == ["departments"]


def test_type_validator():
    # Valid
    assert _check_type("test@example.com", "email", "email", "users", 0) is None
    assert _check_type(42, "integer", "age", "users", 0) is None
    assert _check_type(19.99, "float", "price", "products", 0) is None
    assert _check_type("2024-01-15", "date", "created_at", "orders", 0) is None

    # Invalid
    err = _check_type("not_an_int", "integer", "age", "users", 0)
    assert err is not None
    assert err["error_type"] == "type_mismatch"


def test_constraint_validator():
    field = {
        "name": "age",
        "data_type": "integer",
        "constraints": {"min": 18, "max": 65}
    }
    # In range
    assert len(_check_constraints(25, field, "users", 0)) == 0

    # Below min
    errors = _check_constraints(16, field, "users", 0)
    assert len(errors) == 1
    assert "value 16 < min 18" in errors[0]["message"]

    # Enum constraint
    status_field = {
        "name": "status",
        "data_type": "enum",
        "constraints": {"enum_values": ["active", "inactive", "pending"]}
    }
    assert len(_check_constraints("active", status_field, "users", 0)) == 0
    errs = _check_constraints("unknown", status_field, "users", 0)
    assert len(errs) == 1
    assert "not in enum" in errs[0]["message"]


def test_referential_integrity_check():
    rel = {
        "from_entity": "orders",
        "from_field": "customer_id",
        "to_entity": "customers",
        "to_field": "id"
    }
    data = {
        "customers": [{"id": "C1"}, {"id": "C2"}],
        "orders": [
            {"order_id": "O1", "customer_id": "C1"},
            {"order_id": "O2", "customer_id": "C999"}  # Invalid FK
        ]
    }
    errors = _check_referential_integrity(rel, data)
    assert len(errors) == 1
    assert errors[0]["error_type"] == "referential_integrity"
    assert "C999" in errors[0]["message"]


def test_financial_validation_accepts_balanced_balance_sheet():
    data = {
        "BalanceSheet": [
            {"period": "FY2025", "line_item": "Total Assets", "amount": 1500},
            {"period": "FY2025", "line_item": "Total Liabilities", "amount": 900},
            {"period": "FY2025", "line_item": "Total Equity", "amount": 600},
        ]
    }

    assert _validate_financial_consistency(data) == []


def test_financial_validation_reports_unbalanced_balance_sheet():
    data = {
        "BalanceSheet": [
            {"period": "FY2025", "line_item": "Total Assets", "amount": 1500},
            {"period": "FY2025", "line_item": "Total Liabilities", "amount": 900},
            {"period": "FY2025", "line_item": "Total Equity", "amount": 550},
        ]
    }

    errors = _validate_financial_consistency(data)
    assert len(errors) == 1
    assert errors[0]["error_type"] == "accounting_reconciliation"
    assert "assets = liabilities + equity" in errors[0]["message"]


def test_financial_validation_checks_income_statement_subtotals():
    data = {
        "StatementOfIncome": [
            {"period": "FY2025", "line_item": "Revenue", "amount": 1000},
            {"period": "FY2025", "line_item": "Cost of Goods Sold", "amount": 400},
            {"period": "FY2025", "line_item": "Gross Profit", "amount": 600},
            {"period": "FY2025", "line_item": "Operating Expenses", "amount": 200},
            {"period": "FY2025", "line_item": "Operating Income", "amount": 400},
            {"period": "FY2025", "line_item": "Income Tax Expense", "amount": 100},
            {"period": "FY2025", "line_item": "Net Income", "amount": 300},
        ]
    }

    assert _validate_financial_consistency(data) == []


def test_financial_validation_detects_incorrect_net_income():
    data = {
        "StatementOfIncome": [
            {"period": "FY2025", "line_item": "Operating Income", "amount": 400},
            {"period": "FY2025", "line_item": "Income Tax Expense", "amount": 100},
            {"period": "FY2025", "line_item": "Net Income", "amount": 350},
        ]
    }

    errors = _validate_financial_consistency(data)
    assert len(errors) == 1
    assert "Net income" in errors[0]["message"]


def test_financial_validation_reconciles_cash_flow_and_equity_roll_forward():
    data = {
        "CashFlowStatement": [
            {"period": "FY2025", "line_item": "Beginning Cash", "amount": 100},
            {"period": "FY2025", "line_item": "Net Change in Cash", "amount": -15},
            {"period": "FY2025", "line_item": "Ending Cash", "amount": 85},
        ],
        "StatementOfChangesInEquity": [
            {"period": "FY2025", "line_item": "Beginning Equity", "amount": 500},
            {"period": "FY2025", "line_item": "Net Income", "amount": 100},
            {"period": "FY2025", "line_item": "Dividends", "amount": -25},
            {"period": "FY2025", "line_item": "Ending Equity", "amount": 575},
        ],
    }

    assert _validate_financial_consistency(data) == []
