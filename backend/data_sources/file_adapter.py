"""Local file adapter — import exercises from JSON, CSV, or Markdown files.

Supports:
  - JSON files (array of exercise objects or question bank format)
  - CSV files (header row required)
  - Markdown files (parsed for code blocks + descriptions)
"""
from __future__ import annotations
import csv
import io
import json
import re
from pathlib import Path
from .base import DataSourceBase
from .models import DataSourceConfig


class FileAdapter(DataSourceBase):
    source_type = 'file'

    def fetch(self, config: DataSourceConfig) -> list[dict]:
        """Read raw content from local file(s).

        config.url: file path or directory path
        config.options:
          - pattern: str — glob pattern for directory (default: "*.json")
        """
        path = Path(config.url).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f'文件不存在：{path}')

        if path.is_dir():
            pattern = (config.options or {}).get('pattern', '*.json')
            files = sorted(path.glob(pattern))
        else:
            files = [path]

        items = []
        for f in files[:20]:  # max 20 files
            try:
                raw = f.read_text(encoding='utf-8')
                items.append({
                    'filename': f.name,
                    'path': str(f),
                    'content': raw,
                    'extension': f.suffix.lower(),
                })
            except (OSError, UnicodeDecodeError):
                continue
        return items

    def parse(self, raw_items: list[dict], config: DataSourceConfig) -> list[dict]:
        """Parse files based on extension."""
        parsed = []
        for item in raw_items:
            ext = item.get('extension', '')
            content = item.get('content', '')

            if ext == '.json':
                parsed.extend(self._parse_json(content, item))
            elif ext == '.csv':
                parsed.extend(self._parse_csv(content, item))
            elif ext in ('.md', '.markdown'):
                parsed.extend(self._parse_markdown(content, item))
        return parsed

    def _parse_json(self, content: str, item: dict) -> list[dict]:
        """Parse JSON file — supports array format or question bank format."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return []

        results = []
        filename = item.get('filename', '')

        # Question bank format
        if isinstance(data, dict) and 'chapters' in data:
            for chapter in data.get('chapters', []):
                ch_id = chapter.get('chapterId', '')
                for ex in chapter.get('exercises', []):
                    results.append(self._normalize(ex, filename, ch_id))
            return results

        # Array of exercises
        if isinstance(data, list):
            for ex in data:
                if isinstance(ex, dict):
                    results.append(self._normalize(ex, filename))
            return results

        return []

    def _parse_csv(self, content: str, item: dict) -> list[dict]:
        """Parse CSV with headers: title, description, answer, difficulty, tags"""
        results = []
        filename = item.get('filename', '')
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            results.append({
                'title': row.get('title', ''),
                'description': row.get('description', ''),
                'text': row.get('text', row.get('description', '')),
                'content': row.get('answerCode', row.get('content', '')),
                'answerCode': row.get('answerCode', ''),
                'answer': row.get('answer', ''),
                'difficulty': row.get('difficulty', ''),
                'tags': [t.strip() for t in (row.get('tags', '')).split(',') if t.strip()],
                'source_name': f'CSV:{filename}',
                'source_url': '',
                'taskGoal': row.get('taskGoal', ''),
                'hint': row.get('hint', ''),
                'expectedOutput': row.get('expectedOutput', ''),
                'starter': row.get('starter', ''),
                'analysis': row.get('analysis', ''),
                'category': row.get('category', ''),
            })
        return results

    def _parse_markdown(self, content: str, item: dict) -> list[dict]:
        """Parse Markdown for code blocks with preceding headers as descriptions."""
        results = []
        filename = item.get('filename', '')
        # Split by ## headers
        sections = re.split(r'^## ', content, flags=re.MULTILINE)

        for section in sections[1:]:  # skip first empty split
            lines = section.strip().split('\n', 1)
            title = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ''

            # Find code blocks
            code_blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', body, re.DOTALL)
            description = re.sub(r'```.*?```', '', body, flags=re.DOTALL).strip()

            if code_blocks:
                results.append({
                    'title': title,
                    'description': description[:500],
                    'text': description[:500],
                    'content': code_blocks[0].strip(),
                    'answerCode': code_blocks[0].strip(),
                    'answer': '',
                    'difficulty': '',
                    'tags': ['Markdown'],
                    'source_name': f'Markdown:{filename}',
                    'source_url': '',
                    'taskGoal': f'完成 {title} 相关练习。',
                    'hint': '',
                    'expectedOutput': '',
                    'starter': '',
                    'analysis': description[:300] if description else '',
                    'category': '',
                })
        return results

    @staticmethod
    def _normalize(ex: dict, filename: str, chapter_id: str = '') -> dict:
        """Normalize an exercise dict to intermediate format."""
        return {
            'title': ex.get('title', ''),
            'description': ex.get('description', ''),
            'text': ex.get('text', ex.get('description', '')),
            'content': ex.get('answerCode', ex.get('content', '')),
            'answerCode': ex.get('answerCode', ''),
            'answer': ex.get('answer', ''),
            'difficulty': ex.get('level', ex.get('difficulty', '')),
            'tags': ex.get('tags', []),
            'source_name': f'File:{filename}',
            'source_url': '',
            'taskGoal': ex.get('taskGoal', ''),
            'hint': ex.get('hint', ''),
            'expectedOutput': ex.get('expectedOutput', ''),
            'starter': ex.get('starter', ''),
            'analysis': ex.get('analysis', ''),
            'category': chapter_id or ex.get('chapterId', ''),
        }
