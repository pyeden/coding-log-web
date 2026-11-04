from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import make_settings, write
from resume_assistant.app import create_app


def test_health(client) -> None:
    test_client, _ = client
    response = test_client.get("/api/resume/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "resume-assistant",
        "version": "1.0.0",
    }


def test_latest_generates_and_sets_no_store(client) -> None:
    test_client, _ = client
    response = test_client.get("/api/resume/latest")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload["schema_version"] == "1.0"
    assert payload["profile"]["name"] == "三木先生"
    assert payload["experience"] == []
    assert payload["education"] == []
    assert "工作经历" in payload["missing"]
    assert "教育经历" in payload["missing"]


def test_refresh_requires_token(client) -> None:
    test_client, _ = client
    assert test_client.post("/api/resume/refresh").status_code == 401
    wrong = test_client.post(
        "/api/resume/refresh", headers={"X-Resume-Token": "nope"}
    )
    assert wrong.status_code == 401
    assert wrong.json() == {"detail": "unauthorized"}


def test_refresh_with_token_changes_generated_at(client) -> None:
    test_client, _ = client
    first = test_client.get("/api/resume/latest").json()
    response = test_client.post(
        "/api/resume/refresh", headers={"X-Resume-Token": "secret"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["changed"] is False
    assert len(body["source_hash"]) == 64

    second = test_client.get("/api/resume/latest").json()
    assert second["generated_at"] != first["generated_at"]


def test_refresh_rate_limit_30_seconds(client) -> None:
    test_client, application = client
    headers = {"X-Resume-Token": "secret"}
    first = test_client.post("/api/resume/refresh", headers=headers)
    assert first.status_code == 200
    second = test_client.post("/api/resume/refresh", headers=headers)
    assert second.status_code == 429
    assert second.json() == {"detail": "too_frequent"}

    application.state.last_refresh_at = time.monotonic() - 31
    third = test_client.post("/api/resume/refresh", headers=headers)
    assert third.status_code == 200


def test_refresh_reflects_new_skill(workspace: Path) -> None:
    application = create_app(make_settings(workspace))
    headers = {"X-Resume-Token": "secret"}
    with TestClient(application) as test_client:
        before = test_client.get("/api/resume/latest").json()
        assert all("Rust" not in group["items"] for group in before["skills"])

        skills_path = workspace / "kb" / "skills.md"
        write(skills_path, skills_path.read_text(encoding="utf-8") + "- Rust\n")
        response = test_client.post("/api/resume/refresh", headers=headers)
        assert response.status_code == 200
        assert response.json()["changed"] is True

        after = test_client.get("/api/resume/latest").json()
        assert any("Rust" in group["items"] for group in after["skills"])

        write(skills_path, skills_path.read_text(encoding="utf-8").replace("- Rust\n", ""))
        application.state.last_refresh_at = None
        assert test_client.post("/api/resume/refresh", headers=headers).status_code == 200
        restored = test_client.get("/api/resume/latest").json()
        assert all("Rust" not in group["items"] for group in restored["skills"])


def test_status_contract(client) -> None:
    test_client, _ = client
    response = test_client.get("/api/resume/status")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "generated_at",
        "source_hash",
        "article_count",
        "kb_files",
        "missing",
        "next_scheduled_at",
    }
    assert payload["article_count"] == 5
    assert payload["kb_files"] == ["profile.md", "skills.md", "projects.md"]
    assert "T" in payload["next_scheduled_at"]


def test_refresh_failure_keeps_previous_snapshot(workspace: Path, monkeypatch) -> None:
    application = create_app(make_settings(workspace))
    headers = {"X-Resume-Token": "secret"}
    with TestClient(application) as test_client:
        assert test_client.post("/api/resume/refresh", headers=headers).status_code == 200
        snapshot = application.state.settings.snapshot_path
        previous = snapshot.read_bytes()

        def boom(*args, **kwargs):
            raise RuntimeError("kb exploded")

        monkeypatch.setattr("resume_assistant.app.build_document", boom)
        application.state.last_refresh_at = None
        response = test_client.post("/api/resume/refresh", headers=headers)
        assert response.status_code == 500
        assert response.json()["detail"] == "generation_failed"
        assert "kb exploded" in response.json()["reason"]
        assert snapshot.read_bytes() == previous


def test_token_from_file(workspace: Path) -> None:
    settings = make_settings(workspace, token=None)
    token_file = workspace / "kb" / ".refresh_token"
    write(token_file, "file-secret\n")
    settings = settings.__class__(
        kb_dir=settings.kb_dir,
        blog_docs_dir=settings.blog_docs_dir,
        data_dir=settings.data_dir,
        refresh_token=None,
        token_file=token_file,
        rate_limit_seconds=0,
    )
    with TestClient(create_app(settings)) as test_client:
        assert (
            test_client.post(
                "/api/resume/refresh", headers={"X-Resume-Token": "file-secret"}
            ).status_code
            == 200
        )


def test_cors_allows_public_site(client) -> None:
    test_client, _ = client
    response = test_client.options(
        "/api/resume/latest",
        headers={
            "Origin": "https://seres-ai.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://seres-ai.com"
