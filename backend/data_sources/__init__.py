"""data_sources package — PyStart Academy auto-import system.

Usage:
    from backend.data_sources import run_import, list_sources, add_source, ...
"""
from __future__ import annotations
import json
import traceback
from typing import Optional

from .models import (
    DataSourceConfig, ImportLog,
    load_configs, save_configs, load_logs, append_log,
    get_config, now_iso, new_id,
)
from .dedup import DedupIndex
from .mapper import map_batch
from .scheduler import scheduler as _scheduler

# ─── Adapter registry ───────────────────────────────────────────────

_ADAPTERS = {}


def _get_adapter(source_type: str):
    """Lazy-load adapter by source_type."""
    if source_type in _ADAPTERS:
        return _ADAPTERS[source_type]

    if source_type == 'github_api':
        from .github_adapter import GitHubAdapter
        adapter = GitHubAdapter()
    elif source_type == 'rss':
        from .rss_adapter import RSSAdapter
        adapter = RSSAdapter()
    elif source_type == 'web':
        from .web_adapter import WebAdapter
        adapter = WebAdapter()
    elif source_type == 'file':
        from .file_adapter import FileAdapter
        adapter = FileAdapter()
    else:
        raise ValueError(f'不支持的数据源类型：{source_type}')

    _ADAPTERS[source_type] = adapter
    return adapter


# ─── CRUD for data source configs ───────────────────────────────────

def list_sources() -> list[dict]:
    """List all data source configs with status."""
    configs = load_configs()
    active_jobs = _scheduler.get_status().get('activeJobs', {})
    return [
        {
            **c.to_dict(),
            'running': c.id in active_jobs,
        }
        for c in configs
    ]


def add_source(name: str, source_type: str, url: str,
               schedule: str = '', enabled: bool = True,
               options: dict | None = None) -> DataSourceConfig:
    """Create a new data source config."""
    configs = load_configs()
    config = DataSourceConfig(
        id=new_id(),
        name=name,
        source_type=source_type,
        url=url,
        enabled=enabled,
        schedule=schedule or '',
        options=options or {},
    )
    configs.append(config)
    save_configs(configs)
    return config


def update_source(source_id: str, updates: dict) -> DataSourceConfig:
    """Update an existing data source config."""
    configs = load_configs()
    for c in configs:
        if c.id == source_id:
            for key in ('name', 'source_type', 'url', 'enabled', 'schedule', 'options'):
                if key in updates:
                    setattr(c, key, updates[key])
            save_configs(configs)
            return c
    raise ValueError(f'数据源不存在：{source_id}')


def delete_source(source_id: str):
    """Delete a data source config."""
    configs = load_configs()
    configs = [c for c in configs if c.id != source_id]
    save_configs(configs)


# ─── Import execution ───────────────────────────────────────────────

def run_import(source_id: str) -> ImportLog:
    """Execute an import for a single data source.

    1. Load config
    2. Fetch raw data via adapter
    3. Parse to intermediate format
    4. Map to exercise format
    5. Deduplicate against existing bank
    6. Import new exercises into question bank
    7. Log the result
    """
    from . import models as _m  # avoid circular

    config = get_config(source_id)
    if not config:
        raise ValueError(f'数据源不存在：{source_id}')

    started = now_iso()
    errors = []
    fetched = 0
    imported = 0
    skipped = 0

    try:
        # 1. Get adapter
        adapter = _get_adapter(config.source_type)

        # 2. Fetch
        raw_items = adapter.fetch(config)
        fetched = len(raw_items)

        if not raw_items:
            log = ImportLog(
                source_id=source_id,
                source_name=config.name,
                started_at=started,
                finished_at=now_iso(),
                status='success',
                fetched=0, imported=0, skipped=0,
                errors=['没有抓取到数据。'],
            )
            append_log(log)
            _update_last_sync(config)
            return log

        # 3. Parse
        parsed_items = adapter.parse(raw_items, config)

        # 4. Map to exercises
        exercises = map_batch(parsed_items)

        # 5. Dedup
        dedup = DedupIndex()
        # Load existing bank fingerprints
        try:
            from .. import question_bank_service
            bank = question_bank_service.load_question_bank(validate=False)
            dedup.bulk_add_from_bank(bank)
        except Exception:
            pass

        new_exercises, dupes = dedup.deduplicate(exercises)
        skipped = len(dupes)
        dedup.save()

        # 6. Import into question bank
        if new_exercises:
            try:
                from .. import question_bank_service
                # Build a mini bank with new exercises grouped by chapter
                chapter_map = {}
                for ex in new_exercises:
                    ch_id = 'auto-import'
                    # Use mapper's inferred chapter
                    from .mapper import infer_chapter_id
                    ch_id = infer_chapter_id(ex)
                    if ch_id not in chapter_map:
                        chapter_map[ch_id] = {
                            'chapterId': ch_id,
                            'chapterTitle': f'自动导入 - {ch_id}',
                            'exercises': [],
                        }
                    chapter_map[ch_id]['exercises'].append(ex)

                mini_bank = {
                    'schemaVersion': 'pystart-question-bank-v1',
                    'id': f'import-{source_id}',
                    'title': f'Auto import from {config.name}',
                    'chapters': list(chapter_map.values()),
                }

                question_bank_service.import_question_bank(
                    mini_bank,
                    strategy='append'
                )
                imported = len(new_exercises)
            except Exception as e:
                errors.append(f'写入题库失败：{str(e)}')
                imported = 0

        status = 'success' if not errors else ('partial' if imported > 0 else 'error')

    except Exception as e:
        errors.append(f'{type(e).__name__}: {str(e)}')
        status = 'error'

    log = ImportLog(
        source_id=source_id,
        source_name=config.name,
        started_at=started,
        finished_at=now_iso(),
        status=status,
        fetched=fetched,
        imported=imported,
        skipped=skipped,
        errors=errors,
    )
    append_log(log)
    _update_last_sync(config)
    return log


def _update_last_sync(config: DataSourceConfig):
    """Update last_sync timestamp for a config."""
    try:
        configs = load_configs()
        for c in configs:
            if c.id == config.id:
                c.last_sync = now_iso()
        save_configs(configs)
    except Exception:
        pass


# ─── Scheduler management ───────────────────────────────────────────

def get_scheduler_status() -> dict:
    return _scheduler.get_status()


def start_scheduler():
    """Start the background scheduler (called at server startup)."""
    _scheduler.set_import_fn(run_import)
    _scheduler.start()


def trigger_import_async(source_id: str):
    """Trigger an import in background thread."""
    _scheduler.run_import_async(source_id)


def is_import_running(source_id: str) -> bool:
    return _scheduler.is_job_running(source_id)


# ─── Logs ────────────────────────────────────────────────────────────

def get_logs(limit: int = 50) -> list[dict]:
    logs = load_logs()
    return [l.to_dict() for l in logs[:limit]]


# ─── Preset sources ─────────────────────────────────────────────────

PRESET_SOURCES = [
    {
        'name': 'TheAlgorithms/Python',
        'source_type': 'github_api',
        'url': 'https://github.com/TheAlgorithms/Python',
        'schedule': '',
        'options': {
            'repo': 'TheAlgorithms/Python',
            'path': '',
            'branch': 'master',
            'max_files': 30,
            'min_size': 200,
        },
    },
    {
        'name': 'TheAlgorithms 排序算法',
        'source_type': 'github_api',
        'url': 'https://github.com/TheAlgorithms/Python/tree/master/sorts',
        'schedule': '',
        'options': {
            'repo': 'TheAlgorithms/Python',
            'path': 'sorts',
            'branch': 'master',
            'max_files': 20,
            'min_size': 100,
        },
    },
    {
        'name': 'TheAlgorithms 数据结构',
        'source_type': 'github_api',
        'url': 'https://github.com/TheAlgorithms/Python/tree/master/data_structures',
        'schedule': '',
        'options': {
            'repo': 'TheAlgorithms/Python',
            'path': 'data_structures',
            'branch': 'master',
            'max_files': 20,
            'min_size': 200,
        },
    },
    {
        'name': 'Real Python (RSS)',
        'source_type': 'rss',
        'url': 'https://realpython.com/atom.xml',
        'schedule': '@weekly',
        'options': {'max_entries': 20, 'filter_python': True},
    },
]
