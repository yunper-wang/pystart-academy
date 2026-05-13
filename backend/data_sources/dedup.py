"""MD5-based deduplication for imported exercises.

Maintains a fingerprint index in JSON to avoid re-importing duplicates.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

INDEX_FILE = Path(__file__).resolve().parent.parent.parent / 'question_banks' / 'fingerprint_index.json'


def exercise_fingerprint(exercise: dict) -> str:
    """Generate MD5 fingerprint from exercise title + text + answerCode."""
    parts = [
        str(exercise.get('title', '')),
        str(exercise.get('text', '')),
        str(exercise.get('description', '')),
        str(exercise.get('answerCode', '')),
    ]
    raw = '|'.join(parts).strip().lower()
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


class DedupIndex:
    """Simple JSON-backed set of fingerprints."""

    def __init__(self):
        self._fingerprints: set[str] = set()
        self._load()

    def _load(self):
        if INDEX_FILE.exists():
            try:
                with INDEX_FILE.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                self._fingerprints = set(data) if isinstance(data, list) else set()
            except (json.JSONDecodeError, OSError):
                self._fingerprints = set()

    def save(self):
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        INDEX_FILE.write_text(
            json.dumps(sorted(self._fingerprints), ensure_ascii=False),
            encoding='utf-8'
        )

    def contains(self, exercise: dict) -> bool:
        return exercise_fingerprint(exercise) in self._fingerprints

    def add(self, exercise: dict) -> str:
        """Add exercise fingerprint, return the fingerprint."""
        fp = exercise_fingerprint(exercise)
        self._fingerprints.add(fp)
        return fp

    def deduplicate(self, exercises: list[dict]) -> tuple[list[dict], list[dict]]:
        """Split exercises into (new, duplicates).

        New exercises are automatically added to the index.
        """
        new = []
        dupes = []
        for ex in exercises:
            if self.contains(ex):
                dupes.append(ex)
            else:
                self.add(ex)
                new.append(ex)
        return new, dupes

    def bulk_add_from_bank(self, bank: dict):
        """Load existing exercises from a question bank into the index."""
        for chapter in bank.get('chapters', []):
            for exercise in chapter.get('exercises', []):
                self.add(exercise)

    @property
    def size(self) -> int:
        return len(self._fingerprints)
