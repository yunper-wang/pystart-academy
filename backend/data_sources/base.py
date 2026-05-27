"""Abstract base class for data source adapters.

Each adapter must implement:
  - fetch(config) -> list[dict]    — retrieve raw items from the source
  - parse(raw_items, config) -> list[dict]  — convert to internal format

The mapper module converts parsed items into standard exercise format.
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Any

from .models import DataSourceConfig


class DataSourceBase(ABC):
    """Base class all data source adapters extend."""

    source_type: str = ''  # subclasses must set this

    @abstractmethod
    def fetch(self, config: DataSourceConfig) -> list[dict]:
        """Retrieve raw data from the source.

        Returns a list of raw item dicts (format depends on source_type).
        """
        ...

    @abstractmethod
    def parse(self, raw_items: list[dict], config: DataSourceConfig) -> list[dict]:
        """Parse raw items into a normalized intermediate format.

        The intermediate format should contain at minimum:
          - title: str
          - description: str
          - content: str (code or text body)
          - source_url: str
          - source_name: str
          - tags: list[str]
          - difficulty: str (optional)
        """
        ...

    # ── Shared HTTP helpers ──────────────────────────────────────

    @staticmethod
    def http_get(url: str, headers: dict | None = None, timeout: int = 30) -> bytes:
        """Simple GET request using stdlib urllib."""
        req = urllib.request.Request(url, method='GET')
        req.add_header('User-Agent', 'PyStart-Academy/1.0 (auto-import)')
        req.add_header('Accept', 'application/json')
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'HTTP {e.code}: {e.reason} — {url}') from e
        except urllib.error.URLError as e:
            raise RuntimeError(f'网络错误: {e.reason} — {url}') from e

    @staticmethod
    def http_get_json(url: str, headers: dict | None = None, timeout: int = 30) -> Any:
        """GET and parse JSON response."""
        raw = DataSourceBase.http_get(url, headers, timeout)
        return json.loads(raw.decode('utf-8'))

    @staticmethod
    def http_get_text(url: str, headers: dict | None = None, timeout: int = 30) -> str:
        """GET and return text content."""
        raw = DataSourceBase.http_get(url, headers, timeout)
        return raw.decode('utf-8', errors='replace')
