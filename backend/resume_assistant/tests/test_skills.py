from __future__ import annotations

import json
from pathlib import Path

from conftest import make_settings, write
from resume_assistant.generator import build_document, load_snapshot, parse_skills
from resume_assistant.models import ResumeDocument, SkillGroup


def test_parse_skills_with_levels() -> None:
    groups = parse_skills(
        "## 编程语言\n- Python | 95\n- Go | 80\n- TypeScript / JavaScript | 75\n"
    )
    assert len(groups) == 1
    assert groups[0].items == ["Python", "Go", "TypeScript / JavaScript"]
    assert groups[0].levels == [95, 80, 75]


def test_parse_skills_without_levels_defaults_to_zero() -> None:
    groups = parse_skills("## 后端与数据\n- FastAPI\n- MySQL（含 Binlog 双向同步）\n")
    assert groups[0].items == ["FastAPI", "MySQL（含 Binlog 双向同步）"]
    assert groups[0].levels == [0, 0]


def test_parse_skills_invalid_level_keeps_whole_line_as_name() -> None:
    groups = parse_skills(
        "## 车载与总线\n"
        "- CAN | 101\n"
        "- LIN | abc\n"
        "- Modbus | 70\n"
        "- UDS | -5\n"
        "- A | 1 2\n"
    )
    assert groups[0].items == ["CAN | 101", "LIN | abc", "Modbus", "UDS | -5", "A | 1 2"]
    assert groups[0].levels == [0, 0, 70, 0, 0]


def test_parse_skills_name_whitespace_and_boundaries() -> None:
    groups = parse_skills("## G\n-   Python   |   95  \n- Zero | 0\n- Hundred | 100\n")
    assert groups[0].items == ["Python", "Zero", "Hundred"]
    assert groups[0].levels == [95, 0, 100]


def test_parse_skills_rsplit_keeps_pipe_in_name() -> None:
    groups = parse_skills("## G\n- a|b | 60\n")
    assert groups[0].items == ["a|b"]
    assert groups[0].levels == [60]


def test_build_document_levels_align_with_items(workspace: Path) -> None:
    write(
        workspace / "kb" / "skills.md",
        "## 编程语言\n- Python | 95\n- Go | 80\n\n## 平台与框架\n- Django | 92\n- 无分值条目\n",
    )
    document = build_document(make_settings(workspace))

    assert [group.group for group in document.skills] == ["编程语言", "平台与框架"]
    assert document.skills[0].items == ["Python", "Go"]
    assert document.skills[0].levels == [95, 80]
    assert document.skills[1].items == ["Django", "无分值条目"]
    assert document.skills[1].levels == [92, 0]
    for group in document.skills:
        assert len(group.items) == len(group.levels)


def test_alignment_pads_short_levels(tmp_path: Path) -> None:
    """Defensive: a partially filled group is padded with 0 at build time."""
    from resume_assistant.generator import _normalize_skill_group

    group = _normalize_skill_group(SkillGroup(group="G", items=["a", "b", "c"], levels=[50]))
    assert group.levels == [50, 0, 0]
    group = _normalize_skill_group(SkillGroup(group="G", items=["a"], levels=[50, 60]))
    assert group.levels == [50]


def test_old_snapshot_without_levels_still_loads(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    payload = {
        "schema_version": "1.0",
        "generated_at": "2026-11-04T10:45:00+08:00",
        "source": {"source_hash": "0" * 64},
        "skills": [{"group": "编程语言", "items": ["Python", "Go"]}],
    }
    (data_dir / "resume.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    settings = make_settings(tmp_path)
    settings = settings.__class__(
        kb_dir=settings.kb_dir,
        blog_docs_dir=settings.blog_docs_dir,
        data_dir=data_dir,
        refresh_token=settings.refresh_token,
        token_file=None,
        rate_limit_seconds=0,
    )

    loaded = load_snapshot(settings)
    assert loaded is not None
    assert loaded.skills[0].items == ["Python", "Go"]
    assert loaded.skills[0].levels == []
    assert loaded.schema_version == "1.0"


def test_snapshot_keeps_levels(workspace: Path) -> None:
    from resume_assistant.generator import write_snapshot

    write(workspace / "kb" / "skills.md", "## 编程语言\n- Python | 95\n")
    settings = make_settings(workspace)
    document = build_document(settings, generated_at="2026-11-05T09:00:00+08:00")
    write_snapshot(settings, document)

    loaded = load_snapshot(settings)
    assert loaded is not None
    assert loaded.skills == [SkillGroup(group="编程语言", items=["Python"], levels=[95])]
    assert ResumeDocument.model_validate_json(
        settings.snapshot_path.read_text(encoding="utf-8")
    ).skills[0].levels == [95]
