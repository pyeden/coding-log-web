"""分享与反馈的本地持久化：SQLite（分享，30 天 TTL）+ JSONL（反馈）。

数据目录默认 backend/travel_assistant/data/，已加入 .gitignore。
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("TRAVEL_DATA_DIR") or os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "travel.db")
FEEDBACK_PATH = os.path.join(DATA_DIR, "feedback.jsonl")

SHARE_TTL_DAYS = 30
SHARE_ID_LENGTH = 8
_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
_ID_RE = re.compile(r"^[a-z0-9]{8}$")


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _connect() -> sqlite3.Connection:
    _ensure_data_dir()
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS shares ("
        "id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL)"
    )
    return conn


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def save_share(payload: dict) -> str:
    """保存完整 plan，返回 8 位短 id。"""
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    conn = _connect()
    try:
        for _ in range(8):
            share_id = "".join(secrets.choice(_ALPHABET) for _ in range(SHARE_ID_LENGTH))
            try:
                conn.execute(
                    "INSERT INTO shares (id, payload, created_at) VALUES (?, ?, ?)",
                    (share_id, raw, _utcnow().isoformat(timespec="seconds")),
                )
                conn.commit()
                return share_id
            except sqlite3.IntegrityError:
                continue
        raise RuntimeError("SHARE_ID_COLLISION")
    finally:
        conn.close()


def get_share(share_id: str) -> dict | None:
    """读取分享；不存在或超过 30 天返回 None，并清理过期记录。"""
    share_id = (share_id or "").strip().lower()
    if not _ID_RE.match(share_id):
        return None
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT payload, created_at FROM shares WHERE id = ?", (share_id,)
        ).fetchone()
        if not row:
            return None
        payload, created_at = row
        try:
            created = datetime.fromisoformat(created_at)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
        except ValueError:
            created = _utcnow()
        if _utcnow() - created > timedelta(days=SHARE_TTL_DAYS):
            conn.execute("DELETE FROM shares WHERE id = ?", (share_id,))
            conn.commit()
            return None
        data = json.loads(payload)
        return data if isinstance(data, dict) else None
    finally:
        conn.close()
    return None


def append_feedback(record: dict) -> None:
    """追加一条反馈；只保存调用方传入的非 PII 字段。"""
    _ensure_data_dir()
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with open(FEEDBACK_PATH, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
