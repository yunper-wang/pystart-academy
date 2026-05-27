"""RSS/Atom feed adapter — parse Python tutorial blog feeds.

Targets:
  - Real Python RSS feed
  - Python Weekly RSS feed
  - Any RSS/Atom feed with Python tutorials

Uses stdlib xml.etree.ElementTree for RSS/Atom parsing.
"""
from __future__ import annotations
import re
import time
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from .base import DataSourceBase
from .models import DataSourceConfig


class _HTMLStripper(HTMLParser):
    """Strip HTML tags, keep text content."""
    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def get_text(self):
        return ' '.join(self._parts).strip()


def strip_html(html: str) -> str:
    if not html:
        return ''
    try:
        parser = _HTMLStripper()
        parser.feed(html)
        return parser.get_text()[:2000]
    except Exception:
        return re.sub(r'<[^>]+>', '', html)[:2000]


class RSSAdapter(DataSourceBase):
    source_type = 'rss'

    # Default Python RSS feeds
    DEFAULT_FEEDS = {
        'real-python': 'https://realpython.com/atom.xml',
        'python-weekly': 'https://mail.python.org/pipermail/python-dev/atom.xml',
        'planet-python': 'https://planetpython.org/rss20.xml',
    }

    def fetch(self, config: DataSourceConfig) -> list[dict]:
        """Fetch and parse RSS/Atom feed entries.

        config.url: feed URL (or key from DEFAULT_FEEDS)
        config.options:
          - max_entries: int (default: 30)
          - filter_python: bool (default: True) — only keep Python-related entries
        """
        url = config.url
        if url in self.DEFAULT_FEEDS:
            url = self.DEFAULT_FEEDS[url]

        opts = config.options or {}
        max_entries = opts.get('max_entries', 30)

        try:
            raw_xml = self.http_get_text(url, timeout=20)
        except Exception as e:
            raise RuntimeError(f'RSS 抓取失败：{e}') from e

        return self._parse_feed_xml(raw_xml, max_entries)

    def _parse_feed_xml(self, xml_text: str, max_entries: int) -> list[dict]:
        """Parse RSS or Atom XML into raw items."""
        items = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        # Try RSS 2.0
        for item in root.iter('item'):
            if len(items) >= max_entries:
                break
            entry = self._parse_rss_item(item)
            if entry:
                items.append(entry)

        # Try Atom if RSS yielded nothing
        if not items:
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry_elem in root.iter('{http://www.w3.org/2005/Atom}entry'):
                if len(items) >= max_entries:
                    break
                entry = self._parse_atom_entry(entry_elem)
                if entry:
                    items.append(entry)

        return items

    def _parse_rss_item(self, item_elem) -> dict | None:
        title = (item_elem.findtext('title') or '').strip()
        link = (item_elem.findtext('link') or '').strip()
        description = strip_html(item_elem.findtext('description') or '')
        pub_date = (item_elem.findtext('pubDate') or '').strip()
        tags = [cat.text.strip() for cat in item_elem.findall('category') if cat.text]

        if not title:
            return None

        return {
            'title': title,
            'description': description[:500],
            'link': link,
            'pub_date': pub_date,
            'tags': tags,
        }

    def _parse_atom_entry(self, entry_elem) -> dict | None:
        ns = '{http://www.w3.org/2005/Atom}'
        title = (entry_elem.findtext(f'{ns}title') or '').strip()
        link_elem = entry_elem.find(f'{ns}link')
        link = link_elem.get('href', '') if link_elem is not None else ''
        summary = strip_html(entry_elem.findtext(f'{ns}summary') or entry_elem.findtext(f'{ns}content') or '')
        updated = (entry_elem.findtext(f'{ns}updated') or '').strip()
        tags = [cat.get('term', '') for cat in entry_elem.findall(f'{ns}category')]

        if not title:
            return None

        return {
            'title': title,
            'description': summary[:500],
            'link': link,
            'pub_date': updated,
            'tags': [t for t in tags if t],
        }

    def parse(self, raw_items: list[dict], config: DataSourceConfig) -> list[dict]:
        """Parse RSS entries into intermediate exercise format."""
        opts = config.options or {}
        filter_python = opts.get('filter_python', True)
        source_name = config.name or 'RSS'

        parsed = []
        for item in raw_items:
            title = item.get('title', '')
            description = item.get('description', '')

            # Filter: only keep Python-related entries if enabled
            if filter_python:
                combined = (title + ' ' + description).lower()
                if 'python' not in combined and not any('python' in str(t).lower() for t in item.get('tags', [])):
                    continue

            tags = list(item.get('tags') or [])
            if 'Python' not in tags:
                tags.append('Python')

            parsed.append({
                'title': title,
                'description': description,
                'text': description,
                'content': '',
                'answerCode': '',
                'answer': '',
                'taskGoal': f'阅读并理解：{title}',
                'hint': f'参考链接：{item.get("link", "")}',
                'expectedOutput': '',
                'starter': '',
                'analysis': description[:300],
                'source_url': item.get('link', ''),
                'source_name': source_name,
                'tags': tags,
                'category': '',
                'difficulty': '基础',
            })
        return parsed
