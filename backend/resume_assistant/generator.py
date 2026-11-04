"""Deterministic resume generation from the resume knowledge base and blog docs.

The generator only publishes facts that exist in the knowledge base. Optional
sections that are not present are reported through ``missing`` instead of being
invented. Contact details are limited to the explicitly whitelisted public
links (``github`` and ``site``); phone numbers and private e-mail fields are
never emitted.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

from .models import (
    Link,
    Profile,
    Project,
    ResumeDocument,
    SkillGroup,
    SourceInfo,
    Writing,
    WritingSeries,
)

SERVICE_DIR = Path(__file__).resolve().parent
DEFAULT_KB_DIR = Path("/Users/mac/resume-kb")
DEFAULT_BLOG_DOCS_DIR = Path("/Users/mac/coding-log-web/docs")
DEFAULT_DATA_DIR = SERVICE_DIR / "data"
DEFAULT_TOKEN_FILE_NAME = ".refresh_token"

# Fixed order: it defines both the source hash and source.kb_files.
KB_FILES = (
    "profile.md",
    "skills.md",
    "projects.md",
    "experience.md",
    "education.md",
    "honors.md",
)
OPTIONAL_KB_FILES = {
    "experience.md": "工作经历",
    "education.md": "教育经历",
    "honors.md": "荣誉",
}
HASH_NAMESPACE = b"resume-assistant/source-hash/v1\n"
MAX_SERIES = 12
TZ_CST = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class Settings:
    kb_dir: Path
    blog_docs_dir: Path
    data_dir: Path
    refresh_token: Optional[str] = None
    token_file: Optional[Path] = None
    rate_limit_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "Settings":
        kb_dir = Path(os.environ.get("RESUME_KB_DIR", str(DEFAULT_KB_DIR))).expanduser()
        blog_docs_dir = Path(
            os.environ.get("BLOG_DOCS_DIR", str(DEFAULT_BLOG_DOCS_DIR))
        ).expanduser()
        data_dir = Path(
            os.environ.get("RESUME_DATA_DIR", str(DEFAULT_DATA_DIR))
        ).expanduser()
        token_file_env = os.environ.get("RESUME_TOKEN_FILE")
        token_file = (
            Path(token_file_env).expanduser()
            if token_file_env
            else kb_dir / DEFAULT_TOKEN_FILE_NAME
        )
        try:
            rate_limit = float(os.environ.get("RESUME_REFRESH_INTERVAL_SECONDS", "30"))
        except ValueError:
            rate_limit = 30.0
        return cls(
            kb_dir=kb_dir,
            blog_docs_dir=blog_docs_dir,
            data_dir=data_dir,
            refresh_token=os.environ.get("RESUME_REFRESH_TOKEN") or None,
            token_file=token_file,
            rate_limit_seconds=rate_limit,
        )

    @property
    def snapshot_path(self) -> Path:
        return self.data_dir / "resume.json"


# ---------------------------------------------------------------------------
# Small parsers
# ---------------------------------------------------------------------------

_FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _strip_bom(text: str) -> str:
    return text.lstrip("\ufeff")


def parse_profile(text: Optional[str]) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "name": "",
        "title": "",
        "summary": "",
        "github": "",
        "site": "",
        "directions": [],
    }
    if not text:
        return data

    current_list: Optional[str] = None
    for raw in _strip_bom(text).splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        if current_list == "directions" and stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                data["directions"].append(item)
            continue
        match = _FIELD_RE.match(stripped)
        if not match:
            current_list = None
            continue
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        current_list = None
        if key == "directions":
            if value:
                parsed = _parse_inline_list(value)
                data["directions"].extend(parsed)
            else:
                current_list = "directions"
        elif key in ("name", "title", "summary", "github", "site"):
            data[key] = value
    # Deduplicate while preserving order.
    data["directions"] = _dedupe(data["directions"])
    return data


def _parse_inline_list(value: str) -> List[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = yaml.safe_load(value)
        except yaml.YAMLError:
            parsed = None
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_skills(text: Optional[str]) -> List[SkillGroup]:
    groups: List[SkillGroup] = []
    if not text:
        return groups
    current: Optional[SkillGroup] = None
    for raw in _strip_bom(text).splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("## "):
            current = SkillGroup(group=stripped[3:].strip(), items=[])
            groups.append(current)
            continue
        if current is not None and stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                current.items.append(item)
    return [group for group in groups if group.group]


def parse_entries(text: Optional[str]) -> List[Project]:
    """Parse ``## name`` sections used by projects/experience/education."""
    entries: List[Project] = []
    if not text:
        return entries

    current: Optional[Dict[str, Any]] = None
    collecting: Optional[str] = None

    def flush() -> None:
        nonlocal current
        if current is not None and current.get("name"):
            entries.append(
                Project(
                    name=str(current.get("name", "")).strip(),
                    role=str(current.get("role", "")).strip(),
                    period=str(current.get("period", "")).strip(),
                    summary=str(current.get("summary", "")).strip(),
                    tech=_split_tech(current.get("tech", "")),
                    link=_clean_link(current.get("link")),
                    highlights=list(current.get("highlights", [])),
                )
            )
        current = None

    for raw in _strip_bom(text).splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("## "):
            flush()
            current = {"name": stripped[3:].strip(), "highlights": []}
            collecting = None
            continue
        if current is None:
            continue
        if collecting == "highlights" and stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                current["highlights"].append(item)
            continue
        match = _FIELD_RE.match(stripped)
        if not match:
            collecting = None
            continue
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        collecting = None
        if key == "highlights":
            if value:
                current["highlights"].extend(_parse_inline_list(value))
            else:
                collecting = "highlights"
        elif key in ("role", "period", "summary", "tech", "link"):
            current[key] = value
    flush()
    return entries


def parse_honors(text: Optional[str]) -> List[str]:
    honors: List[str] = []
    if not text:
        return honors
    for raw in _strip_bom(text).splitlines():
        stripped = raw.strip()
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                honors.append(item)
    return honors


def _split_tech(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    return [part.strip() for part in re.split(r"[,，]", str(value)) if part.strip()]


def _clean_link(value: Any) -> Optional[str]:
    if not value:
        return None
    link = str(value).strip()
    if not link:
        return None
    if link.startswith("http://") or link.startswith("https://") or link.startswith("/"):
        return link
    return None


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# Blog scan
# ---------------------------------------------------------------------------


def read_frontmatter(path: Path) -> Dict[str, Any]:
    text = _read_text(path)
    if text is None:
        return {}
    text = _strip_bom(text)
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return {}
    try:
        parsed = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


@dataclass(frozen=True)
class Article:
    path: str
    permalink: str
    title: str
    categories: Tuple[str, ...]


def scan_articles(docs_dir: Path) -> List[Article]:
    if not docs_dir.is_dir():
        return []
    articles: List[Article] = []
    for path in sorted(docs_dir.rglob("*.md")):
        meta = read_frontmatter(path)
        permalink = meta.get("permalink")
        if not isinstance(permalink, str) or not permalink.strip():
            continue
        title = meta.get("title")
        categories = meta.get("categories")
        if isinstance(categories, str):
            category_list = [categories]
        elif isinstance(categories, list):
            category_list = [str(item) for item in categories if str(item).strip()]
        else:
            category_list = []
        articles.append(
            Article(
                path=str(path.relative_to(docs_dir)),
                permalink=permalink.strip(),
                title=str(title).strip() if title is not None else "",
                categories=tuple(_dedupe(category_list)),
            )
        )
    return articles


def series_counts(articles: List[Article]) -> List[WritingSeries]:
    counter: Counter = Counter()
    for article in articles:
        for category in article.categories:
            counter[category] += 1
    ordered = sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:MAX_SERIES]
    return [WritingSeries(name=name, count=count) for name, count in ordered]


def _norm_link(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.strip().rstrip("/").lower()


def _norm_title(value: str) -> str:
    return re.sub(r"[\s\-_/]+", "", value).casefold()


def merge_doc_projects(
    kb_projects: List[Project], docs_dir: Path
) -> List[Project]:
    """Append blog project pages not already represented in the KB.

    Only title and permalink are taken; role/period/summary/highlights remain
    empty because the KB did not assert them.
    """
    project_dir = docs_dir / "08.项目"
    if not project_dir.is_dir():
        return list(kb_projects)

    kb_links = {_norm_link(project.link) for project in kb_projects if project.link}
    kb_titles = [_norm_title(project.name) for project in kb_projects]
    merged = list(kb_projects)
    for path in sorted(project_dir.glob("*.md")):
        meta = read_frontmatter(path)
        permalink = meta.get("permalink")
        if not isinstance(permalink, str) or not permalink.strip():
            continue
        title = meta.get("title")
        name = str(title).strip() if title is not None else path.stem
        if not name:
            name = path.stem
        norm_title = _norm_title(name)
        if _norm_link(permalink) in kb_links:
            continue
        if any(
            norm_title and (norm_title in known or known in norm_title)
            for known in kb_titles
            if known
        ):
            continue
        merged.append(
            Project(
                name=name,
                role="",
                period="",
                summary="",
                tech=[],
                link=permalink.strip(),
                highlights=[],
            )
        )
    return merged


# ---------------------------------------------------------------------------
# Hashing / generation / persistence
# ---------------------------------------------------------------------------

def compute_source_hash(kb_dir: Path, articles: List[Article]) -> str:
    digest = hashlib.sha256()
    digest.update(HASH_NAMESPACE)
    for name in KB_FILES:
        data = b""
        try:
            data = (kb_dir / name).read_bytes()
        except OSError:
            data = b""
        digest.update(b"FILE\x00" + name.encode("utf-8") + b"\x00")
        digest.update(str(len(data)).encode("ascii") + b"\x00")
        digest.update(data)
        digest.update(b"\x00")
    digest.update(b"PERMALINKS\x00")
    for permalink in sorted(article.permalink for article in articles):
        digest.update(permalink.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _now_cst() -> datetime:
    return datetime.now(TZ_CST)


def next_scheduled_at(now: Optional[datetime] = None) -> str:
    current = (now or _now_cst()).astimezone(TZ_CST)
    target = current.replace(day=1, hour=3, minute=10, second=0, microsecond=0)
    if current >= target:
        if current.month == 12:
            target = target.replace(year=target.year + 1, month=1)
        else:
            target = target.replace(month=target.month + 1)
    return target.isoformat()


def build_document(settings: Settings, generated_at: Optional[str] = None) -> ResumeDocument:
    kb_dir = settings.kb_dir
    texts = {name: _read_text(kb_dir / name) for name in KB_FILES}
    articles = scan_articles(settings.blog_docs_dir)

    profile_data = parse_profile(texts["profile.md"])
    links: List[Link] = []
    if profile_data["github"]:
        links.append(Link(label="GitHub", url=profile_data["github"]))
    if profile_data["site"]:
        links.append(Link(label="站点", url=profile_data["site"]))
    profile = Profile(
        name=profile_data["name"],
        title=profile_data["title"],
        summary=profile_data["summary"],
        links=links,
        directions=list(profile_data["directions"]),
    )

    skills = parse_skills(texts["skills.md"])
    kb_projects = parse_entries(texts["projects.md"])
    projects = merge_doc_projects(kb_projects, settings.blog_docs_dir)
    experience = parse_entries(texts["experience.md"])
    education = parse_entries(texts["education.md"])
    honors = parse_honors(texts["honors.md"])

    missing = [
        label
        for filename, label in OPTIONAL_KB_FILES.items()
        if texts.get(filename) is None
    ]

    kb_files = [name for name in KB_FILES if texts.get(name) is not None]
    source_hash = compute_source_hash(kb_dir, articles)
    writing = Writing(
        article_count=len(articles),
        series=series_counts(articles),
    )
    return ResumeDocument(
        generated_at=generated_at or _now_cst().isoformat(timespec="seconds"),
        source=SourceInfo(
            source_hash=source_hash,
            article_count=len(articles),
            kb_files=kb_files,
        ),
        profile=profile,
        skills=skills,
        projects=projects,
        experience=experience,
        education=education,
        honors=honors,
        writing=writing,
        missing=missing,
    )


def dumps_document(document: ResumeDocument) -> str:
    return json.dumps(document.model_dump(), ensure_ascii=False, indent=2) + "\n"


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix="." + path.name + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def write_snapshot(settings: Settings, document: ResumeDocument) -> Path:
    path = settings.snapshot_path
    atomic_write_text(path, dumps_document(document))
    return path


def load_snapshot(settings: Settings) -> Optional[ResumeDocument]:
    try:
        raw = settings.snapshot_path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None
    try:
        return ResumeDocument.model_validate_json(raw)
    except Exception:
        return None
