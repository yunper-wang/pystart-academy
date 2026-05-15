#!/usr/bin/env python3
"""Daily Python question bank updater.

Fetches trend signals from multiple sources (GitHub repos, RSS feeds, popular
Python exercise sites), generates original PyStart-compatible exercises, and
imports them into the question bank.

Designed to run via GitHub Actions daily cron.

Sources:
  1. GitHub Search API — recent Python practice/exercise repos
  2. RSS Feeds — Real Python, Planet Python, Python Weekly
  3. Web scraping — Popular Python exercise sites (W3Schools, GeeksForGeeks, etc.)

Output:
  - data/latest_python_questions.json  (raw trend signals + drafts)
  - data.json                          (updated question bank)
  - Git commit with changes (if any)
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "latest_python_questions.json"
DATA_FILE = ROOT / "data.json"
UA = "pystart-academy-daily-updater/2.0"

# ─── GitHub Search Queries ──────────────────────────────────────────

def get_date_filter(days_back: int = 30) -> str:
    """Dynamic date filter: repos created in the last N days."""
    date = (dt.date.today() - dt.timedelta(days=days_back)).isoformat()
    return f"created:>{date}"


def get_github_queries() -> list[str]:
    date_filter = get_date_filter(30)
    return [
        f"python practice problems {date_filter}",
        f"python exercises questions {date_filter} language:Python",
        f"python quiz questions {date_filter}",
        f"python coding challenges {date_filter} language:Python",
        f"python beginner exercises {date_filter}",
        f"leetcode solutions python {date_filter}",
        f"python interview questions {date_filter}",
        f"python algorithms {date_filter} language:Python",
    ]


# ─── Topic → Chapter Mapping ───────────────────────────────────────

TOPIC_RULES = [
    # (keyword, topic, chapter_id, tags)
    ("quiz", "字典和集合", "c12", ["字典", "集合", "统计"]),
    ("dict", "字典和集合", "c12", ["字典", "键值对", "统计"]),
    ("dsa", "列表进阶与批量数据处理", "c23", ["列表", "排序", "算法思维"]),
    ("leetcode", "列表进阶与批量数据处理", "c23", ["列表", "哈希表", "算法思维"]),
    ("algorithm", "列表进阶与批量数据处理", "c23", ["算法", "数据结构", "列表"]),
    ("case", "综合脚本项目：个人学习记录器", "c29", ["综合项目", "数据汇总", "报表"]),
    ("file", "文本文件小脚本实践", "c26", ["文件", "文本分析", "报告"]),
    ("exception", "异常处理与健壮程序", "c27", ["异常处理", "输入校验", "健壮性"]),
    ("oop", "类和对象", "c19", ["面向对象", "类", "继承"]),
    ("class", "类和对象", "c19", ["类", "对象", "方法"]),
    ("function", "函数定义和参数", "c13", ["函数", "参数", "返回值"]),
    ("recursion", "函数定义和参数", "c13", ["递归", "函数", "算法"]),
    ("loop", "for 循环和 while 循环", "c08", ["循环", "for", "while"]),
    ("string", "字符串常用操作", "c10", ["字符串", "文本处理", "格式化"]),
    ("list", "列表和元组", "c11", ["列表", "元组", "索引"]),
    ("sort", "列表进阶与批量数据处理", "c23", ["排序", "列表", "算法"]),
    ("search", "列表进阶与批量数据处理", "c23", ["搜索", "二分查找", "列表"]),
    ("beginner", "Python 是什么", "c01", ["入门", "基础", "Python"]),
    ("input", "输入和输出", "c05", ["输入", "输出", "print"]),
    ("operator", "运算符", "c06", ["运算符", "算术", "比较"]),
    ("condition", "条件判断", "c07", ["条件", "if", "判断"]),
    ("module", "模块导入", "c15", ["模块", "import", "标准库"]),
    ("datetime", "日期、时间与简单自动化脚本", "c28", ["日期", "时间", "自动化"]),
    ("error", "异常处理与健壮程序", "c27", ["异常", "错误处理", "try-except"]),
    ("web", "综合脚本项目：个人学习记录器", "c29", ["网络", "API", "数据抓取"]),
    ("data", "字典进阶与结构化数据", "c24", ["数据", "字典", "结构化"]),
    ("project", "综合复盘与小型脚本开发流程", "c30", ["项目", "综合", "脚本"]),
]

# ─── Exercise Templates (Original Content) ─────────────────────────

TEMPLATES = {
    "c01": {
        "title": "Python 版本特性速查",
        "level": "基础",
        "description": "根据当前 Python 版本号，输出主版本号和次版本号，并判断是否为 Python 3。",
        "starter": "import sys\nversion = sys.version_info\n# 输出版本信息\n",
        "answerCode": "import sys\nversion = sys.version_info\nprint(f'主版本：{version.major}')\nprint(f'次版本：{version.minor}')\nprint(f'Python 3：{version.major == 3}')\n",
        "expectedOutput": "主版本：3\n次版本：12\nPython 3：True",
        "direction": "Python 基础",
    },
    "c05": {
        "title": "格式化用户信息输入",
        "level": "基础",
        "description": "模拟接收用户输入的姓名和年龄，格式化输出自我介绍。",
        "starter": "name = '小明'\nage = 18\n# 输出格式化的自我介绍\n",
        "answerCode": "name = '小明'\nage = 18\nprint(f'大家好，我叫{name}，今年{age}岁。')\nprint(f'十年后我{age + 10}岁。')\n",
        "expectedOutput": "大家好，我叫小明，今年18岁。\n十年后我28岁。",
        "direction": "输入输出",
    },
    "c06": {
        "title": "温度转换计算器",
        "level": "基础",
        "description": "将摄氏温度转换为华氏温度和开尔文温度，输出三种温度的对照表。",
        "starter": "celsius = 25\n# 转换为华氏和开尔文\n",
        "answerCode": "celsius = 25\nfahrenheit = celsius * 9 / 5 + 32\nkelvin = celsius + 273.15\nprint(f'摄氏：{celsius}°C')\nprint(f'华氏：{fahrenheit}°F')\nprint(f'开尔文：{kelvin}K')\n",
        "expectedOutput": "摄氏：25°C\n华氏：77.0°F\n开尔文：298.15K",
        "direction": "运算符应用",
    },
    "c07": {
        "title": "成绩等级判定器",
        "level": "进阶",
        "description": "根据分数判定等级：90+优秀、80+良好、60+及格、60以下不及格。",
        "starter": "score = 85\n# 判定等级\n",
        "answerCode": "score = 85\nif score >= 90:\n    level = '优秀'\nelif score >= 80:\n    level = '良好'\nelif score >= 60:\n    level = '及格'\nelse:\n    level = '不及格'\nprint(f'{score}分 → {level}')\n",
        "expectedOutput": "85分 → 良好",
        "direction": "条件判断",
    },
    "c08": {
        "title": "九九乘法表生成器",
        "level": "进阶",
        "description": "使用嵌套循环生成完整的九九乘法表。",
        "starter": "# 生成九九乘法表\n",
        "answerCode": "for i in range(1, 10):\n    for j in range(1, i + 1):\n        print(f'{j}×{i}={i*j}', end='\\t')\n    print()\n",
        "expectedOutput": "1×1=1\t\n1×2=2\t2×2=4\t\n1×3=3\t2×3=6\t3×3=9\t",
        "direction": "循环练习",
    },
    "c10": {
        "title": "文本清洗与统计",
        "level": "进阶",
        "description": "清洗一段文本：去除多余空格、统计单词数、找出最长单词。",
        "starter": "text = '  Python is   a powerful  programming language  '\n# 清洗并统计\n",
        "answerCode": "text = '  Python is   a powerful  programming language  '\ncleaned = ' '.join(text.split())\nwords = cleaned.split()\nprint(f'清洗后：{cleaned}')\nprint(f'单词数：{len(words)}')\nlongest = max(words, key=len)\nprint(f'最长单词：{longest}（{len(longest)}字符）')\n",
        "expectedOutput": "清洗后：Python is a powerful programming language\n单词数：6\n最长单词：programming（11字符）",
        "direction": "字符串操作",
    },
    "c11": {
        "title": "列表去重与排序",
        "level": "进阶",
        "description": "对包含重复元素的列表去重，并按从小到大排序。",
        "starter": "numbers = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]\n# 去重并排序\n",
        "answerCode": "numbers = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]\nunique = list(set(numbers))\nunique.sort()\nprint(f'去重排序后：{unique}')\nprint(f'原始长度：{len(numbers)}')\nprint(f'去重后长度：{len(unique)}')\n",
        "expectedOutput": "去重排序后：[1, 2, 3, 4, 5, 6, 9]\n原始长度：11\n去重后长度：7",
        "direction": "列表操作",
    },
    "c12": {
        "title": "统计练习题标签热度",
        "level": "进阶",
        "description": "给定一组从公开练习仓库归纳出的标签，统计每个标签出现次数，并输出出现次数最多的标签。",
        "starter": "tags = ['list', 'dict', 'quiz', 'dict', 'quiz', 'dict']\n# 统计最高频标签\n",
        "answerCode": "tags = ['list', 'dict', 'quiz', 'dict', 'quiz', 'dict']\ncounts = {}\nfor tag in tags:\n    counts[tag] = counts.get(tag, 0) + 1\ntop = max(counts, key=counts.get)\nprint(f'{top}:{counts[top]}')\n",
        "expectedOutput": "dict:3",
        "direction": "结构化数据",
    },
    "c13": {
        "title": "自定义排序函数",
        "level": "进阶",
        "description": "编写一个函数，支持按自定义规则对列表排序（如按字符串长度）。",
        "starter": "words = ['python', 'is', 'awesome', 'hi', 'code']\n# 按长度排序\n",
        "answerCode": "def sort_by_length(words):\n    return sorted(words, key=len)\n\nwords = ['python', 'is', 'awesome', 'hi', 'code']\nresult = sort_by_length(words)\nprint(result)\n",
        "expectedOutput": "['hi', 'is', 'code', 'python', 'awesome']",
        "direction": "函数应用",
    },
    "c14": {
        "title": "多返回值函数",
        "level": "进阶",
        "description": "编写一个函数同时返回列表的最大值、最小值和平均值。",
        "starter": "numbers = [23, 45, 12, 67, 34, 89, 56]\n# 返回统计值\n",
        "answerCode": "def stats(numbers):\n    return max(numbers), min(numbers), sum(numbers) / len(numbers)\n\nnumbers = [23, 45, 12, 67, 34, 89, 56]\nmaximum, minimum, average = stats(numbers)\nprint(f'最大值：{maximum}')\nprint(f'最小值：{minimum}')\nprint(f'平均值：{average:.1f}')\n",
        "expectedOutput": "最大值：89\n最小值：12\n平均值：46.6",
        "direction": "返回值",
    },
    "c15": {
        "title": "标准库实用工具",
        "level": "进阶",
        "description": "使用 collections.Counter 统计字符出现频率，输出前3高频字符。",
        "starter": "from collections import Counter\ntext = 'abracadabra'\n# 统计字符频率\n",
        "answerCode": "from collections import Counter\ntext = 'abracadabra'\nfreq = Counter(text)\ntop3 = freq.most_common(3)\nfor char, count in top3:\n    print(f'{char}: {count}次')\n",
        "expectedOutput": "a: 5次\nb: 2次\nr: 2次",
        "direction": "模块应用",
    },
    "c16": {
        "title": "CSV 数据读取与统计",
        "level": "挑战",
        "description": "模拟读取 CSV 格式的成绩数据，计算每科平均分。",
        "starter": "csv_data = '''name,math,english,science\n小明,90,85,92\n小红,88,92,78\n小刚,76,80,85'''\n# 解析并统计\n",
        "answerCode": "csv_data = '''name,math,english,science\n小明,90,85,92\n小红,88,92,78\n小刚,76,80,85'''\nlines = csv_data.strip().split('\\n')\nheaders = lines[0].split(',')[1:]\nfor i, subject in enumerate(headers):\n    scores = [int(line.split(',')[i + 1]) for line in lines[1:]]\n    avg = sum(scores) / len(scores)\n    print(f'{subject}: 平均分 {avg:.1f}')\n",
        "expectedOutput": "math: 平均分 84.7\nenglish: 平均分 85.7\nscience: 平均分 85.0",
        "direction": "文件处理",
    },
    "c17": {
        "title": "安全数据解析器",
        "level": "进阶",
        "description": "安全地解析 JSON 字符串，处理可能的格式错误。",
        "starter": "import json\ndata_list = ['{\"name\": \"test\"}', 'invalid json', '{\"value\": 42}']\n# 安全解析\n",
        "answerCode": "import json\ndata_list = ['{\"name\": \"test\"}', 'invalid json', '{\"value\": 42}']\nfor raw in data_list:\n    try:\n        obj = json.loads(raw)\n        print(f'解析成功：{obj}')\n    except json.JSONDecodeError as e:\n        print(f'解析失败：{e}')\n",
        "expectedOutput": "解析成功：{'name': 'test'}\n解析失败：Expecting value: line 1 column 1 (char 0)\n解析成功：{'value': 42}",
        "direction": "异常处理",
    },
    "c18": {
        "title": "面向对象：学生类",
        "level": "挑战",
        "description": "定义一个 Student 类，包含姓名、成绩属性和计算平均分的方法。",
        "starter": "# 定义 Student 类\n",
        "answerCode": "class Student:\n    def __init__(self, name, scores):\n        self.name = name\n        self.scores = scores\n    \n    def average(self):\n        return sum(self.scores) / len(self.scores)\n    \n    def __str__(self):\n        return f'{self.name}: 平均分{self.average():.1f}'\n\ns = Student('小明', [90, 85, 92])\nprint(s)\nprint(f'最高分：{max(s.scores)}')\n",
        "expectedOutput": "小明: 平均分89.0\n最高分：92",
        "direction": "面向对象",
    },
    "c19": {
        "title": "继承与多态示例",
        "level": "挑战",
        "description": "实现一个简单的形状类继承体系，展示多态特性。",
        "starter": "# 实现 Shape 基类和 Circle、Rectangle 子类\n",
        "answerCode": "import math\nclass Shape:\n    def area(self):\n        return 0\nclass Circle(Shape):\n    def __init__(self, r):\n        self.r = r\n    def area(self):\n        return math.pi * self.r ** 2\nclass Rectangle(Shape):\n    def __init__(self, w, h):\n        self.w, self.h = w, h\n    def area(self):\n        return self.w * self.h\nshapes = [Circle(5), Rectangle(4, 6)]\nfor s in shapes:\n    print(f'{type(s).__name__}: {s.area():.1f}')\n",
        "expectedOutput": "Circle: 78.5\nRectangle: 24.0",
        "direction": "类与继承",
    },
    "c20": {
        "title": "综合复习：数据处理流水线",
        "level": "挑战",
        "description": "综合运用列表、字典、函数等知识，实现一个简单的数据处理流水线。",
        "starter": "# 实现数据清洗→统计→排序的流水线\n",
        "answerCode": "data = ['Alice:90', 'Bob:85', 'Charlie:92', 'David:78', 'Eve:88']\nstudents = []\nfor item in data:\n    name, score = item.split(':')\n    students.append({'name': name, 'score': int(score)})\nstudents.sort(key=lambda s: s['score'], reverse=True)\navg = sum(s['score'] for s in students) / len(students)\nprint(f'平均分：{avg:.1f}')\nfor s in students:\n    mark = '✓' if s['score'] >= avg else '✗'\n    print(f\"{s['name']}: {s['score']} {mark}\")\n",
        "expectedOutput": "平均分：86.6\nCharlie: 92 ✓\nAlice: 90 ✓\nEve: 88 ✓\nBob: 85 ✗\nDavid: 78 ✗",
        "direction": "综合练习",
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
    "c24": {
        "title": "嵌套字典数据提取",
        "level": "挑战",
        "description": "从嵌套字典中提取特定信息，处理可能缺失的键。",
        "starter": "users = {\n    'u001': {'name': 'Alice', 'scores': [90, 85, 92]},\n    'u002': {'name': 'Bob'},\n    'u003': {'name': 'Charlie', 'scores': [78, 88]}\n}\n# 安全提取每个人的成绩信息\n",
        "answerCode": "users = {\n    'u001': {'name': 'Alice', 'scores': [90, 85, 92]},\n    'u002': {'name': 'Bob'},\n    'u003': {'name': 'Charlie', 'scores': [78, 88]}\n}\nfor uid, info in users.items():\n    name = info.get('name', '未知')\n    scores = info.get('scores', [])\n    if scores:\n        avg = sum(scores) / len(scores)\n        print(f'{name}: 平均分 {avg:.1f}（{len(scores)}科）')\n    else:\n        print(f'{name}: 暂无成绩')\n",
        "expectedOutput": "Alice: 平均分 89.0（3科）\nBob: 暂无成绩\nCharlie: 平均分 83.0（2科）",
        "direction": "字典进阶",
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
    "c28": {
        "title": "日期计算与格式化",
        "level": "进阶",
        "description": "计算两个日期之间的天数差，并格式化输出。",
        "starter": "from datetime import date\nstart = date(2026, 1, 1)\nend = date(2026, 5, 15)\n# 计算天数差\n",
        "answerCode": "from datetime import date\nstart = date(2026, 1, 1)\nend = date(2026, 5, 15)\ndelta = end - start\nprint(f'从 {start} 到 {end}')\nprint(f'相差 {delta.days} 天')\nprint(f'约 {delta.days // 7} 周 {delta.days % 7} 天')\n",
        "expectedOutput": "从 2026-01-01 到 2026-05-15\n相差 134 天\n约 19 周 1 天",
        "direction": "日期时间",
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
    "c30": {
        "title": "脚本开发流程演练",
        "level": "挑战",
        "description": "按照规范的脚本开发流程，编写一个命令行参数解析器。",
        "starter": "import sys\n# 解析命令行参数\n",
        "answerCode": "import sys\nargs = sys.argv[1:]\nif not args:\n    print('用法: python script.py <名字> [年龄]')\nelse:\n    name = args[0]\n    age = args[1] if len(args) > 1 else '未知'\n    print(f'姓名：{name}')\n    print(f'年龄：{age}')\n",
        "expectedOutput": "姓名：Alice\n年龄：未知",
        "direction": "脚本开发",
    },
}

# ─── RSS Feeds to Check ────────────────────────────────────────────

RSS_FEEDS = [
    ("Real Python", "https://realpython.com/atom.xml"),
    ("Planet Python", "https://planetpython.org/rss20.xml"),
    ("Python Insider", "https://blog.python.org/feeds/posts/default?alt=rss"),
]


# ─── Source Adapters ────────────────────────────────────────────────

def gh_search(query: str) -> list[dict]:
    """Search GitHub repositories."""
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": query, "sort": "updated", "order": "desc", "per_page": 10}
    )
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": UA,
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp).get("items", [])


def fetch_rss(url: str, max_entries: int = 20) -> list[dict]:
    """Fetch and parse RSS/Atom feed."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        xml_text = resp.read().decode("utf-8", errors="replace")

    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    # Try RSS 2.0
    for item in root.iter("item"):
        if len(items) >= max_entries:
            break
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        if title:
            items.append({"title": title, "link": link, "description": desc[:500]})

    # Try Atom if RSS yielded nothing
    if not items:
        ns = "{http://www.w3.org/2005/Atom}"
        for entry in root.iter(f"{ns}entry"):
            if len(items) >= max_entries:
                break
            title = (entry.findtext(f"{ns}title") or "").strip()
            link_elem = entry.find(f"{ns}link")
            link = link_elem.get("href", "") if link_elem is not None else ""
            summary = (entry.findtext(f"{ns}summary") or "").strip()
            if title:
                items.append({"title": title, "link": link, "description": summary[:500]})

    return items


def fetch_popular_python_sites() -> list[dict]:
    """Fetch exercise topics from popular Python learning sites."""
    sites = [
        "https://www.w3schools.com/python/python_exercises.asp",
        "https://www.practicepython.org/",
        "https://codingbat.com/python",
    ]
    all_items = []
    for url in sites:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            # Extract titles from h2/h3 tags
            titles = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", html, re.IGNORECASE)
            for title in titles[:10]:
                clean = re.sub(r"<[^>]+>", "", title).strip()
                if clean and len(clean) > 3:
                    all_items.append({
                        "title": clean,
                        "link": url,
                        "source": url.split("//")[1].split("/")[0],
                    })
        except Exception:
            continue
    return all_items


# ─── Classification ─────────────────────────────────────────────────

def classify(text: str) -> tuple[str, str, list[str]]:
    """Classify a text into chapter, direction, and tags."""
    lower = text.lower()
    for needle, _topic, cid, tags in TOPIC_RULES:
        if needle in lower:
            return cid, TEMPLATES[cid]["direction"], tags
    return "c23", TEMPLATES["c23"]["direction"], ["Python", "练习", "问题解决"]


# ─── Exercise Generation ────────────────────────────────────────────

def make_exercise(cid: str, tags: list[str], idx: int, signals: list[dict]) -> dict:
    """Create an original exercise inspired by trend signals."""
    base = dict(TEMPLATES[cid])
    today = dt.date.today().isoformat()
    qid = f"latest-{today}-{idx:02d}"
    signal_names = [s.get("full_name") or s.get("title", "") for s in signals[:3]]
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
        "source": "pystart-web-trend-original-v2",
        "qualityNotes": "基于公开仓库元数据和 RSS 订阅趋势生成；未复制第三方题目正文或答案。",
        "webSignals": signal_names,
    }


# ─── Main Update Logic ─────────────────────────────────────────────

def main() -> dict:
    """Run the daily update pipeline."""
    all_signals = []
    errors = []

    # 1. GitHub Search
    print("📡 Fetching GitHub signals...")
    for query in get_github_queries():
        try:
            for item in gh_search(query):
                text = " ".join([
                    item.get("full_name", ""),
                    item.get("description") or "",
                ])
                all_signals.append({
                    "source": "github",
                    "full_name": item.get("full_name", ""),
                    "url": item.get("html_url", ""),
                    "updated_at": item.get("updated_at", ""),
                    "description": item.get("description"),
                    "text": text,
                })
        except Exception as exc:
            errors.append(f"GitHub: {query[:40]}... → {exc}")

    # 2. RSS Feeds
    print("📡 Fetching RSS feeds...")
    for name, url in RSS_FEEDS:
        try:
            items = fetch_rss(url)
            for item in items:
                all_signals.append({
                    "source": "rss",
                    "full_name": f"{name}: {item['title']}",
                    "url": item.get("link", ""),
                    "description": item.get("description"),
                    "text": f"{item['title']} {item.get('description', '')}",
                })
        except Exception as exc:
            errors.append(f"RSS: {name} → {exc}")

    # 3. Popular Python sites
    print("📡 Fetching popular Python sites...")
    try:
        site_items = fetch_popular_python_sites()
        for item in site_items:
            all_signals.append({
                "source": "web",
                "full_name": item["title"],
                "url": item.get("link", ""),
                "description": item["title"],
                "text": item["title"],
            })
    except Exception as exc:
        errors.append(f"Web: popular sites → {exc}")

    # Deduplicate signals by text similarity
    seen_texts = set()
    unique_signals = []
    for sig in all_signals:
        key = (sig.get("text", "") or "")[:100].lower().strip()
        if key and key not in seen_texts:
            seen_texts.add(key)
            unique_signals.append(sig)

    print(f"📊 Collected {len(unique_signals)} unique signals from {len(all_signals)} total")

    # 4. Classify signals into chapters
    grouped: dict[str, list[dict]] = {}
    for sig in unique_signals:
        text = sig.get("text", "") or ""
        cid, _direction, tags = classify(text)
        sig["chapterId"] = cid
        sig["tags"] = tags
        grouped.setdefault(cid, []).append(sig)

    # 5. Generate exercises (one per chapter, up to 10 chapters)
    exercises = []
    for idx, (cid, signals) in enumerate(sorted(grouped.items())[:10], 1):
        exercises.append(make_exercise(cid, signals[0]["tags"], idx, signals))

    # 6. Write output
    payload = {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sourcePolicy": "Use public web metadata as trend signals only; do not copy third-party question text.",
        "signalsCount": len(unique_signals),
        "exercisesCount": len(exercises),
        "sources": {
            "github": len([s for s in unique_signals if s.get("source") == "github"]),
            "rss": len([s for s in unique_signals if s.get("source") == "rss"]),
            "web": len([s for s in unique_signals if s.get("source") == "web"]),
        },
        "errors": errors,
        "signals": unique_signals[:50],
        "exercises": exercises,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Wrote {OUT.relative_to(ROOT)} with {len(exercises)} exercise drafts")

    # 7. Import into question bank
    import subprocess
    imported_count = 0
    if exercises:
        try:
            import_script = ROOT / "scripts" / "import_latest_python_questions.py"
            result = subprocess.run(
                [sys.executable, str(import_script)],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                imported_count = len(exercises)
                print(f"✅ Imported {imported_count} exercises into question bank")
                if result.stdout.strip():
                    print(f"   Import output: {result.stdout.strip()[:200]}")
            else:
                # Import script may fail if chapters don't have existing exercises
                # This is non-fatal — the drafts are still saved in latest_python_questions.json
                err_msg = result.stderr.strip()[:300] if result.stderr else result.stdout.strip()[:300]
                errors.append(f"Import: {err_msg}")
                print(f"⚠️ Import script error (drafts still saved): {err_msg}")
        except Exception as exc:
            errors.append(f"Import: {exc}")
            print(f"⚠️ Import error: {exc}")

    result = {
        "date": dt.date.today().isoformat(),
        "signals_collected": len(unique_signals),
        "exercises_generated": len(exercises),
        "exercises_imported": imported_count,
        "errors": errors,
        "sources": payload["sources"],
    }
    print(f"\n📋 Summary: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result


if __name__ == "__main__":
    result = main()
    if result.get("errors"):
        print(f"\n⚠️ Completed with {len(result['errors'])} errors")
        sys.exit(0)  # Don't fail the CI for non-critical errors
    else:
        print("\n✅ All done!")
