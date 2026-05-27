"""Map raw parsed items from external sources to pystart-question-bank-v1 exercise format.

The mapper handles:
  - Difficulty inference (from labels, code length, keywords)
  - Direction/type inference (from tags, category, content analysis)
  - Tag normalization
  - ID generation
  - Field defaults
"""
from __future__ import annotations
import hashlib
import re

# ─── Chapter mapping (category keyword → chapterId) ─────────────────

CATEGORY_CHAPTER_MAP = {
    # TheAlgorithms directory names → our chapter IDs
    'sorts': 'c13',
    'sort': 'c13',
    'searches': 'c13',
    'search': 'c13',
    'data_structures': 'c17',
    'data-structures': 'c17',
    'linked_list': 'c17',
    'stack': 'c17',
    'queue': 'c17',
    'tree': 'c17',
    'graph': 'c17',
    'hash': 'c17',
    'maths': 'c14',
    'math': 'c14',
    'matrix': 'c14',
    'strings': 'c11',
    'string': 'c11',
    'text': 'c11',
    'dynamic_programming': 'c20',
    'dynamic-programming': 'c20',
    'backtracking': 'c20',
    'greedy': 'c20',
    'bit_manipulation': 'c14',
    'bit': 'c14',
    'boolean': 'c05',
    'logic': 'c05',
    'conditionals': 'c05',
    'loops': 'c07',
    'loop': 'c07',
    'functions': 'c10',
    'function': 'c10',
    'recursion': 'c10',
    'class': 'c19',
    'classes': 'c19',
    'oop': 'c19',
    'conversions': 'c04',
    'conversion': 'c04',
    'casting': 'c04',
    'datetime': 'c18',
    'date': 'c18',
    'time': 'c18',
    'file': 'c18',
    'files': 'c18',
    'io': 'c18',
    'web_programming': 'c29',
    'web': 'c29',
    'network': 'c29',
    'ciphers': 'c15',
    'cipher': 'c15',
    'crypto': 'c15',
    'compression': 'c15',
    'digital_image_processing': 'c28',
    'image': 'c28',
    'audio': 'c28',
    'electronics': 'c28',
    'machine_learning': 'c29',
    'ml': 'c29',
    'linear_algebra': 'c14',
    'statistics': 'c14',
    'physics': 'c28',
    'financial': 'c28',
    'cellular_automata': 'c20',
    'cellular': 'c20',
    'fractals': 'c20',
    'genetic': 'c20',
    'divide_and_conquer': 'c20',
    'divide': 'c20',
    'graph_theory': 'c20',
    'traversals': 'c20',
    'two_pointer': 'c20',
    'two-pointer': 'c20',
    'heap': 'c17',
    'binary': 'c17',
    'trie': 'c17',
    'union_find': 'c17',
}

LEVEL_KEYWORDS_HARD = {'hard', 'advanced', 'challenge', 'complex', 'difficult'}
LEVEL_KEYWORDS_MEDIUM = {'medium', 'intermediate', 'moderate'}
LEVEL_KEYWORDS_EASY = {'easy', 'basic', 'simple', 'beginner', 'intro'}


def infer_chapter_id(raw: dict) -> str:
    """Infer chapter ID from category, directory, or tags."""
    # Check explicit category/directory field
    category = (raw.get('category') or raw.get('directory') or '').lower().strip('/')
    if category:
        # Try last path component first
        parts = [p for p in category.split('/') if p]
        for part in reversed(parts):
            normalized = part.replace('-', '_').replace(' ', '_')
            if normalized in CATEGORY_CHAPTER_MAP:
                return CATEGORY_CHAPTER_MAP[normalized]

    # Check tags
    tags = raw.get('tags') or []
    for tag in tags:
        normalized = str(tag).lower().replace('-', '_').replace(' ', '_')
        if normalized in CATEGORY_CHAPTER_MAP:
            return CATEGORY_CHAPTER_MAP[normalized]

    # Default to c01
    return 'c01'


def infer_level(raw: dict) -> str:
    """Infer exercise difficulty level."""
    # Explicit field
    explicit = (raw.get('difficulty') or raw.get('level') or '').lower()
    for kw in LEVEL_KEYWORDS_HARD:
        if kw in explicit:
            return '挑战'
    for kw in LEVEL_KEYWORDS_MEDIUM:
        if kw in explicit:
            return '进阶'
    for kw in LEVEL_KEYWORDS_EASY:
        if kw in explicit:
            return '基础'

    # From tags
    tags_lower = ' '.join(str(t).lower() for t in (raw.get('tags') or []))
    for kw in LEVEL_KEYWORDS_HARD:
        if kw in tags_lower:
            return '挑战'
    for kw in LEVEL_KEYWORDS_MEDIUM:
        if kw in tags_lower:
            return '进阶'

    # From code length
    code = raw.get('answerCode') or raw.get('content') or ''
    lines = len([l for l in code.split('\n') if l.strip()])
    if lines > 30:
        return '挑战'
    if lines > 10:
        return '进阶'
    return '基础'


def infer_direction(raw: dict) -> str:
    """Infer exercise direction/type."""
    # Explicit
    explicit = (raw.get('direction') or raw.get('question_type') or '').strip()
    if explicit:
        return explicit

    # Has options → likely choice question
    if raw.get('options'):
        return '选择题'

    # Has code → code exercise
    code = raw.get('answerCode') or raw.get('content') or ''
    if 'def ' in code or 'class ' in code or 'import ' in code:
        return '编程题'
    if 'print(' in code:
        return 'Python 基础语法'

    return '填空题'


def normalize_tags(raw: dict, extra_tags: list[str] | None = None) -> list[str]:
    """Normalize and deduplicate tags."""
    tags = set()
    for t in (raw.get('tags') or []):
        t = str(t).strip()
        if t and len(t) < 30:
            tags.add(t)
    if extra_tags:
        for t in extra_tags:
            t = str(t).strip()
            if t and len(t) < 30:
                tags.add(t)
    return sorted(tags)[:10]


def generate_exercise_id(chapter_id: str, raw: dict, counter: int) -> str:
    """Generate a stable exercise ID."""
    # Use source URL hash if available
    source = raw.get('source_url') or raw.get('source') or ''
    title = raw.get('title') or ''
    if source:
        h = hashlib.md5(source.encode()).hexdigest()[:6]
        return f'{chapter_id}-ext-{h}'
    if title:
        h = hashlib.md5(title.encode()).hexdigest()[:6]
        return f'{chapter_id}-ext-{h}'
    return f'{chapter_id}-ext-{counter:03d}'


def map_to_exercise(raw: dict, counter: int = 0) -> dict:
    """Convert a parsed intermediate item to standard exercise format.

    Intermediate format expected:
      title, description, content, source_url, source_name, tags, difficulty, category
    """
    chapter_id = infer_chapter_id(raw)

    exercise = {
        'id': generate_exercise_id(chapter_id, raw, counter),
        'title': (raw.get('title') or '').strip()[:200] or f'导入题目 {counter}',
        'level': infer_level(raw),
        'direction': infer_direction(raw),
        'tags': normalize_tags(raw),
        'description': (raw.get('description') or '').strip()[:1000],
        'text': (raw.get('text') or raw.get('description') or '').strip()[:1000],
        'taskGoal': (raw.get('taskGoal') or f'阅读并理解代码，回答相关问题。').strip()[:500],
        'starter': (raw.get('starter') or '').strip()[:5000] or '# 请在这里完成练习',
        'expectedOutput': (raw.get('expectedOutput') or '').strip()[:1000] or '运行程序查看输出',
        'answer': (raw.get('answer') or '').strip()[:1000],
        'answerCode': (raw.get('answerCode') or raw.get('content') or raw.get('answer') or '').strip()[:10000] or '# 参考答案待补充',
        'hint': (raw.get('hint') or '').strip()[:1000],
        'analysis': (raw.get('analysis') or '').strip()[:2000],
        'examples': raw.get('examples') or [],
        'tests': raw.get('tests') or [],
        'qualityNotes': f'auto-imported from {raw.get("source_name", "unknown")}',
        'source': raw.get('source_url') or raw.get('source_name') or 'auto-import',
    }
    return exercise


def map_batch(items: list[dict], start_counter: int = 0) -> list[dict]:
    """Map a batch of parsed items to exercises."""
    return [map_to_exercise(item, start_counter + i) for i, item in enumerate(items)]
