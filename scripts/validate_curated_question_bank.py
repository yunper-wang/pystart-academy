#!/usr/bin/env python3
"""Validate the curated v2 PyStart exercise bank."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"
SOURCE = "pystart-curated-v2"
REQUIRED = [
    "id", "title", "level", "direction", "tags", "description", "text",
    "taskGoal", "starter", "expectedOutput", "answer", "answerCode",
    "hint", "analysis", "examples", "tests", "qualityNotes", "source",
]
LEVEL_EXPECTED = Counter({"基础": 3, "进阶": 3, "挑战": 2})
BANNED_SOURCES = {"legacy/unknown", "futurecoder-authorized-copy", "futurecoder", "pystart-quality-original-v1"}


def run_code(code: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "answer.py"
        path.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, str(path)],
                cwd=tmp,
                text=True,
                capture_output=True,
                timeout=3,
            )
        except subprocess.TimeoutExpired:
            return False, "TIMEOUT"
    output = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, output


def main() -> None:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    chapters = data.get("chapters", [])
    errors: list[str] = []
    total = 0
    all_sources = Counter()
    all_levels = Counter()
    ids = set()
    direction_counter = Counter()

    if len(chapters) != 30:
        errors.append(f"章节数应为 30，实际 {len(chapters)}")

    for chapter in chapters:
        cid = chapter.get("id")
        exercises = chapter.get("exercises", [])
        total += len(exercises)
        levels = Counter(e.get("level") for e in exercises)
        if len(exercises) != 8:
            errors.append(f"{cid} 题数应为 8，实际 {len(exercises)}")
        if levels != LEVEL_EXPECTED:
            errors.append(f"{cid} 难度分布错误：{dict(levels)}")
        tag_union = set()
        for idx, ex in enumerate(exercises, 1):
            prefix = f"{cid}#{idx}"
            missing = [field for field in REQUIRED if field not in ex or ex[field] in (None, "", [])]
            if missing:
                errors.append(f"{prefix} 缺少字段：{missing}")
            qid = ex.get("id")
            if qid in ids:
                errors.append(f"重复题目 id：{qid}")
            ids.add(qid)
            source = ex.get("source")
            all_sources[source] += 1
            all_levels[ex.get("level")] += 1
            direction_counter[ex.get("direction")] += 1
            tag_union.update(ex.get("tags") or [])
            if source != SOURCE:
                errors.append(f"{prefix} source 应为 {SOURCE}，实际 {source}")
            if source in BANNED_SOURCES:
                errors.append(f"{prefix} 包含被禁旧来源：{source}")
            if len(ex.get("title", "")) < 4:
                errors.append(f"{prefix} title 信息量不足")
            if len(ex.get("description", "")) < 18:
                errors.append(f"{prefix} description 过短")
            if len(ex.get("analysis", "")) < 35:
                errors.append(f"{prefix} analysis 过短")
            if len(ex.get("tags") or []) < 2:
                errors.append(f"{prefix} tags 至少需要 2 个")
            if not isinstance(ex.get("examples"), list) or not ex.get("examples"):
                errors.append(f"{prefix} examples 不能为空")
            if not isinstance(ex.get("tests"), list) or not ex.get("tests"):
                errors.append(f"{prefix} tests 不能为空")
            ok, output = run_code(ex.get("answerCode", ""))
            expected = str(ex.get("expectedOutput", "")).strip()
            if not ok:
                errors.append(f"{prefix} answerCode 运行失败：{output[:160]}")
            elif output != expected:
                errors.append(f"{prefix} 输出不匹配：expected={expected!r}, got={output!r}")
        if len(tag_union) < 2:
            errors.append(f"{cid} 标签覆盖不足")

    if total != 240:
        errors.append(f"总题数应为 240，实际 {total}")
    if all_sources != Counter({SOURCE: 240}):
        errors.append(f"来源分布错误：{dict(all_sources)}")
    if all_levels != Counter({"基础": 90, "进阶": 90, "挑战": 60}):
        errors.append(f"全局难度分布错误：{dict(all_levels)}")
    if len(direction_counter) < 20:
        errors.append(f"方向覆盖不足：{len(direction_counter)}")

    print("curated-v2 validation summary")
    print("chapters:", len(chapters))
    print("total:", total)
    print("sources:", dict(all_sources))
    print("levels:", dict(all_levels))
    print("directions:", len(direction_counter))

    if errors:
        print("\nERRORS:")
        for err in errors[:80]:
            print("-", err)
        if len(errors) > 80:
            print(f"... {len(errors)-80} more")
        raise SystemExit(1)
    print("validation passed")


if __name__ == "__main__":
    main()
