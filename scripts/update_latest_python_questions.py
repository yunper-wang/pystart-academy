#!/usr/bin/env python3
"""Fetch recent public Python practice-question signals and build an original update set.

The script intentionally does not copy third-party question text. It uses public
repository metadata as trend signals, then writes PyStart-compatible original
exercise drafts to data/latest_python_questions.json for review/import.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "latest_python_questions.json"
UA = "pystart-academy-question-updater/1.0"

def _date_filter(days_back: int = 30) -> str:
    """Dynamic date filter — always recent."""
    return (dt.date.today() - dt.timedelta(days=days_back)).isoformat()


def _build_searches() -> list[str]:
    d = _date_filter()
    return [
        f"python practice problems created:>{d}",
        f"python exercises questions created:>{d} language:Python",
        f"python quiz questions created:>{d}",
        f"python tutorial beginner created:>{d}",
        f"leetcode python solutions created:>{d}",
        f"python coding challenges created:>{d}",
    ]


SEARCHES = _build_searches()

TOPIC_RULES = [
    ("quiz", "字典和集合", "c12", ["字典", "集合", "统计"]),
    ("dsa", "列表进阶与批量数据处理", "c23", ["列表", "排序", "算法思维"]),
    ("leetcode", "列表进阶与批量数据处理", "c23", ["列表", "哈希表", "算法思维"]),
    ("case", "综合脚本项目：个人学习记录器", "c29", ["综合项目", "数据汇总", "报表"]),
    ("file", "文本文件小脚本实践", "c26", ["文件", "文本分析", "报告"]),
    ("exception", "异常处理与健壮程序", "c27", ["异常处理", "输入校验", "健壮性"]),
]

TEMPLATES = {
    "c12": {
        "title": "统计练习题标签热度",
        "level": "进阶",
        "description": "给定一组从公开练习仓库归纳出的标签，统计每个标签出现次数，并输出出现次数最多的标签。",
        "starter": "tags = ['list', 'dict', 'quiz', 'dict', 'quiz', 'dict']\n# 统计最高频标签\n",
        "answerCode": "tags = ['list', 'dict', 'quiz', 'dict', 'quiz', 'dict']\ncounts = {}\nfor tag in tags:\n    counts[tag] = counts.get(tag, 0) + 1\ntop = max(counts, key=counts.get)\nprint(f'{top}:{counts[top]}')\n",
        "expectedOutput": "dict:3",
        "direction": "结构化数据",
    },
    "c23": {
        "title": "整理算法练习完成记录",
        "level": "挑战",
        "description": "根据练习完成记录筛选已完成项目，按耗时从少到多排序，并输出题目名称列表。",
        "starter": "records = [{'name': 'Two Sum', 'done': True, 'minutes': 18}, {'name': 'Merge Lists', 'done': False, 'minutes': 25}, {'name': 'Valid Parentheses', 'done': True, 'minutes': 12}]\n# 输出已完成题目名称\n",
        "answerCode": "records = [{'name': 'Two Sum', 'done': True, 'minutes': 18}, {'name': 'Merge Lists', 'done': False, 'minutes': 25}, {'name': 'Valid Parentheses', 'done': True, 'minutes': 12}]\nfinished = [item for item in records if item['done']]\nfinished.sort(key=lambda item: item['minutes'])\nprint([item['name'] for item in finished])\n",
        "expectedOutput": "['Valid Parentheses', 'Two Sum']",
        "direction": "列表进阶",
    },
    "c26": {
        "title": "生成练习日志摘要",
        "level": "进阶",
        "description": "模拟读取多行练习日志，忽略空行后统计有效记录数，并输出摘要文本。",
        "starter": "log_text = 'print 基础\\n\\n列表 进阶\\n字典 进阶'\n# 统计有效行\n",
        "answerCode": "log_text = 'print 基础\\n\\n列表 进阶\\n字典 进阶'\nlines = [line.strip() for line in log_text.splitlines() if line.strip()]\nprint(f'有效记录：{len(lines)}')\n",
        "expectedOutput": "有效记录：3",
        "direction": "文本脚本",
    },
    "c27": {
        "title": "安全解析练习分数",
        "level": "进阶",
        "description": "把字符串分数转换为整数，遇到无法转换的数据时记为 0，最后输出平均分。",
        "starter": "raw_scores = ['90', 'bad', '75']\n# 安全转换并计算平均分\n",
        "answerCode": "raw_scores = ['90', 'bad', '75']\nscores = []\nfor item in raw_scores:\n    try:\n        scores.append(int(item))\n    except ValueError:\n        scores.append(0)\nprint(sum(scores) // len(scores))\n",
        "expectedOutput": "55",
        "direction": "健壮程序",
    },
    "c29": {
        "title": "汇总题库练习进度",
        "level": "挑战",
        "description": "根据每日练习记录统计完成题数和总用时，输出适合作为学习记录器首页的摘要。",
        "starter": "daily = [{'date': '2026-05-11', 'count': 3, 'minutes': 42}, {'date': '2026-05-12', 'count': 4, 'minutes': 55}]\n# 输出汇总摘要\n",
        "answerCode": "daily = [{'date': '2026-05-11', 'count': 3, 'minutes': 42}, {'date': '2026-05-12', 'count': 4, 'minutes': 55}]\ntotal_count = sum(item['count'] for item in daily)\ntotal_minutes = sum(item['minutes'] for item in daily)\nprint(f'完成{total_count}题，用时{total_minutes}分钟')\n",
        "expectedOutput": "完成7题，用时97分钟",
        "direction": "学习记录项目",
    },
}


def gh_search(query: str) -> list[dict]:
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": query, "sort": "updated", "order": "desc", "per_page": 8}
    )
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.load(resp).get("items", [])


def classify(text: str) -> tuple[str, str, list[str]]:
    lower = text.lower()
    for needle, _topic, cid, tags in TOPIC_RULES:
        if needle in lower:
            return cid, TEMPLATES[cid]["direction"], tags
    return "c23", TEMPLATES["c23"]["direction"], ["Python", "练习", "问题解决"]


def make_exercise(cid: str, tags: list[str], idx: int, signals: list[dict]) -> dict:
    base = dict(TEMPLATES[cid])
    qid = f"latest-{dt.date.today().isoformat()}-{idx:02d}"
    signal_names = [s["full_name"] for s in signals[:3]]
    return {
        "id": qid,
        "chapterId": cid,
        "level": base["level"],
        "title": base["title"],
        "text": f"{base['title']}：{base['description']}",
        "description": base["description"],
        "hint": "先把固定样例数据跑通，再考虑如何替换成真实输入。",
        "starter": base["starter"],
        "expectedOutput": base["expectedOutput"],
        "answer": base["answerCode"],
        "answerCode": base["answerCode"],
        "taskGoal": base["description"],
        "analysis": "本题由近期公开 Python 练习仓库的主题趋势启发，但题干、数据和参考答案均为 PyStart 原创内容，适合补充到对应章节。",
        "tags": tags,
        "examples": [{"input": "题目内置固定数据", "output": base["expectedOutput"]}],
        "tests": [{"name": "参考答案输出校验", "expected": base["expectedOutput"]}],
        "direction": base["direction"],
        "source": "pystart-web-trend-original-v1",
        "qualityNotes": "基于公开仓库元数据趋势生成；未复制第三方题目正文或答案。",
        "webSignals": signal_names,
    }


def main() -> None:
    all_items = []
    for query in SEARCHES:
        try:
            for item in gh_search(query):
                text = " ".join([item.get("full_name", ""), item.get("description") or ""])
                cid, direction, tags = classify(text)
                all_items.append({
                    "full_name": item["full_name"],
                    "url": item["html_url"],
                    "updated_at": item["updated_at"],
                    "description": item.get("description"),
                    "chapterId": cid,
                    "direction": direction,
                    "tags": tags,
                })
        except Exception as exc:
            all_items.append({"error": str(exc), "query": query})

    grouped: dict[str, list[dict]] = {}
    for item in all_items:
        if "chapterId" in item:
            grouped.setdefault(item["chapterId"], []).append(item)

    exercises = []
    for idx, (cid, signals) in enumerate(sorted(grouped.items())[:5], 1):
        exercises.append(make_exercise(cid, signals[0]["tags"], idx, signals))

    payload = {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sourcePolicy": "Use public web metadata as trend signals only; do not copy third-party question text.",
        "signals": all_items[:30],
        "exercises": exercises,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} with {len(exercises)} original exercise drafts from {len(all_items)} signals")


if __name__ == "__main__":
    main()
