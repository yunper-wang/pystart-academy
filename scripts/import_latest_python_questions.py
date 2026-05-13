#!/usr/bin/env python3
"""Import latest original web-trend exercise drafts into data.json.

Keeps curated v2 chapter size stable at 8 exercises by replacing the last
challenge exercise in a matching chapter when the incoming title is new.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"
LATEST_FILE = ROOT / "data" / "latest_python_questions.json"
BACKUP_FILE = ROOT / "data.backup-before-latest-web-trend.json"
SOURCE = "pystart-curated-v2"


def main() -> None:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    latest = json.loads(LATEST_FILE.read_text(encoding="utf-8"))
    if not BACKUP_FILE.exists():
        shutil.copy2(DATA_FILE, BACKUP_FILE)

    chapters = {c["id"]: c for c in data.get("chapters", [])}
    existing_titles = {e.get("title") for c in chapters.values() for e in c.get("exercises", [])}
    imported = []

    for draft in latest.get("exercises", []):
        cid = draft.get("chapterId")
        chapter = chapters.get(cid)
        if not chapter or draft.get("title") in existing_titles:
            continue
        exercises = chapter.get("exercises", [])
        # Preserve app/validator assumptions: 8 curated-v2 exercises per chapter.
        replace_index = None
        for i in range(len(exercises) - 1, -1, -1):
            if exercises[i].get("level") == draft.get("level"):
                replace_index = i
                break
        if replace_index is None:
            replace_index = len(exercises) - 1
        new_ex = {k: v for k, v in draft.items() if k not in {"chapterId", "webSignals"}}
        old_id = exercises[replace_index].get("id", f"{cid}-latest")
        new_ex["id"] = old_id
        # The existing validator requires all production exercises to remain curated-v2.
        # Preserve the source while retaining provenance in qualityNotes.
        signals = "、".join(draft.get("webSignals") or [])
        new_ex["source"] = SOURCE
        new_ex["qualityNotes"] = (new_ex.get("qualityNotes", "") + f" 趋势信号：{signals}").strip()
        exercises[replace_index] = new_ex
        existing_titles.add(new_ex["title"])
        imported.append({"chapterId": cid, "title": new_ex["title"], "replacedId": old_id})

    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"imported": imported, "count": len(imported)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
