"""Data models for the auto-import system.

Zero external dependencies — stdlib only (dataclasses, json, datetime).
"""
from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# ─── Data Source Config ─────────────────────────────────────────────

@dataclass
class DataSourceConfig:
    id: str
    name: str
    source_type: str      # 'github_api' | 'rss' | 'web' | 'file'
    url: str
    enabled: bool = True
    schedule: str = ''    # Cron expression, empty = manual only
    last_sync: str = ''
    options: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> DataSourceConfig:
        return cls(
            id=d.get('id', ''),
            name=d.get('name', ''),
            source_type=d.get('source_type', ''),
            url=d.get('url', ''),
            enabled=d.get('enabled', True),
            schedule=d.get('schedule', ''),
            last_sync=d.get('last_sync', ''),
            options=d.get('options', {}),
        )


# ─── Import Job ─────────────────────────────────────────────────────

@dataclass
class ImportJob:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    source_id: str = ''
    started_at: str = ''
    finished_at: str = ''
    status: str = 'pending'  # 'pending' | 'running' | 'success' | 'partial' | 'error'
    fetched: int = 0
    imported: int = 0
    skipped: int = 0
    errors: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ImportJob:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─── Import Log ─────────────────────────────────────────────────────

@dataclass
class ImportLog:
    source_id: str
    source_name: str
    started_at: str
    finished_at: str
    status: str
    fetched: int
    imported: int
    skipped: int
    errors: list

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ImportLog:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─── Persistence helpers ────────────────────────────────────────────

CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / 'question_banks' / 'data_sources.json'
LOG_FILE = Path(__file__).resolve().parent.parent.parent / 'question_banks' / 'import_logs.json'
MAX_LOGS = 100


def load_configs() -> list[DataSourceConfig]:
    if not CONFIG_FILE.exists():
        return []
    with CONFIG_FILE.open('r', encoding='utf-8') as f:
        data = json.load(f)
    return [DataSourceConfig.from_dict(d) for d in data if isinstance(d, dict)]


def save_configs(configs: list[DataSourceConfig]):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps([c.to_dict() for c in configs], ensure_ascii=False, indent=2),
        encoding='utf-8'
    )


def load_logs() -> list[ImportLog]:
    if not LOG_FILE.exists():
        return []
    with LOG_FILE.open('r', encoding='utf-8') as f:
        data = json.load(f)
    return [ImportLog.from_dict(d) for d in data if isinstance(d, dict)]


def append_log(log: ImportLog):
    logs = load_logs()
    logs.insert(0, log)  # newest first
    logs = logs[:MAX_LOGS]
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(
        json.dumps([l.to_dict() for l in logs], ensure_ascii=False, indent=2),
        encoding='utf-8'
    )


def get_config(config_id: str) -> Optional[DataSourceConfig]:
    for c in load_configs():
        if c.id == config_id:
            return c
    return None


def now_iso() -> str:
    return datetime.now().isoformat(timespec='seconds')


def new_id() -> str:
    return 'ds-' + uuid.uuid4().hex[:6]
