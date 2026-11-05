from __future__ import annotations

import re
from pathlib import Path

from conftest import make_settings, write
from resume_assistant.generator import (
    build_document,
    compute_source_hash,
    dumps_document,
    load_snapshot,
    scan_articles,
    series_counts,
)

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")


def test_schema_and_missing_sections(workspace: Path) -> None:
    document = build_document(make_settings(workspace))
    payload = document.model_dump()

    assert payload["schema_version"] == "1.1"
    assert payload["profile"]["name"] == "三木先生"
    assert "软件工程" in payload["profile"]["directions"]
    assert len(payload["skills"]) >= 2
    assert len(payload["projects"]) >= 2
    assert payload["experience"] == []
    assert payload["education"] == []
    assert "工作经历" in payload["missing"]
    assert "教育经历" in payload["missing"]
    assert "荣誉" in payload["missing"]
    assert payload["source"]["article_count"] == 5
    assert re.fullmatch(r"[0-9a-f]{64}", payload["source"]["source_hash"])


def test_optional_sections_are_parsed_not_missing(workspace: Path) -> None:
    write(
        workspace / "kb" / "experience.md",
        "## 某公司\nrole: 工程师\nperiod: 2020–2022\nsummary: 测试经历\nhighlights:\n- 做了测试\n",
    )
    write(
        workspace / "kb" / "education.md",
        "## 某大学\nrole: 学生\nperiod: 2016–2020\nsummary: 本科\n",
    )
    write(workspace / "kb" / "honors.md", "- 某奖项\n")
    document = build_document(make_settings(workspace))

    assert document.experience[0].name == "某公司"
    assert document.experience[0].highlights == ["做了测试"]
    assert document.education[0].name == "某大学"
    assert document.honors == ["某奖项"]
    assert document.missing == []


def test_missing_kb_files_do_not_raise(workspace: Path) -> None:
    settings = make_settings(workspace)
    settings = settings.__class__(**{**settings.__dict__, "kb_dir": workspace / "no-such-kb"})
    document = build_document(settings)
    assert document.profile.name == ""
    assert document.skills == []
    assert "工作经历" in document.missing


def test_deterministic_hash_and_payload(workspace: Path) -> None:
    settings = make_settings(workspace)
    first = build_document(settings, generated_at="2026-11-04T10:45:00+08:00")
    second = build_document(settings, generated_at="2026-11-04T10:45:00+08:00")

    assert first.source.source_hash == second.source.source_hash
    assert dumps_document(first) == dumps_document(second)

    write(workspace / "kb" / "skills.md", (workspace / "kb" / "skills.md").read_text() + "- Rust\n")
    third = build_document(settings, generated_at="2026-11-04T10:45:00+08:00")
    assert third.source.source_hash != first.source.source_hash


def test_source_hash_covers_permalinks(workspace: Path) -> None:
    settings = make_settings(workspace)
    before = compute_source_hash(settings.kb_dir, scan_articles(settings.blog_docs_dir))
    write(
        workspace / "blog-docs" / "07.AI技术" / "04.four.md",
        "---\ntitle: Four\npermalink: /pages/four/\n---\n",
    )
    after = compute_source_hash(settings.kb_dir, scan_articles(settings.blog_docs_dir))
    assert before != after


def test_writing_stats_and_doc_project_merge(workspace: Path) -> None:
    settings = make_settings(workspace)
    document = build_document(settings)

    assert document.writing.article_count == 5
    assert document.writing.series[0].name == "AI技术"
    assert document.writing.series[0].count == 2
    names = [project.name for project in document.projects]
    assert "新项目" in names
    assert "旅行助手" not in names  # already covered by the KB project
    merged = next(project for project in document.projects if project.name == "新项目")
    assert merged.link == "/projects/new/"
    assert merged.summary == ""
    assert merged.role == ""
    assert merged.highlights == []


def test_no_private_contact_details(workspace: Path) -> None:
    write(
        workspace / "kb" / "profile.md",
        (workspace / "kb" / "profile.md").read_text()
        + "email: private@example.com\nphone: 13800138000\n",
    )
    document = build_document(make_settings(workspace))
    text = dumps_document(document)
    assert not EMAIL_RE.search(text)
    assert not PHONE_RE.search(text)
    assert [link.label for link in document.profile.links] == ["GitHub", "站点"]


def test_snapshot_roundtrip(workspace: Path) -> None:
    from resume_assistant.generator import write_snapshot

    settings = make_settings(workspace)
    document = build_document(settings, generated_at="2026-11-04T10:45:00+08:00")
    write_snapshot(settings, document)
    loaded = load_snapshot(settings)
    assert loaded is not None
    assert dumps_document(loaded) == dumps_document(document)
