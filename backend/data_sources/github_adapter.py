"""GitHub API adapter — fetch Python code from public repos.

Primary targets:
  - TheAlgorithms/Python (700+ algorithms, MIT license)
  - Any public GitHub repo with Python files

Uses GitHub REST API (no token needed for public repos, 60 req/hr rate limit).
"""
from __future__ import annotations
import base64
import json
import re
import time
import urllib.request
import urllib.error
from .base import DataSourceBase
from .models import DataSourceConfig


class GitHubAdapter(DataSourceBase):
    source_type = 'github_api'

    def fetch(self, config: DataSourceConfig) -> list[dict]:
        """Fetch Python files from a GitHub repository.

        config.options:
          - repo: str          — e.g. "TheAlgorithms/Python" (required)
          - path: str          — subdirectory, e.g. "sorts" (optional, defaults to root)
          - branch: str        — branch name (default: "master")
          - max_files: int     — max files to fetch (default: 50)
          - min_size: int      — skip files smaller than this (default: 100 bytes)
        """
        opts = config.options or {}
        repo = opts.get('repo') or config.url.replace('https://github.com/', '').strip('/')
        path = opts.get('path', '').strip('/')
        branch = opts.get('branch', 'master')
        max_files = opts.get('max_files', 50)
        min_size = opts.get('min_size', 100)

        items = []
        self._fetch_recursive(repo, path, branch, max_files, min_size, items, depth=0)
        return items

    def _fetch_recursive(self, repo: str, path: str, branch: str,
                         max_files: int, min_size: int, items: list, depth: int):
        """Recursively fetch .py files from a GitHub directory."""
        if len(items) >= max_files or depth > 5:
            return

        url = f'https://api.github.com/repos/{repo}/contents/{path}?ref={branch}'
        try:
            entries = self.http_get_json(url, timeout=15)
        except Exception:
            return

        if not isinstance(entries, list):
            return

        for entry in entries:
            if len(items) >= max_files:
                break

            entry_type = entry.get('type', '')
            entry_name = entry.get('name', '')
            entry_path = entry.get('path', '')

            if entry_type == 'dir':
                # Skip hidden directories and __pycache__
                if entry_name.startswith('.') or entry_name == '__pycache__':
                    continue
                time.sleep(0.5)  # rate limiting
                self._fetch_recursive(repo, entry_path, branch, max_files, min_size, items, depth + 1)

            elif entry_type == 'file' and entry_name.endswith('.py'):
                size = entry.get('size', 0)
                if size < min_size:
                    continue

                # Fetch file content
                download_url = entry.get('download_url')
                if not download_url:
                    continue

                try:
                    content = self.http_get_text(download_url, timeout=10)
                except Exception:
                    continue

                items.append({
                    'name': entry_name,
                    'path': entry_path,
                    'directory': '/'.join(entry_path.split('/')[:-1]),
                    'content': content,
                    'size': size,
                    'html_url': entry.get('html_url', ''),
                })
                time.sleep(0.3)  # rate limiting between file fetches

    def parse(self, raw_items: list[dict], config: DataSourceConfig) -> list[dict]:
        """Parse GitHub Python files into intermediate format."""
        parsed = []
        for item in raw_items:
            content = item.get('content', '')
            name = item.get('name', '').replace('.py', '').replace('_', ' ').title()

            # Extract docstring
            docstring = self._extract_docstring(content)
            description = docstring.split('\n')[0] if docstring else name

            # Infer tags from directory
            directory = item.get('directory', '')
            tags = [t for t in directory.split('/') if t and t != '.'][-3:]
            tags.append('Python')

            parsed.append({
                'title': name,
                'description': description,
                'text': docstring or description,
                'content': content,
                'answerCode': content,
                'starter': '',
                'taskGoal': f'阅读并理解 {name} 的实现，回答相关问题。',
                'hint': f'查看源代码 {item.get("html_url", "")}',
                'analysis': docstring[:500] if docstring else '',
                'source_url': item.get('html_url', ''),
                'source_name': 'GitHub',
                'tags': tags,
                'category': directory or item.get('path', ''),
                'difficulty': '',  # will be inferred by mapper
            })
        return parsed

    @staticmethod
    def _extract_docstring(code: str) -> str:
        """Extract the module-level docstring from Python source."""
        code = code.strip()
        # Match triple-quoted docstring at start of file
        for quote in ('"""', "'''"):
            if code.startswith(quote):
                end = code.find(quote, 3)
                if end > 3:
                    return code[3:end].strip()
            # Also check after shebang/encoding lines
            lines = code.split('\n')
            for i, line in enumerate(lines[:5]):
                if line.strip().startswith(quote):
                    rest = '\n'.join(lines[i:])
                    end = rest.find(quote, 3)
                    if end > 3:
                        return rest[3:end].strip()
                    break
                if line.strip() and not line.strip().startswith('#'):
                    break
        return ''
