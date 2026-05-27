#!/usr/bin/env python3
"""Import latest original web-trend exercise drafts into the curated-v2 question bank.

Targets question_banks/curated-v2/question_bank.json (NOT data.json).
Keeps curated v2 chapter size stable at 8 exercises by replacing the last
exercise of the same level when the incoming title is new.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QB_FILE = ROOT / "question_banks" / "curated-v2" / "question_bank.json"
LATEST_FILE = ROOT / "data" / "latest_python_questions.json"
BACKUP_DIR = ROOT / "question_banks" / "curated-v2" / "backups"
SOURCE = "pystart-curated-v2"
MAX_BACKUPS = 5


def main() -> None:
    if not QB_FILE.exists():
        raise FileNotFoundError(
            f"Question bank not found: {QB_FILE}\n"
            "Run scripts/build_curated_question_bank.py first to create the initial bank."
        )

    qb = json.loads(QB_FILE.read_text(encoding="utf-8"))
    latest = json.loads(LATEST_FILE.read_text(encoding="utf-8"))

    # Backup
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    import datetime as dt
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"question_bank_{ts}.json"
    shutil.copy2(QB_FILE, backup_path)
    # Prune old backups
    backups = sorted(BACKUP_DIR.glob("question_bank_*.json"))
    for old in backups[:-MAX_BACKUPS]:
        old.unlink()
    print(f"Backup: {backup_path.name}")

    # Build chapter index using chapterId (NOT id)
    chapters = {c["chapterId"]: c for c in qb.get("chapters", [])}
    existing_titles = {
        e.get("title")
        for c in chapters.values()
        for e in c.get("exercises", [])
    }
    imported = []

    for draft in latest.get("exercises", []):
        cid = draft.get("chapterId")
        chapter = chapters.get(cid)
        if not chapter:
            continue
        if draft.get("title") in existing_titles:
            continue

        exercises = chapter.get("exercises", [])
        if not exercises:
            continue

        # Replace the last exercise of the same level
        draft_level = draft.get("level", "进阶")
        replace_index = None
        for i in range(len(exercises) - 1, -1, -1):
            if exercises[i].get("level") == draft_level:
                replace_index = i
                break
        if replace_index is None:
            replace_index = len(exercises) - 1

        new_ex = {k: v for k, v in draft.items() if k not in {"chapterId", "webSignals"}}
        old_id = exercises[replace_index].get("id", f"{cid}-latest")
        new_ex["id"] = old_id
        # Preserve curated-v2 source for validator
        signals = "、".join(draft.get("webSignals") or [])
        new_ex["source"] = SOURCE
        new_ex["qualityNotes"] = (new_ex.get("qualityNotes", "") + f" 趋势信号：{signals}").strip()

        exercises[replace_index] = new_ex
        existing_titles.add(new_ex["title"])
        imported.append({"chapterId": cid, "title": new_ex["title"], "replacedId": old_id})

    QB_FILE.write_text(json.dumps(qb, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"imported": imported, "count": len(imported)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
