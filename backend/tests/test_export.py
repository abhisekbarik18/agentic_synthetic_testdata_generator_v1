"""
Unit tests for Export Agent, multi-format outputs, and SQL sanitization.
"""

from pathlib import Path
import pandas as pd
import pytest

from app.agents.export_agent import (
    _export_entity,
    _to_csv,
    _to_docx,
    _to_html,
    _is_financial_statement,
    _build_financial_pdf_story,
    _to_json,
    _to_markdown,
    _to_parquet,
    _to_pdf,
    _to_sql,
    _to_xlsx,
    _to_xml,
)
from app.utils.security import sanitise_sql_value, validate_sql_safety, check_export_file_size, safe_filename


@pytest.fixture
def sample_df():
    return pd.DataFrame([
        {"id": 1, "name": "Alice Smith", "email": "alice@example.com", "active": True, "score": 95.5},
        {"id": 2, "name": "Bob O'Connor", "email": "bob@example.com", "active": False, "score": 88.0},
        {"id": 3, "name": "Carol Danvers", "email": "carol@example.com", "active": True, "score": 99.2},
    ])


@pytest.fixture
def temp_export_dir(tmp_path):
    out = tmp_path / "exports"
    out.mkdir()
    return out


def test_export_csv(sample_df, temp_export_dir):
    info = _to_csv(sample_df, "users", temp_export_dir, "users")
    assert info["format"] == "csv"
    assert info["record_count"] == 3
    assert Path(info["path"]).exists()
    loaded = pd.read_csv(info["path"])
    assert len(loaded) == 3
    assert "Bob O'Connor" in loaded["name"].values


def test_export_json(sample_df, temp_export_dir):
    info = _to_json(sample_df, "users", temp_export_dir, "users")
    assert info["format"] == "json"
    assert info["record_count"] == 3
    assert Path(info["path"]).exists()


def test_export_entity_uses_a_timestamped_versioned_filename(sample_df, temp_export_dir):
    info = _export_entity(sample_df, "users", "csv", temp_export_dir, "users")

    assert info["format"] == "csv"
    assert info["filename"].startswith("users_")
    assert info["filename"].endswith(".csv")
    assert info["entity_name"] == "users"
    assert info["created_at"]
    assert Path(info["path"]).exists()


def test_export_xlsx(sample_df, temp_export_dir):
    info = _to_xlsx(sample_df, "users", temp_export_dir, "users")
    assert info["format"] == "xlsx"
    assert info["record_count"] == 3
    assert Path(info["path"]).exists()


def test_export_xml(sample_df, temp_export_dir):
    info = _to_xml(sample_df, "users", temp_export_dir, "users")
    assert info["format"] == "xml"
    assert info["record_count"] == 3
    content = Path(info["path"]).read_text(encoding="utf-8")
    assert "<dataset entity=\"users\">" in content
    assert "<record>" in content


def test_export_sql(sample_df, temp_export_dir):
    info = _to_sql(sample_df, "users", temp_export_dir, "users")
    assert info["format"] == "sql"
    assert info["record_count"] == 3
    content = Path(info["path"]).read_text(encoding="utf-8")
    assert "INSERT INTO \"users\"" in content
    assert "Bob O''Connor" in content  # Escaped single quote


def test_export_parquet(sample_df, temp_export_dir):
    info = _to_parquet(sample_df, "users", temp_export_dir, "users")
    assert info["format"] == "parquet"
    assert info["record_count"] == 3
    assert Path(info["path"]).exists()


def test_export_pdf(sample_df, temp_export_dir):
    info = _to_pdf(sample_df, "income_statement", temp_export_dir, "Statement of Income")
    assert info["format"] == "pdf"
    assert info["record_count"] == 3
    content = Path(info["path"]).read_bytes()
    assert content.startswith(b"%PDF")
    assert b"Statement of Income" in content


def test_financial_statement_pdf_recognizes_dynamic_line_item_data(temp_export_dir):
    financial_df = pd.DataFrame([
        {
            "period": "FY2025",
            "statement_section": "Revenue",
            "line_item": "Net sales",
            "amount": 1250000,
            "currency": "USD",
        },
        {
            "period": "FY2024",
            "statement_section": "Revenue",
            "line_item": "Net sales",
            "amount": 1100000,
            "currency": "USD",
        },
    ])

    assert _is_financial_statement(financial_df)
    info = _to_pdf(financial_df, "statement_of_income", temp_export_dir, "Statement of Income")
    assert info["format"] == "pdf"
    assert info["record_count"] == 2
    assert Path(info["path"]).read_bytes().startswith(b"%PDF")


def test_financial_pdf_layout_uses_statement_periods_and_amounts():
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    financial_df = pd.DataFrame([
        {
            "period": "FY2025",
            "statement_section": "Revenue",
            "line_item": "Net sales",
            "amount": 1250000,
            "currency": "USD",
        },
        {
            "period": "FY2024",
            "statement_section": "Revenue",
            "line_item": "Net sales",
            "amount": 1100000,
            "currency": "USD",
        },
    ])
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle("TestHeader", parent=styles["Normal"])
    story = _build_financial_pdf_story(
        financial_df,
        "Statement of Income",
        styles,
        header_style,
        styles["Normal"],
    )
    table_content = [
        cell.getPlainText() if hasattr(cell, "getPlainText") else str(cell)
        for row in story[-1]._cellvalues
        for cell in row
    ]

    assert "FY2025" in table_content
    assert "FY2024" in table_content
    assert "Net sales" in table_content
    assert "USD 1,250,000.00" in table_content
    assert "USD 1,100,000.00" in table_content


def test_export_html_escapes_values(sample_df, temp_export_dir):
    sample_df.loc[0, "name"] = "<script>alert(1)</script>"
    info = _to_html(sample_df, "users", temp_export_dir, "users")
    content = Path(info["path"]).read_text(encoding="utf-8")
    assert info["format"] == "html"
    assert "&lt;script&gt;" in content
    assert "<script>alert(1)</script>" not in content


def test_export_markdown_escapes_table_pipes(sample_df, temp_export_dir):
    sample_df.loc[0, "name"] = "Alice | Smith"
    info = _to_markdown(sample_df, "users", temp_export_dir, "users")
    content = Path(info["path"]).read_text(encoding="utf-8")
    assert info["format"] == "markdown"
    assert "Alice \\| Smith" in content


def test_export_docx(sample_df, temp_export_dir):
    info = _to_docx(sample_df, "income_statement", temp_export_dir, "Statement of Income")
    assert info["format"] == "docx"
    assert info["record_count"] == 3
    assert Path(info["path"]).read_bytes().startswith(b"PK")


def test_sql_safety_guard():
    # Valid INSERT
    assert validate_sql_safety("INSERT INTO users (id, name) VALUES (1, 'Alice');") is True
    # Dangerous statements should be flagged
    assert validate_sql_safety("INSERT INTO users VALUES (1); DROP TABLE users;") is False
    assert validate_sql_safety("INSERT INTO users VALUES (1); TRUNCATE TABLE users;") is False


def test_safe_filename():
    assert safe_filename("../../etc/passwd.csv") == "etc_passwd.csv"
    assert safe_filename("customer_data!@#$.json") == "customer_data____.json"
