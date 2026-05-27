#!/usr/bin/env python3
"""Import latest web-trend exercise drafts into the curated-v2 question bank.

Replaces the last exercise of matching level in each chapter when the
incoming title is new. Maintains 8 exercises per chapter (except chapters
that already have more).

Usage:
    python scripts/import_to_curated_bank.py [--dry-run]
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QB_FILE = ROOT / "question_banks" / "curated-v2" / "question_bank.json"
LATEST_FILE = ROOT / "data" / "latest_python_questions.json"
BACKUP_FILE = ROOT / "question_banks" / "curated-v2" / "question_bank.backup.json"


def main(dry_run: bool = False) -> None:
    qb = json.loads(QB_FILE.read_text(encoding="utf-8"))
    latest = json.loads(LATEST_FILE.read_text(encoding="utf-8"))

    exercises = latest.get("exercises", [])
    if not exercises:
        print("No exercises to import.")
        return

    if not BACKUP_FILE.exists() and not dry_run:
        shutil.copy2(QB_FILE, BACKUP_FILE)
        print(f"Backup saved to {BACKUP_FILE.relative_to(ROOT)}")

    chapters = {ch["chapterId"]: ch for ch in qb.get("chapters", [])}
    existing_titles = {
        ex.get("title")
        for ch in chapters.values()
        for ex in ch.get("exercises", [])
    }
    imported = []
    skipped = []

    for draft in exercises:
        cid = draft.get("chapterId")
        chapter = chapters.get(cid)
        if not chapter:
            skipped.append({"chapterId": cid, "reason": "chapter not found"})
            continue
        if draft.get("title") in existing_titles:
            skipped.append({"chapterId": cid, "title": draft.get("title"), "reason": "duplicate title"})
            continue

        ch_exercises = chapter.get("exercises", [])
        draft_level = draft.get("level", "进阶")

        # Find last exercise of same level to replace
        replace_index = None
        for i in range(len(ch_exercises) - 1, -1, -1):
            if ch_exercises[i].get("level") == draft_level:
                replace_index = i
                break
        if replace_index is None:
            replace_index = len(ch_exercises) - 1

        old_ex = ch_exercises[replace_index]
        old_id = old_ex.get("id", f"{cid}-unknown")

        # Build new exercise (preserve id for app compatibility)
        new_ex = {
            "id": old_id,
            "level": draft.get("level", "进阶"),
            "title": draft.get("title", ""),
            "text": draft.get("text", ""),
            "description": draft.get("description", ""),
            "hint": draft.get("hint", ""),
            "answer": draft.get("answerCode", ""),
            "starter": draft.get("starter", ""),
            "expectedOutput": draft.get("expectedOutput", ""),
            "answerCode": draft.get("answerCode", ""),
            "taskGoal": draft.get("taskGoal", ""),
            "analysis": draft.get("analysis", ""),
            "tags": draft.get("tags", []),
            "examples": draft.get("examples", []),
            "tests": draft.get("tests", []),
            "direction": draft.get("direction", ""),
            "source": "pystart-web-trend-original-v2",
            "qualityNotes": draft.get("qualityNotes", ""),
        }

        if dry_run:
            print(f"  [DRY-RUN] Would replace {old_id} in {cid}: {old_ex.get('title')} → {new_ex['title']}")
        else:
            ch_exercises[replace_index] = new_ex
            existing_titles.add(new_ex["title"])

        imported.append({
            "chapterId": cid,
            "replacedId": old_id,
            "oldTitle": old_ex.get("title"),
            "newTitle": new_ex["title"],
        })

    if not dry_run and imported:
        qb["updatedAt"] = latest.get("generatedAt", "")
        QB_FILE.write_text(json.dumps(qb, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Updated {QB_FILE.relative_to(ROOT)}")

    result = {
        "imported": len(imported),
        "skipped": len(skipped),
        "details": imported,
        "skippedDetails": skipped,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
