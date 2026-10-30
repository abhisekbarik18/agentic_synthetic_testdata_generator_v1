"""
Integration tests for FastAPI endpoints.
"""

from unittest.mock import patch
from app.models.db_models import Job


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "llm_provider" in data


def test_list_jobs_empty(client):
    response = client.get("/api/jobs")
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert "total" in data


def test_create_generation_job(client):
    with patch("app.services.generation_service._run_pipeline_thread"):
        payload = {
            "prompt": "Generate 10 synthetic employee records with id, name, and email fields.",
            "formats": ["csv", "json"]
        }
        response = client.post("/api/generate", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert "csv" in data["formats"]


def test_create_generation_job_accepts_document_formats(client):
    with patch("app.services.generation_service._run_pipeline_thread"):
        payload = {
            "prompt": "Generate a synthetic statement of income with revenue and expenses.",
            "formats": ["pdf", "html", "markdown", "docx"]
        }
        response = client.post("/api/generate", json=payload)
        assert response.status_code == 202
        assert response.json()["formats"] == ["pdf", "html", "markdown", "docx"]


def test_get_job_data_and_preview(client, db_session):
    job = Job(
        id="test-job-123",
        prompt="Generate customers",
        status="completed",
        requested_formats=["json"],
        generated_data={
            "customers": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"}
            ]
        },
        record_count=2,
    )
    db_session.add(job)
    db_session.commit()

    # Get job status
    resp = client.get("/api/jobs/test-job-123")
    assert resp.status_code == 200
    assert resp.json()["job_id"] == "test-job-123"

    # Get preview data
    resp_data = client.get("/api/jobs/test-job-123/data")
    assert resp_data.status_code == 200
    preview = resp_data.json()
    assert "customers" in preview["entities"]
    assert len(preview["entities"]["customers"]) == 2


def test_followup_export_uses_formats_from_instruction(client, db_session):
    job = Job(
        id="followup-export-job",
        prompt="Generate customer records",
        status="completed",
        requested_formats=["csv"],
        generated_data={"customers": [{"id": 1}]},
    )
    db_session.add(job)
    db_session.commit()

    with patch("app.api.routes.export_job_data", return_value=[]) as export:
        response = client.post(
            "/api/jobs/followup-export-job/followup",
            json={"prompt": "Please convert this dataset to Parquet and SQL", "regenerate": False},
        )

    assert response.status_code == 202
    assert export.call_args.args[2] == ["parquet", "sql"]


def test_followup_export_reports_unrecognized_instruction(client, db_session):
    job = Job(
        id="followup-invalid-job",
        prompt="Generate customer records",
        status="completed",
        requested_formats=["csv"],
        generated_data={"customers": [{"id": 1}]},
    )
    db_session.add(job)
    db_session.commit()

    response = client.post(
        "/api/jobs/followup-invalid-job/followup",
        json={"prompt": "Add a phone number field", "regenerate": False},
    )

    assert response.status_code == 400
    assert "Regenerate Records" in response.json()["detail"]


def test_regenerating_followup_includes_formats_mentioned_in_instruction(client, db_session):
    original = Job(
        id="followup-regenerate-job",
        prompt="Generate customer records",
        status="completed",
        requested_formats=["csv"],
        generated_data={"customers": [{"id": 1}]},
    )
    db_session.add(original)
    db_session.commit()

    def create_job(prompt, formats, db):
        assert "Add a phone_number field" in prompt
        assert formats == ["csv", "xlsx"]
        job = Job(
            id="followup-regenerated-result",
            prompt=prompt,
            status="pending",
            requested_formats=formats,
        )
        db.add(job)
        db.commit()
        return job.id

    with patch("app.api.routes.start_generation", side_effect=create_job):
        response = client.post(
            "/api/jobs/followup-regenerate-job/followup",
            json={"prompt": "Add a phone_number field and export to Excel", "regenerate": True},
        )

    assert response.status_code == 202
    assert response.json()["formats"] == ["csv", "xlsx"]


def test_additional_exports_are_versioned_and_return_latest_metadata(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.export_service.settings.EXPORT_DIR", str(tmp_path))
    job = Job(
        id="versioned-export-job",
        prompt="Generate customer records",
        status="completed",
        requested_formats=["csv"],
        generated_data={"customers": [{"id": 1, "name": "Ada"}]},
    )
    db_session.add(job)
    db_session.commit()

    first = client.post(
        "/api/jobs/versioned-export-job/export",
        json={"formats": ["csv"]},
    )
    second = client.post(
        "/api/jobs/versioned-export-job/export",
        json={"formats": ["csv"]},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_file = first.json()["files"][0]
    second_file = second.json()["files"][0]
    assert first_file["filename"] != second_file["filename"]
    assert first_file["entity_name"] == second_file["entity_name"] == "customers"
    assert first_file["created_at"] and second_file["created_at"]
    assert first_file["filename"].startswith("customers_")
    assert (tmp_path / "versioned-export-job" / first_file["filename"]).exists()
    assert (tmp_path / "versioned-export-job" / second_file["filename"]).exists()
    download = client.get(
        f"/api/jobs/versioned-export-job/export/{second_file['filename']}"
    )
    assert download.status_code == 200
    assert "Ada" in download.text

    job_response = client.get("/api/jobs/versioned-export-job")
    assert job_response.status_code == 200
    assert len(job_response.json()["export_files"]) == 2
    assert "csv" in job_response.json()["formats"]
