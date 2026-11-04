from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from resume_assistant.app import create_app  # noqa: E402
from resume_assistant.generator import Settings  # noqa: E402


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


PROFILE = """# 基本信息
name: 三木先生
title: 软件工程师
summary: 关注软件工程、自动化测试与 AI 工程实践。
github: https://github.com/pyeden
site: https://seres-ai.com
directions:
  - 软件工程
  - 自动化测试技术
  - AI 技术
"""

SKILLS = """## 编程语言
- Go
- Python

## 后端与数据
- FastAPI
- MySQL
"""

PROJECTS = """## PanguVerse
role: 作者
period: 2026
summary: 原子编排平台。
tech: Python, FastAPI, Vue
link: https://seres-ai.com/panguverse/
highlights:
- 原子库与运行历史

## 智能旅行助手
role: 作者
period: 2026
summary: 生成逐日行程。
tech: FastAPI, Vue, AMap
link: https://seres-ai.com/projects/travel/
highlights:
- 天气与附近推荐
"""


def make_workspace(tmp_path: Path, docs: bool = True) -> Path:
    kb = tmp_path / "kb"
    write(kb / "profile.md", PROFILE)
    write(kb / "skills.md", SKILLS)
    write(kb / "projects.md", PROJECTS)
    if docs:
        docs_dir = tmp_path / "blog-docs"
        write(
            docs_dir / "07.AI技术" / "01.one.md",
            "---\ntitle: One\npermalink: /pages/one/\ncategories:\n  - AI技术\n---\n# One\n",
        )
        write(
            docs_dir / "07.AI技术" / "02.two.md",
            "---\ntitle: Two\npermalink: /pages/two/\ncategories:\n  - AI技术\n  - 工程实践\n---\n# Two\n",
        )
        write(
            docs_dir / "09.编程" / "03.three.md",
            "---\ntitle: Three\npermalink: /pages/three/\ncategories:\n  - 编程\n---\n# Three\n",
        )
        write(
            docs_dir / "08.项目" / "01.旅行助手.md",
            "---\ntitle: 旅行助手\npermalink: /projects/travel/\n---\n# 旅行助手\n",
        )
        write(
            docs_dir / "08.项目" / "02.新项目.md",
            "---\ntitle: 新项目\npermalink: /projects/new/\n---\n# 新项目\n",
        )
    return tmp_path


def make_settings(tmp_path: Path, token: str | None = "secret", rate_limit: float = 30.0) -> Settings:
    return Settings(
        kb_dir=tmp_path / "kb",
        blog_docs_dir=tmp_path / "blog-docs",
        data_dir=tmp_path / "data",
        refresh_token=token,
        token_file=None,
        rate_limit_seconds=rate_limit,
    )


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return make_workspace(tmp_path)


@pytest.fixture
def client(workspace: Path):
    application = create_app(make_settings(workspace))
    from fastapi.testclient import TestClient

    with TestClient(application) as test_client:
        yield test_client, application
