"""Response models for the public resume document (schema 1.1)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.1"


class Link(BaseModel):
    label: str
    url: str


class Profile(BaseModel):
    name: str = ""
    title: str = ""
    summary: str = ""
    links: List[Link] = Field(default_factory=list)
    directions: List[str] = Field(default_factory=list)


class SkillGroup(BaseModel):
    group: str
    items: List[str] = Field(default_factory=list)
    # Aligned with ``items``; 0 means "no score available" (chips fallback).
    # Defaults to [] so snapshots written before schema 1.1 still validate.
    levels: List[int] = Field(default_factory=list)


class Project(BaseModel):
    name: str
    role: str = ""
    period: str = ""
    summary: str = ""
    tech: List[str] = Field(default_factory=list)
    link: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)


class WritingSeries(BaseModel):
    name: str
    count: int


class Writing(BaseModel):
    article_count: int = 0
    series: List[WritingSeries] = Field(default_factory=list)


class SourceInfo(BaseModel):
    knowledge_base: str = "resume-kb+blog-docs"
    source_hash: str
    article_count: int = 0
    kb_files: List[str] = Field(default_factory=list)


class ResumeDocument(BaseModel):
    schema_version: str = SCHEMA_VERSION
    generated_at: str
    source: SourceInfo
    profile: Profile = Field(default_factory=Profile)
    skills: List[SkillGroup] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    experience: List[Project] = Field(default_factory=list)
    education: List[Project] = Field(default_factory=list)
    honors: List[str] = Field(default_factory=list)
    writing: Writing = Field(default_factory=Writing)
    missing: List[str] = Field(default_factory=list)
