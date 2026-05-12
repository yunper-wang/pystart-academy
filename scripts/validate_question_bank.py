#!/usr/bin/env python3
"""Validate PyStart Academy exercise data quality.

This script intentionally focuses on the enhanced original question bank:
exercises tagged with source == 'pystart-quality-original-v1'. It verifies
that the new exercises keep the existing app-compatible fields while adding
richer learning metadata.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"
SOURCE = "pystart-quality-original-v1"
REQUIRED_FIELDS = [
    "level",
    "title",
    "text",
    "description",
    "hint",
    "starter",
    "expectedOutput",
    "answer",
    "answerCode",
    "taskGoal",
    "analysis",
    "tags",
    "examples",
    "tests",
    "source",
]
REQUIRED_DIRECTIONS = {
    "Python 基础语法",
    "字符串",
    "列表",
    "字典",
    "集合",
    "元组",
    "条件判断和循环",
    "函数和作用域",
    "文件读写",
    "异常处理",
    "面向对象",
    "常用标准库",
    "基础算法和数据结构",
    "综合应用",
}


def fail(message: str) -> None:
    print(f"❌ {message}")
    sys.exit(1)


def load_data() -> dict:
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - command-line guard
        fail(f"无法读取 data.json：{exc}")


def main() -> None:
    data = load_data()
    chapters = data.get("chapters") or []
    if not chapters:
        fail("data.json 中没有 chapters")

    chapter_ids = {chapter.get("id") for chapter in chapters}
    seen_titles: set[str] = set()
    enhanced = []
    directions = Counter()
    levels = Counter()

    for chapter in chapters:
        if not chapter.get("id") or not chapter.get("title"):
            fail("章节缺少 id 或 title")
        if chapter.get("stageId") not in {stage.get("id") for stage in data.get("stages", [])}:
            fail(f"章节 {chapter.get('id')} 引用了不存在的 stageId")
        for index, exercise in enumerate(chapter.get("exercises") or []):
            if not exercise.get("text") or not exercise.get("level"):
                fail(f"{chapter.get('id')} 第 {index + 1} 题缺少 text/level")
            if exercise.get("source") == SOURCE:
                enhanced.append((chapter, index, exercise))

    if len(enhanced) < 40:
        fail(f"新增高质量题数量不足：{len(enhanced)}，至少需要 40 道")

    for chapter, index, exercise in enhanced:
        where = f"{chapter.get('id')} 第 {index + 1} 题"
        missing = [field for field in REQUIRED_FIELDS if field not in exercise]
        if missing:
            fail(f"{where} 缺少字段：{', '.join(missing)}")
        title = str(exercise.get("title") or "").strip()
        if len(title) < 4:
            fail(f"{where} title 过短")
        if title in seen_titles:
            fail(f"重复题目标题：{title}")
        seen_titles.add(title)
        if len(str(exercise.get("description") or "")) < 24:
            fail(f"{where} description 过短")
        if len(str(exercise.get("analysis") or "")) < 36:
            fail(f"{where} analysis 过短")
        if not str(exercise.get("starter") or "").strip():
            fail(f"{where} starter 为空")
        if not str(exercise.get("answerCode") or "").strip():
            fail(f"{where} answerCode 为空")
        if exercise.get("answer") != exercise.get("answerCode"):
            fail(f"{where} answer 与 answerCode 不一致")
        tags = exercise.get("tags")
        if not isinstance(tags, list) or len(tags) < 2:
            fail(f"{where} tags 至少需要 2 个")
        examples = exercise.get("examples")
        if not isinstance(examples, list) or not examples:
            fail(f"{where} examples 不能为空")
        tests = exercise.get("tests")
        if not isinstance(tests, list) or not tests:
            fail(f"{where} tests 不能为空")
        for test in tests:
            if not isinstance(test, dict) or not test.get("name") or not test.get("expected"):
                fail(f"{where} 存在不完整测试用例")
        direction = exercise.get("direction")
        if direction not in REQUIRED_DIRECTIONS:
            fail(f"{where} direction 不合法：{direction}")
        directions[direction] += 1
        levels[exercise.get("level")] += 1

    missing_directions = sorted(REQUIRED_DIRECTIONS - set(directions))
    if missing_directions:
        fail("新增题未覆盖方向：" + "、".join(missing_directions))
    for level in ["基础", "进阶", "挑战"]:
        if levels[level] < 8:
            fail(f"新增题中 {level} 题数量不足：{levels[level]}，至少需要 8 道")

    print("✅ 题库校验通过")
    print(f"新增高质量原创题：{len(enhanced)} 道")
    print("难度分布：" + ", ".join(f"{k}={v}" for k, v in sorted(levels.items())))
    print("方向覆盖：" + ", ".join(f"{k}={v}" for k, v in sorted(directions.items())))
    print(f"章节数：{len(chapter_ids)}")


if __name__ == "__main__":
    main()
