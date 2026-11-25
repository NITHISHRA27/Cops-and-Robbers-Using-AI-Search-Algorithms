"""Local JSON persistence for finished games."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from config.settings import HISTORY_FILE

MAX_RECORDS = 200


def load_history(path: Path = HISTORY_FILE) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def save_game(record: dict, path: Path = HISTORY_FILE) -> dict:
    record = dict(record)
    record.setdefault("id", uuid.uuid4().hex[:8])
    record.setdefault("timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))
    history = load_history(path)
    history.insert(0, record)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history[:MAX_RECORDS]), encoding="utf-8")
    return record


def clear_history(path: Path = HISTORY_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]", encoding="utf-8")
