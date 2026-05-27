"""Generic web page adapter — parse static HTML pages for Python exercises.

Uses stdlib html.parser for parsing.
Targets simple static pages like tutorial sites.
"""
from __future__ import annotations
import re
import urllib.request
import urllib.error
from html.parser import HTMLParser
from .base import DataSourceBase
from .models import DataSourceConfig


class _PageParser(HTMLParser):
    """Extract structured content from HTML pages."""

    def __init__(self):
        super().__init__()
        self.sections = []       # list of {title, content, code_blocks}
        self._current = None
        self._tag_stack = []
        self._text_buf = []
        self._code_buf = []
        self._in_code = False
        self._in_pre = False
        self._in_h = None  # h1-h6 tag name

    def handle_starttag(self, tag, attrs):
        self._tag_stack.append(tag)
        attrs_dict = dict(attrs)
        cls = attrs_dict.get('class', '')

        if tag in ('h1', 'h2', 'h3'):
            # Start new section
            if self._current and (self._current.get('content') or self._current.get('code_blocks')):
                self.sections.append(self._current)
            self._current = {'title': '', 'content': '', 'code_blocks': []}
            self._in_h = tag
            self._text_buf = []
        elif tag == 'pre':
            self._in_pre = True
            self._code_buf = []
        elif tag == 'code' and self._in_pre:
            self._in_code = True
            self._code_buf = []

    def handle_endtag(self, tag):
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()

        if tag == self._in_h and self._current:
            self._current['title'] = ' '.join(''.join(self._text_buf).split()).strip()
            self._text_buf = []
            self._in_h = None
        elif tag == 'code' and self._in_code:
            self._in_code = False
        elif tag == 'pre' and self._in_pre:
            self._in_pre = False
            code = ''.join(self._code_buf).strip()
            if code and self._current:
                self._current['code_blocks'].append(code)
            self._code_buf = []

    def handle_data(self, data):
        if self._in_h:
            self._text_buf.append(data)
        elif self._in_code or self._in_pre:
            self._code_buf.append(data)
        elif self._current and not self._in_h:
            self._current['content'] += data

    def finalize(self):
        if self._current and (self._current.get('content') or self._current.get('code_blocks')):
            self.sections.append(self._current)
        return self.sections


class WebAdapter(DataSourceBase):
    source_type = 'web'

    def fetch(self, config: DataSourceConfig) -> list[dict]:
        """Fetch HTML page(s) from URLs.

        config.url: single URL or comma-separated URLs
        config.options:
          - urls: list[str] — multiple URLs (alternative to comma-separated)
          - max_pages: int (default: 10)
        """
        opts = config.options or {}
        max_pages = opts.get('max_pages', 10)

        urls = opts.get('urls', [])
        if not urls:
            urls = [u.strip() for u in config.url.split(',') if u.strip()]

        items = []
        for url in urls[:max_pages]:
            try:
                html = self.http_get_text(url, timeout=15)
                items.append({
                    'url': url,
                    'html': html,
                })
            except Exception:
                continue
        return items

    def parse(self, raw_items: list[dict], config: DataSourceConfig) -> list[dict]:
        """Parse HTML pages into intermediate format."""
        source_name = config.name or 'Web'
        parsed = []

        for item in raw_items:
            html = item.get('html', '')
            url = item.get('url', '')

            # Parse HTML structure
            parser = _PageParser()
            try:
                parser.feed(html)
                sections = parser.finalize()
            except Exception:
                continue

            for section in sections:
                title = section.get('title', '').strip()
                content = section.get('content', '').strip()
                code_blocks = section.get('code_blocks', [])

                if not title and not code_blocks:
                    continue

                # Clean up whitespace
                content = ' '.join(content.split())[:1000]

                parsed.append({
                    'title': title or 'Untitled Section',
                    'description': content[:500],
                    'text': content[:500],
                    'content': '\n\n'.join(code_blocks),
                    'answerCode': code_blocks[0] if code_blocks else '',
                    'answer': '',
                    'taskGoal': f'阅读并理解：{title}' if title else '阅读并理解代码。',
                    'hint': f'参考页面：{url}',
                    'expectedOutput': '',
                    'starter': '',
                    'analysis': content[:300],
                    'source_url': url,
                    'source_name': source_name,
                    'tags': ['Web'],
                    'category': '',
                })
        return parsed
