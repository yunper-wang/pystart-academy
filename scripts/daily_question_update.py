#!/usr/bin/env python3
"""Daily PyStart Academy question bank updater — all-in-one pipeline.

Fetches Python practice signals from multiple web sources (GitHub Search API,
RSS feeds, popular exercise sites), generates original exercises inspired by
trends, and imports them into the curated-v2 question bank.

Zero-dependency: uses only Python stdlib (urllib, xml, html.parser, json, re).
Designed to run via GitHub Actions or local cron.

Usage:
    python3 scripts/daily_question_update.py           # full pipeline
    python3 scripts/daily_question_update.py --dry-run  # fetch + generate, skip import
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
LATEST_FILE = ROOT / "data" / "latest_python_questions.json"
QB_FILE = ROOT / "question_banks" / "curated-v2" / "question_bank.json"
BACKUP_DIR = ROOT / "question_banks" / "curated-v2" / "backups"
MAX_BACKUPS = 5
UA = "pystart-academy-daily-updater/2.0"
DRY_RUN = "--dry-run" in sys.argv

# ---------------------------------------------------------------------------
# Chapter topics — all 30 chapters
# ---------------------------------------------------------------------------
TOPICS = {
    "c01": ("Python 是什么", "Python 基础语法", ["print", "脚本结构", "注释"]),
    "c02": ("开发环境和代码运行方式", "代码运行与调试", ["运行顺序", "注释", "调试"]),
    "c03": ("变量与命名规则", "变量与命名", ["变量", "命名", "赋值"]),
    "c04": ("数字、字符串、布尔值", "基础数据类型", ["数字", "字符串", "布尔值"]),
    "c05": ("输入和输出", "输入输出", ["输出", "字符串格式化", "交互思维"]),
    "c06": ("运算符", "运算符", ["算术运算", "比较运算", "逻辑运算"]),
    "c07": ("条件判断", "条件判断", ["if", "elif", "else"]),
    "c08": ("for 循环和 while 循环", "循环", ["for", "while", "累计"]),
    "c09": ("break 和 continue", "循环控制", ["break", "continue", "搜索"]),
    "c10": ("字符串常用操作", "字符串", ["strip", "split", "join"]),
    "c11": ("列表和元组", "列表与元组", ["列表", "切片", "元组"]),
    "c12": ("字典和集合", "字典与集合", ["字典", "集合", "统计"]),
    "c13": ("函数定义和参数", "函数", ["参数", "默认值", "职责拆分"]),
    "c14": ("返回值", "函数返回值", ["return", "多返回值", "组合调用"]),
    "c15": ("模块导入", "模块", ["import", "math", "random"]),
    "c16": ("文件读取和写入", "文件读写", ["读取", "写入", "with"]),
    "c17": ("异常处理", "异常处理", ["try", "except", "健壮性"]),
    "c18": ("面向对象基础", "面向对象", ["class", "属性", "方法"]),
    "c19": ("类和对象", "类与对象", ["__init__", "实例", "对象列表"]),
    "c20": ("综合复习与学习建议", "复习与总结", ["复盘", "统计", "建议"]),
    "c21": ("代码组织与脚本编写习惯", "脚本组织", ["main", "函数组合", "可读性"]),
    "c22": ("输入处理与数据清洗基础", "数据清洗", ["strip", "校验", "标准化"]),
    "c23": ("列表进阶与批量数据处理", "列表进阶", ["筛选", "排序", "推导式"]),
    "c24": ("字典进阶与结构化数据", "结构化数据", ["嵌套字典", "汇总", "查询"]),
    "c25": ("函数拆分与小程序结构", "函数拆分", ["小程序结构", "纯函数", "组合"]),
    "c26": ("文本文件小脚本实践", "文本脚本", ["文本分析", "文件", "报告"]),
    "c27": ("异常处理与健壮程序", "健壮程序", ["容错", "默认值", "边界"]),
    "c28": ("日期、时间与简单自动化脚本", "日期时间", ["datetime", "日志", "打卡"]),
    "c29": ("综合脚本项目：个人学习记录器", "学习记录项目", ["记录", "汇总", "报告"]),
    "c30": ("综合复盘与小型脚本开发流程", "综合脚本流程", ["需求拆分", "项目流程", "交付"]),
}

# ---------------------------------------------------------------------------
# Signal classification rules
# ---------------------------------------------------------------------------
TOPIC_RULES = [
    # (keyword, chapterId)
    ("print", "c01"), ("hello world", "c01"), ("beginner", "c03"),
    ("variable", "c03"), ("string", "c04"), ("input", "c05"),
    ("operator", "c06"), ("condition", "c07"), ("if else", "c07"),
    ("loop", "c08"), ("for loop", "c08"), ("while", "c08"),
    ("break", "c09"), ("continue", "c09"),
    ("string method", "c10"), ("strip", "c10"), ("split", "c10"),
    ("list", "c11"), ("tuple", "c11"), ("slice", "c11"),
    ("dict", "c12"), ("dictionary", "c12"), ("set", "c12"),
    ("function", "c13"), ("parameter", "c13"), ("argument", "c13"),
    ("return", "c14"), ("module", "c15"), ("import", "c15"),
    ("file", "c16"), ("read write", "c16"), ("open", "c16"),
    ("exception", "c17"), ("try except", "c17"), ("error handling", "c17"),
    ("class", "c18"), ("oop", "c18"), ("object", "c19"),
    ("review", "c20"), ("quiz", "c12"),
    ("script", "c21"), ("clean code", "c21"),
    ("data clean", "c22"), ("validation", "c22"),
    ("sort", "c23"), ("filter", "c23"), ("comprehension", "c23"),
    ("nested", "c24"), ("json", "c24"), ("structured", "c24"),
    ("refactor", "c25"), ("decompose", "c25"),
    ("text file", "c26"), ("log", "c26"), ("report", "c26"),
    ("robust", "c27"), ("edge case", "c27"),
    ("datetime", "c28"), ("automation", "c28"), ("schedule", "c28"),
    ("project", "c29"), ("tracker", "c29"), ("record", "c29"),
    ("pipeline", "c30"), ("workflow", "c30"),
    ("leetcode", "c23"), ("dsa", "c23"), ("algorithm", "c23"),
]

# ---------------------------------------------------------------------------
# Exercise templates — multi-variant pool per chapter for daily rotation
# ---------------------------------------------------------------------------
POOL: dict[str, list[dict]] = {}


def _pool(chapter_id: str, variants: list[dict]):
    """Helper to register template variants."""
    POOL[chapter_id] = variants


_pool("c01", [
    {"title": "用 print 输出学习目标", "level": "基础", "description": "用 print 输出'掌握 Python 基础'，体验最简脚本。", "starter": "# 输出学习目标\n", "expectedOutput": "掌握 Python 基础", "answerCode": "print(\"掌握 Python 基础\")\n", "direction": "Python 基础语法"},
    {"title": "输出课程欢迎信息", "level": "基础", "description": "用 print 输出'欢迎来到 PyStart Academy'。", "starter": "# 输出欢迎信息\n", "expectedOutput": "欢迎来到 PyStart Academy", "answerCode": "print(\"欢迎来到 PyStart Academy\")\n", "direction": "Python 基础语法"},
    {"title": "多行输出学习路线", "level": "基础", "description": "用三条 print 语句分别输出'基础→进阶→挑战'。", "starter": "# 输出学习路线\n", "expectedOutput": "基础\n进阶\n挑战", "answerCode": "print(\"基础\")\nprint(\"进阶\")\nprint(\"挑战\")\n", "direction": "Python 基础语法"},
])

_pool("c02", [
    {"title": "输出脚本运行环境信息", "level": "基础", "description": "用 print 输出当前 Python 版本信息。", "starter": "import sys\n# 输出版本信息\n", "expectedOutput": "Python", "answerCode": "import sys\nprint(\"Python\", sys.version.split()[0])\n", "direction": "代码运行与调试"},
    {"title": "输出脚本文件路径", "level": "基础", "description": "用 __file__ 输出当前脚本路径。", "starter": "# 输出当前脚本路径\n", "expectedOutput": "script path:", "answerCode": "import os\nprint(\"script path:\", os.path.abspath(__file__))\n", "direction": "代码运行与调试"},
])

_pool("c03", [
    {"title": "变量交换练习", "level": "基础", "description": "交换 a 和 b 的值并输出。", "starter": "a = 10\nb = 20\n# 交换 a 和 b\n", "expectedOutput": "a=20, b=10", "answerCode": "a = 10\nb = 20\na, b = b, a\nprint(f\"a={a}, b={b}\")\n", "direction": "变量与命名"},
    {"title": "变量命名规范检查", "level": "进阶", "description": "给定一组变量名，判断哪些是合法的 Python 变量名。", "starter": "names = ['my_var', '2nd', '_private', 'my-var', 'class']\n# 输出合法的变量名\n", "expectedOutput": "['my_var', '_private']", "answerCode": "names = ['my_var', '2nd', '_private', 'my-var', 'class']\nimport keyword\nvalid = [n for n in names if n.isidentifier() and not keyword.iskeyword(n)]\nprint(valid)\n", "direction": "变量与命名"},
])

_pool("c04", [
    {"title": "类型转换练习", "level": "基础", "description": "把字符串 '42' 转为整数，与 8 相加后输出。", "starter": "value = '42'\n# 转换并求和\n", "expectedOutput": "50", "answerCode": "value = '42'\nresult = int(value) + 8\nprint(result)\n", "direction": "基础数据类型"},
    {"title": "数据类型判断", "level": "进阶", "description": "判断一组数据的类型并输出类型名列表。", "starter": "data = [42, 'hello', 3.14, True, None]\n# 输出类型名\n", "expectedOutput": "['int', 'str', 'float', 'bool', 'NoneType']", "answerCode": "data = [42, 'hello', 3.14, True, None]\nprint([type(x).__name__ for x in data])\n", "direction": "基础数据类型"},
])

_pool("c05", [
    {"title": "格式化输出名片", "level": "进阶", "description": "用 f-string 输出姓名和年龄。", "starter": "name = '小明'\nage = 20\n# 输出：小明，20岁\n", "expectedOutput": "小明，20岁", "answerCode": "name = '小明'\nage = 20\nprint(f\"{name}，{age}岁\")\n", "direction": "输入输出"},
    {"title": "多行格式化输出", "level": "挑战", "description": "输出一份包含标题、分隔线和内容的简易报告。", "starter": "title = '学习报告'\ncount = 5\n# 输出带分隔线的报告\n", "expectedOutput": "=== 学习报告 ===\n完成 5 题", "answerCode": "title = '学习报告'\ncount = 5\nprint(f\"=== {title} ===\")\nprint(f\"完成 {count} 题\")\n", "direction": "输入输出"},
])

_pool("c06", [
    {"title": "算术运算综合", "level": "基础", "description": "计算 17 除以 5 的商和余数。", "starter": "a, b = 17, 5\n# 输出商和余数\n", "expectedOutput": "商=3, 余数=2", "answerCode": "a, b = 17, 5\nprint(f\"商={a // b}, 余数={a % b}\")\n", "direction": "运算符"},
    {"title": "逻辑运算组合", "level": "进阶", "description": "判断 age 在 18-60 之间且 employed 为 True。", "starter": "age = 25\nemployed = True\n# 判断是否为在职工作年龄\n", "expectedOutput": "在职工作年龄", "answerCode": "age = 25\nemployed = True\nif 18 <= age <= 60 and employed:\n    print(\"在职工作年龄\")\nelse:\n    print(\"其他\")\n", "direction": "运算符"},
])

_pool("c07", [
    {"title": "成绩等级判断", "level": "基础", "description": "根据 score 输出等级。90+优秀，80+良好，60+及格，否则不及格。", "starter": "score = 86\n# 输出等级\n", "expectedOutput": "良好", "answerCode": "score = 86\nif score >= 90:\n    print(\"优秀\")\nelif score >= 80:\n    print(\"良好\")\nelif score >= 60:\n    print(\"及格\")\nelse:\n    print(\"不及格\")\n", "direction": "条件判断"},
    {"title": "多条件优惠判断", "level": "进阶", "description": "会员且消费满100打8折，否则原价。", "starter": "is_member = True\namount = 150\n# 计算应付金额\n", "expectedOutput": "应付：120.0", "answerCode": "is_member = True\namount = 150\nif is_member and amount >= 100:\n    pay = amount * 0.8\nelse:\n    pay = amount\nprint(f\"应付：{pay}\")\n", "direction": "条件判断"},
])

_pool("c08", [
    {"title": "循环求和 1 到 100", "level": "基础", "description": "用 for 循环计算 1+2+...+100。", "starter": "# 计算 1 到 100 的和\n", "expectedOutput": "5050", "answerCode": "total = 0\nfor i in range(1, 101):\n    total += i\nprint(total)\n", "direction": "循环"},
    {"title": "while 猜数字", "level": "挑战", "description": "模拟猜数字：target=7，guesses=[3,8,5,7]，输出猜了几次。", "starter": "target = 7\nguesses = [3, 8, 5, 7]\n# 统计猜了几次\n", "expectedOutput": "第4次猜对！", "answerCode": "target = 7\nguesses = [3, 8, 5, 7]\nfor i, g in enumerate(guesses, 1):\n    if g == target:\n        print(f\"第{i}次猜对！\")\n        break\n", "direction": "循环"},
])

_pool("c09", [
    {"title": "跳过负数求和", "level": "进阶", "description": "遍历列表，跳过负数，求正数之和。", "starter": "nums = [3, -1, 5, -2, 8]\n# 求正数之和\n", "expectedOutput": "16", "answerCode": "nums = [3, -1, 5, -2, 8]\ntotal = 0\nfor n in nums:\n    if n < 0:\n        continue\n    total += n\nprint(total)\n", "direction": "循环控制"},
    {"title": "查找第一个偶数", "level": "进阶", "description": "在列表中找到第一个偶数并停止。", "starter": "nums = [1, 3, 4, 6, 8]\n# 找到第一个偶数\n", "expectedOutput": "找到：4", "answerCode": "nums = [1, 3, 4, 6, 8]\nfor n in nums:\n    if n % 2 == 0:\n        print(f\"找到：{n}\")\n        break\n", "direction": "循环控制"},
])

_pool("c10", [
    {"title": "清洗用户名", "level": "基础", "description": "去掉空格并转小写。", "starter": "username = '  Alice_01  '\n# 清洗\n", "expectedOutput": "alice_01", "answerCode": "username = '  Alice_01  '\nprint(username.strip().lower())\n", "direction": "字符串"},
    {"title": "解析 CSV 行", "level": "进阶", "description": "把 CSV 行拆成字段列表。", "starter": "line = 'Python,85,进阶'\n# 解析为列表\n", "expectedOutput": "['Python', '85', '进阶']", "answerCode": "line = 'Python,85,进阶'\nfields = line.split(',')\nprint(fields)\n", "direction": "字符串"},
])

_pool("c11", [
    {"title": "列表切片练习", "level": "基础", "description": "取列表的前3个元素。", "starter": "nums = [10, 20, 30, 40, 50]\n# 取前3个\n", "expectedOutput": "[10, 20, 30]", "answerCode": "nums = [10, 20, 30, 40, 50]\nprint(nums[:3])\n", "direction": "列表与元组"},
    {"title": "元组解包", "level": "进阶", "description": "解包元组并输出各字段。", "starter": "record = ('小明', 20, 85)\n# 解包并输出\n", "expectedOutput": "姓名：小明，年龄：20，分数：85", "answerCode": "record = ('小明', 20, 85)\nname, age, score = record\nprint(f\"姓名：{name}，年龄：{age}，分数：{score}\")\n", "direction": "列表与元组"},
])

_pool("c12", [
    {"title": "字典计数统计", "level": "进阶", "description": "统计列表中每个元素出现次数。", "starter": "words = ['apple', 'banana', 'apple', 'cherry', 'banana', 'apple']\n# 统计次数\n", "expectedOutput": "{'apple': 3, 'banana': 2, 'cherry': 1}", "answerCode": "words = ['apple', 'banana', 'apple', 'cherry', 'banana', 'apple']\ncounts = {}\nfor w in words:\n    counts[w] = counts.get(w, 0) + 1\nprint(counts)\n", "direction": "字典与集合"},
    {"title": "集合去重", "level": "基础", "description": "用集合去除重复标签。", "starter": "tags = ['python', 'loop', 'python', 'list', 'loop']\n# 去重\n", "expectedOutput": "{'python', 'loop', 'list'}", "answerCode": "tags = ['python', 'loop', 'python', 'list', 'loop']\nunique = set(tags)\nprint(unique)\n", "direction": "字典与集合"},
])

_pool("c13", [
    {"title": "带默认值的问候函数", "level": "基础", "description": "定义 greet(name, greeting='你好') 并调用。", "starter": "# 定义并调用 greet\n", "expectedOutput": "你好，小明！", "answerCode": "def greet(name, greeting='你好'):\n    return f\"{greeting}，{name}！\"\n\nprint(greet('小明'))\n", "direction": "函数"},
    {"title": "可变参数求和", "level": "挑战", "description": "定义 my_sum(*args) 接受任意数量参数求和。", "starter": "# 定义 my_sum 并调用\n", "expectedOutput": "15", "answerCode": "def my_sum(*args):\n    return sum(args)\n\nprint(my_sum(1, 2, 3, 4, 5))\n", "direction": "函数"},
])

_pool("c14", [
    {"title": "多返回值函数", "level": "进阶", "description": "定义 min_max(nums) 返回最小值和最大值。", "starter": "# 定义 min_max 并调用\n", "expectedOutput": "最小值：1，最大值：9", "answerCode": "def min_max(nums):\n    return min(nums), max(nums)\n\nlo, hi = min_max([3, 1, 9, 5])\nprint(f\"最小值：{lo}，最大值：{hi}\")\n", "direction": "函数返回值"},
    {"title": "函数组合调用", "level": "挑战", "description": "定义 double(x) 和 add_one(x)，组合调用。", "starter": "# 定义 double 和 add_one，组合调用\n", "expectedOutput": "7", "answerCode": "def double(x):\n    return x * 2\n\ndef add_one(x):\n    return x + 1\n\nprint(add_one(double(3)))\n", "direction": "函数返回值"},
])

_pool("c15", [
    {"title": "使用 math 模块", "level": "基础", "description": "用 math.sqrt 计算平方根。", "starter": "import math\n# 计算 144 的平方根\n", "expectedOutput": "12.0", "answerCode": "import math\nprint(math.sqrt(144))\n", "direction": "模块"},
    {"title": "随机抽取幸运儿", "level": "进阶", "description": "用 random.choice 从列表中随机选一个。", "starter": "import random\nnames = ['小明', '小红', '小林']\n# 随机选一个\n", "expectedOutput": "幸运儿：", "answerCode": "import random\nnames = ['小明', '小红', '小林']\nlucky = random.choice(names)\nprint(f\"幸运儿：{lucky}\")\n", "direction": "模块"},
])

_pool("c16", [
    {"title": "写入并读取文件", "level": "基础", "description": "把文本写入文件再读出来。", "starter": "# 写入并读取 test.txt\n", "expectedOutput": "Hello PyStart", "answerCode": "with open('test.txt', 'w') as f:\n    f.write('Hello PyStart')\nwith open('test.txt') as f:\n    print(f.read())\n", "direction": "文件读写"},
    {"title": "逐行统计文件行数", "level": "进阶", "description": "统计多行文本的非空行数。", "starter": "lines = ['第一行', '', '第三行', '  ', '第五行']\n# 统计非空行\n", "expectedOutput": "非空行数：3", "answerCode": "lines = ['第一行', '', '第三行', '  ', '第五行']\ncount = sum(1 for line in lines if line.strip())\nprint(f\"非空行数：{count}\")\n", "direction": "文件读写"},
])

_pool("c17", [
    {"title": "安全类型转换", "level": "基础", "description": "安全地把字符串转为整数。", "starter": "values = ['42', 'abc', '7']\n# 安全转换\n", "expectedOutput": "[42, 0, 7]", "answerCode": "values = ['42', 'abc', '7']\nresult = []\nfor v in values:\n    try:\n        result.append(int(v))\n    except ValueError:\n        result.append(0)\nprint(result)\n", "direction": "异常处理"},
    {"title": "自定义异常", "level": "挑战", "description": "定义 ScoreError，当分数不在 0-100 时抛出。", "starter": "# 定义 ScoreError 并测试\n", "expectedOutput": "分数必须在 0-100 之间", "answerCode": "class ScoreError(Exception):\n    pass\n\ndef check_score(s):\n    if not 0 <= s <= 100:\n        raise ScoreError(\"分数必须在 0-100 之间\")\n    return \"有效\"\n\ntry:\n    check_score(150)\nexcept ScoreError as e:\n    print(e)\n", "direction": "异常处理"},
])

_pool("c18", [
    {"title": "定义学生类", "level": "基础", "description": "定义 Student 类，有 name 和 score 属性。", "starter": "# 定义 Student 类\n", "expectedOutput": "小明: 85", "answerCode": "class Student:\n    def __init__(self, name, score):\n        self.name = name\n        self.score = score\n    def __str__(self):\n        return f\"{self.name}: {self.score}\"\n\ns = Student('小明', 85)\nprint(s)\n", "direction": "面向对象"},
    {"title": "类方法练习", "level": "进阶", "description": "给 Student 添加 is_passed 方法。", "starter": "# 添加 is_passed 方法\n", "expectedOutput": "True", "answerCode": "class Student:\n    def __init__(self, name, score):\n        self.name = name\n        self.score = score\n    def is_passed(self):\n        return self.score >= 60\n\ns = Student('小明', 85)\nprint(s.is_passed())\n", "direction": "面向对象"},
])

_pool("c19", [
    {"title": "对象列表操作", "level": "进阶", "description": "创建多个 Student 对象，找出最高分。", "starter": "# 找出最高分学生\n", "expectedOutput": "最高分：小林 92", "answerCode": "class Student:\n    def __init__(self, name, score):\n        self.name = name\n        self.score = score\n\nstudents = [Student('小明', 85), Student('小红', 78), Student('小林', 92)]\ntop = max(students, key=lambda s: s.score)\nprint(f\"最高分：{top.name} {top.score}\")\n", "direction": "类与对象"},
    {"title": "对象序列化", "level": "挑战", "description": "把对象转为字典并序列化为 JSON。", "starter": "# 对象转 JSON\n", "expectedOutput": "{\"name\": \"小明\", \"score\": 85}", "answerCode": "import json\n\nclass Student:\n    def __init__(self, name, score):\n        self.name = name\n        self.score = score\n    def to_dict(self):\n        return {'name': self.name, 'score': self.score}\n\ns = Student('小明', 85)\nprint(json.dumps(s.to_dict(), ensure_ascii=False))\n", "direction": "类与对象"},
])

_pool("c20", [
    {"title": "学习进度统计", "level": "基础", "description": "统计完成率并输出百分比。", "starter": "total = 240\ndone = 156\n# 输出完成率\n", "expectedOutput": "完成率：65.0%", "answerCode": "total = 240\ndone = 156\nrate = done / total * 100\nprint(f\"完成率：{rate}%\")\n", "direction": "复习与总结"},
    {"title": "综合复习报告", "level": "挑战", "description": "根据各章得分生成复习建议。", "starter": "scores = {'循环': 55, '函数': 80, '类': 65}\n# 输出需要复习的章节\n", "expectedOutput": "需要复习：循环", "answerCode": "scores = {'循环': 55, '函数': 80, '类': 65}\nweak = [k for k, v in scores.items() if v < 70]\nprint(f\"需要复习：{'、'.join(weak)}\")\n", "direction": "复习与总结"},
])

_pool("c21", [
    {"title": "main 入口模式", "level": "进阶", "description": "用 if __name__ == '__main__' 模式组织脚本。", "starter": "# 用 main 函数组织\n", "expectedOutput": "程序开始\n程序结束", "answerCode": "def main():\n    print(\"程序开始\")\n    print(\"程序结束\")\n\nif __name__ == '__main__':\n    main()\n", "direction": "脚本组织"},
    {"title": "函数组合完成任务", "level": "挑战", "description": "把数据清洗拆成多个小函数组合调用。", "starter": "# 拆分清洗流程\n", "expectedOutput": "['alice', 'bob']", "answerCode": "def strip_spaces(s):\n    return s.strip()\n\ndef to_lower(s):\n    return s.lower()\n\ndef clean_names(names):\n    return [to_lower(strip_spaces(n)) for n in names if n.strip()]\n\nraw = ['  Alice ', '', ' BOB  ']\nprint(clean_names(raw))\n", "direction": "脚本组织"},
])

_pool("c22", [
    {"title": "输入校验", "level": "基础", "description": "校验年龄输入是否为有效正整数。", "starter": "raw = '25'\n# 校验并转换\n", "expectedOutput": "有效年龄：25", "answerCode": "raw = '25'\ntry:\n    age = int(raw)\n    if age > 0:\n        print(f\"有效年龄：{age}\")\n    else:\n        print(\"年龄必须为正数\")\nexcept ValueError:\n    print(\"无效输入\")\n", "direction": "数据清洗"},
    {"title": "批量数据标准化", "level": "进阶", "description": "把不统一的邮箱格式标准化。", "starter": "emails = [' Alice@Gmail.COM ', 'bob@qq.com', ' CHARLES@163.com ']\n# 标准化\n", "expectedOutput": "['alice@gmail.com', 'bob@qq.com', 'charles@163.com']", "answerCode": "emails = [' Alice@Gmail.COM ', 'bob@qq.com', ' CHARLES@163.com ']\ncleaned = [e.strip().lower() for e in emails if e.strip()]\nprint(cleaned)\n", "direction": "数据清洗"},
])

_pool("c23", [
    {"title": "列表推导式筛选", "level": "进阶", "description": "用列表推导式筛选偶数。", "starter": "nums = [1, 2, 3, 4, 5, 6, 7, 8]\n# 筛选偶数\n", "expectedOutput": "[2, 4, 6, 8]", "answerCode": "nums = [1, 2, 3, 4, 5, 6, 7, 8]\nevens = [n for n in nums if n % 2 == 0]\nprint(evens)\n", "direction": "列表进阶"},
    {"title": "多条件排序", "level": "挑战", "description": "先按分数降序，分数相同按姓名排序。", "starter": "students = [('小明', 85), ('小红', 92), ('小林', 85)]\n# 排序\n", "expectedOutput": "[('小红', 92), ('小林', 85), ('小明', 85)]", "answerCode": "students = [('小明', 85), ('小红', 92), ('小林', 85)]\nstudents.sort(key=lambda x: (-x[1], x[0]))\nprint(students)\n", "direction": "列表进阶"},
])

_pool("c24", [
    {"title": "嵌套字典统计", "level": "进阶", "description": "统计各部门的平均分。", "starter": "dept_scores = {'技术': [85, 90, 78], '产品': [88, 92]}\n# 输出各部门平均分\n", "expectedOutput": "技术：84.3\n产品：90.0", "answerCode": "dept_scores = {'技术': [85, 90, 78], '产品': [88, 92]}\nfor dept, scores in dept_scores.items():\n    avg = sum(scores) / len(scores)\n    print(f\"{dept}：{avg:.1f}\")\n", "direction": "结构化数据"},
    {"title": "字典合并", "level": "挑战", "description": "合并两个字典，相同键的值求和。", "starter": "d1 = {'a': 1, 'b': 2}\nd2 = {'b': 3, 'c': 4}\n# 合并\n", "expectedOutput": "{'a': 1, 'b': 5, 'c': 4}", "answerCode": "d1 = {'a': 1, 'b': 2}\nd2 = {'b': 3, 'c': 4}\nmerged = {}\nfor k, v in d1.items():\n    merged[k] = merged.get(k, 0) + v\nfor k, v in d2.items():\n    merged[k] = merged.get(k, 0) + v\nprint(merged)\n", "direction": "结构化数据"},
])

_pool("c25", [
    {"title": "纯函数拆分", "level": "进阶", "description": "把数据处理拆成纯函数链。", "starter": "# 拆分成纯函数\n", "expectedOutput": "['ALICE', 'BOB']", "answerCode": "def normalize(name):\n    return name.strip()\n\ndef to_upper(name):\n    return name.upper()\n\ndef process(names):\n    return [to_upper(normalize(n)) for n in names if n.strip()]\n\nraw = ['  alice ', '', ' bob  ']\nprint(process(raw))\n", "direction": "函数拆分"},
    {"title": "函数式 pipeline", "level": "挑战", "description": "用 reduce 实现数据处理管道。", "starter": "# 构建处理管道\n", "expectedOutput": "24", "answerCode": "from functools import reduce\n\ndef pipeline(data, *funcs):\n    return reduce(lambda d, f: f(d), funcs, data)\n\ndouble = lambda x: x * 2\nadd_one = lambda x: x + 1\n\nprint(pipeline(3, double, add_one, double))\n", "direction": "函数拆分"},
])

_pool("c26", [
    {"title": "统计文本词频", "level": "进阶", "description": "统计文本中每个单词的出现次数。", "starter": "text = 'the cat sat on the mat the cat'\n# 统计词频\n", "expectedOutput": "{'the': 3, 'cat': 2, 'sat': 1, 'on': 1, 'mat': 1}", "answerCode": "text = 'the cat sat on the mat the cat'\nwords = text.split()\ncounts = {}\nfor w in words:\n    counts[w] = counts.get(w, 0) + 1\nprint(counts)\n", "direction": "文本脚本"},
    {"title": "生成文本摘要", "level": "挑战", "description": "从多行文本中提取关键信息。", "starter": "lines = ['今日完成 5 题', '用时 45 分钟', '正确率 80%']\n# 生成摘要\n", "expectedOutput": "摘要：完成5题，用时45分钟，正确率80%", "answerCode": "lines = ['今日完成 5 题', '用时 45 分钟', '正确率 80%']\nimport re\nnumbers = []\nfor line in lines:\n    nums = re.findall(r'\\d+', line)\n    numbers.extend(nums)\nprint(f\"摘要：完成{numbers[0]}题，用时{numbers[1]}分钟，正确率{numbers[2]}%\")\n", "direction": "文本脚本"},
])

_pool("c27", [
    {"title": "安全解析练习分数", "level": "进阶", "description": "把字符串分数转换为整数，遇到无法转换的数据时记为 0。", "starter": "raw_scores = ['90', 'bad', '75']\n# 安全转换并计算平均分\n", "expectedOutput": "55", "answerCode": "raw_scores = ['90', 'bad', '75']\nscores = []\nfor item in raw_scores:\n    try:\n        scores.append(int(item))\n    except ValueError:\n        scores.append(0)\nprint(sum(scores) // len(scores))\n", "direction": "健壮程序"},
    {"title": "边界值处理", "level": "挑战", "description": "处理除零、空列表等边界情况。", "starter": "data = []\n# 安全计算平均值\n", "expectedOutput": "数据为空", "answerCode": "data = []\nif not data:\n    print(\"数据为空\")\nelse:\n    try:\n        avg = sum(data) / len(data)\n        print(f\"平均值：{avg}\")\n    except ZeroDivisionError:\n        print(\"数据为空\")\n", "direction": "健壮程序"},
])

_pool("c28", [
    {"title": "格式化当前时间", "level": "基础", "description": "输出当前日期时间。", "starter": "from datetime import datetime\n# 输出当前时间\n", "expectedOutput": "当前时间：", "answerCode": "from datetime import datetime\nnow = datetime.now()\nprint(f\"当前时间：{now.strftime('%Y-%m-%d %H:%M')}\")\n", "direction": "日期时间"},
    {"title": "计算学习天数", "level": "进阶", "description": "计算从开始学习到今天的天数。", "starter": "from datetime import datetime, timedelta\nstart = datetime(2026, 1, 1)\n# 计算天数差\n", "expectedOutput": "已学习：", "answerCode": "from datetime import datetime\nstart = datetime(2026, 1, 1)\nnow = datetime.now()\ndays = (now - start).days\nprint(f\"已学习：{days} 天\")\n", "direction": "日期时间"},
])

_pool("c29", [
    {"title": "汇总题库练习进度", "level": "挑战", "description": "根据每日练习记录统计完成题数和总用时。", "starter": "daily = [{'date': '2026-05-11', 'count': 3, 'minutes': 42}, {'date': '2026-05-12', 'count': 4, 'minutes': 55}]\n# 输出汇总摘要\n", "expectedOutput": "完成7题，用时97分钟", "answerCode": "daily = [{'date': '2026-05-11', 'count': 3, 'minutes': 42}, {'date': '2026-05-12', 'count': 4, 'minutes': 55}]\ntotal_count = sum(item['count'] for item in daily)\ntotal_minutes = sum(item['minutes'] for item in daily)\nprint(f'完成{total_count}题，用时{total_minutes}分钟')\n", "direction": "学习记录项目"},
    {"title": "生成学习报表", "level": "挑战", "description": "按日期生成学习报表。", "starter": "records = [{'day': '周一', 'done': 5, 'score': 80}, {'day': '周二', 'done': 3, 'score': 90}]\n# 输出报表\n", "expectedOutput": "周一：5题，80分\n周二：3题，90分", "answerCode": "records = [{'day': '周一', 'done': 5, 'score': 80}, {'day': '周二', 'done': 3, 'score': 90}]\nfor r in records:\n    print(f\"{r['day']}：{r['done']}题，{r['score']}分\")\n", "direction": "学习记录项目"},
])

_pool("c30", [
    {"title": "需求拆分练习", "level": "进阶", "description": "把一个大需求拆成可执行的小任务。", "starter": "requirement = '开发一个学生成绩管理系统'\n# 拆分任务\n", "expectedOutput": "1. 定义数据结构\n2. 实现增删改查\n3. 添加统计功能\n4. 编写测试", "answerCode": "requirement = '开发一个学生成绩管理系统'\ntasks = [\n    '1. 定义数据结构',\n    '2. 实现增删改查',\n    '3. 添加统计功能',\n    '4. 编写测试'\n]\nfor t in tasks:\n    print(t)\n", "direction": "综合脚本流程"},
    {"title": "项目流程回顾", "level": "挑战", "description": "回顾整个学习流程并输出关键收获。", "starter": "# 输出学习回顾\n", "expectedOutput": "Python 学习完成！\n关键收获：变量、循环、函数、类", "answerCode": "milestones = ['变量', '循环', '函数', '类']\nprint('Python 学习完成！')\nprint(f\"关键收获：{'、'.join(milestones)}\")\n", "direction": "综合脚本流程"},
])

# ---------------------------------------------------------------------------
# Web fetching
# ---------------------------------------------------------------------------

def get_date_filter(days_back: int = 30) -> str:
    """Dynamic date filter for GitHub Search API."""
    return (dt.date.today() - dt.timedelta(days=days_back)).isoformat()


def fetch_url(url: str, headers: dict | None = None, timeout: int = 20) -> str:
    """Fetch a URL and return the response body as string."""
    hdrs = {"User-Agent": UA}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def gh_search(query: str, per_page: int = 8) -> list[dict]:
    """Search GitHub repositories."""
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": query, "sort": "updated", "order": "desc", "per_page": per_page}
    )
    try:
        body = fetch_url(url, {"Accept": "application/vnd.github+json"})
        return json.loads(body).get("items", [])
    except Exception as e:
        print(f"  [WARN] GitHub search failed: {e}")
        return []


def fetch_rss(url: str) -> list[dict]:
    """Parse an RSS/Atom feed and return items."""
    try:
        body = fetch_url(url)
        root = ET.fromstring(body)
        items = []
        # RSS 2.0
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            if title:
                items.append({"title": title, "url": link, "description": desc, "source": "rss"})
        # Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            title = (entry.findtext("atom:title", "", ns) or entry.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
            link_el = entry.find("atom:link", ns) or entry.find("{http://www.w3.org/2005/Atom}link")
            link = link_el.get("href", "") if link_el is not None else ""
            desc = (entry.findtext("atom:summary", "", ns) or entry.findtext("{http://www.w3.org/2005/Atom}summary") or "").strip()
            if title:
                items.append({"title": title, "url": link, "description": desc, "source": "rss"})
        return items[:15]
    except Exception as e:
        print(f"  [WARN] RSS fetch failed ({url}): {e}")
        return []


class SimpleTextExtractor(HTMLParser):
    """Extract visible text from HTML."""
    def __init__(self):
        super().__init__()
        self._text = []
        self._skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = True
    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = False
    def handle_data(self, data):
        if not self._skip:
            self._text.append(data)
    def get_text(self):
        return " ".join(self._text)


def scrape_page(url: str, title_selector: str = "") -> list[dict]:
    """Scrape a web page for exercise-like content."""
    try:
        body = fetch_url(url)
        parser = SimpleTextExtractor()
        parser.feed(body)
        text = parser.get_text()
        # Extract sections that look like exercises
        items = []
        # Look for numbered items or headings
        for match in re.finditer(r'(\d+[\.\)]\s*[^\n]{10,120})', text):
            title = match.group(1).strip()[:80]
            items.append({"title": title, "url": url, "description": title, "source": "web"})
        return items[:10]
    except Exception as e:
        print(f"  [WARN] Web scrape failed ({url}): {e}")
        return []


# ---------------------------------------------------------------------------
# Signal collection
# ---------------------------------------------------------------------------

RSS_FEEDS = [
    "https://realpython.com/atom.xml",
    "https://planetpython.org/rss20.xml",
    "https://pycoders.com/feed",
    "https://pythonweekly.com/rss",
    "https://www.python.org/feeds/blog.atom",
]

WEB_SOURCES = [
    "https://www.practicepython.org/",
    "https://www.w3schools.com/python/python_exercises.asp",
    "https://www.learnpython.org/",
]


def collect_github_signals() -> list[dict]:
    """Collect signals from GitHub Search API."""
    date_filter = get_date_filter(30)
    queries = [
        f"python practice problems created:>{date_filter}",
        f"python exercises questions created:>{date_filter} language:Python",
        f"python quiz questions created:>{date_filter}",
        f"python tutorial beginner created:>{date_filter}",
        f"leetcode python solutions created:>{date_filter}",
        f"python coding challenges created:>{date_filter}",
        f"python learning exercises created:>{date_filter}",
        f"python homework assignments created:>{date_filter}",
        f"python algorithm practice created:>{date_filter}",
        f"python interview questions created:>{date_filter}",
    ]
    signals = []
    for query in queries:
        print(f"  GitHub: {query[:60]}...")
        for item in gh_search(query):
            text = " ".join([item.get("full_name", ""), item.get("description") or ""])
            cid, direction, tags = classify(text)
            signals.append({
                "full_name": item.get("full_name", ""),
                "url": item.get("html_url", ""),
                "updated_at": item.get("updated_at", ""),
                "description": item.get("description"),
                "chapterId": cid,
                "direction": direction,
                "tags": tags,
                "source": "github",
            })
    return signals


def collect_rss_signals() -> list[dict]:
    """Collect signals from RSS feeds."""
    signals = []
    for feed_url in RSS_FEEDS:
        print(f"  RSS: {feed_url}")
        for item in fetch_rss(feed_url):
            text = " ".join([item.get("title", ""), item.get("description", "")])
            cid, direction, tags = classify(text)
            signals.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
                "chapterId": cid,
                "direction": direction,
                "tags": tags,
                "source": "rss",
            })
    return signals


def collect_web_signals() -> list[dict]:
    """Collect signals from popular Python exercise sites."""
    signals = []
    for url in WEB_SOURCES:
        print(f"  Web: {url}")
        for item in scrape_page(url):
            text = " ".join([item.get("title", ""), item.get("description", "")])
            cid, direction, tags = classify(text)
            signals.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
                "chapterId": cid,
                "direction": direction,
                "tags": tags,
                "source": "web",
            })
    return signals


# ---------------------------------------------------------------------------
# Classification & exercise generation
# ---------------------------------------------------------------------------

def classify(text: str) -> tuple[str, str, list[str]]:
    """Classify a signal into a chapter based on keyword matching."""
    lower = text.lower()
    for needle, cid in TOPIC_RULES:
        if needle in lower:
            topic_info = TOPICS.get(cid)
            if topic_info:
                return cid, topic_info[1], topic_info[2]
    # Default to c23 (list processing) if no match
    return "c23", TOPICS["c23"][1], TOPICS["c23"][2]


def get_template(cid: str, date_seed: str) -> dict:
    """Get a template variant for a chapter, rotating daily."""
    variants = POOL.get(cid, [])
    if not variants:
        # Fallback generic template
        topic_info = TOPICS.get(cid, ("Python 练习", "综合", ["Python", "练习"]))
        return {
            "title": f"综合练习：{topic_info[0]}",
            "level": "进阶",
            "description": f"综合运用{topic_info[0]}的知识完成练习。",
            "starter": "# 请在这里完成练习\n",
            "expectedOutput": "运行程序查看输出",
            "answerCode": "# 参考答案待补充\nprint('Hello PyStart')\n",
            "direction": topic_info[1],
        }
    # Use date-based hash to select variant
    h = hashlib.md5(f"{cid}-{date_seed}".encode()).hexdigest()
    idx = int(h, 16) % len(variants)
    return dict(variants[idx])


def make_exercise(cid: str, tags: list[str], idx: int, signals: list[dict]) -> dict:
    """Generate an original exercise inspired by trend signals."""
    date_seed = dt.date.today().isoformat()
    base = get_template(cid, date_seed)
    qid = f"daily-{date_seed}-{idx:02d}"
    signal_names = []
    for s in signals[:3]:
        name = s.get("full_name") or s.get("title") or s.get("url", "")
        if name:
            signal_names.append(name)

    # Ensure non-empty fallbacks for required fields
    starter = (base.get("starter") or "").strip() or "# 请在这里完成练习\n"
    answer_code = (base.get("answerCode") or "").strip() or "# 参考答案待补充\nprint('Hello PyStart')\n"
    expected_output = (base.get("expectedOutput") or "").strip() or "运行程序查看输出"
    description = (base.get("description") or "").strip() or f"综合运用{TOPICS.get(cid, ('Python',))[0]}知识完成练习。"

    return {
        "id": qid,
        "chapterId": cid,
        "level": base.get("level", "进阶"),
        "title": base.get("title", f"练习 {cid}"),
        "text": f"{base.get('title', '')}：{description}",
        "description": description,
        "hint": "先把固定样例数据跑通，再考虑如何替换成真实输入。",
        "starter": starter,
        "expectedOutput": expected_output,
        "answer": answer_code,
        "answerCode": answer_code,
        "taskGoal": description,
        "analysis": "本题由近期公开 Python 练习仓库的主题趋势启发，但题干、数据和参考答案均为 PyStart 原创内容，适合补充到对应章节。",
        "tags": tags,
        "examples": [{"input": "题目内置固定数据", "output": expected_output}],
        "tests": [{"name": "参考答案输出校验", "expected": expected_output}],
        "direction": base.get("direction", TOPICS.get(cid, ("", "综合", []))[1]),
        "source": "pystart-web-trend-original-v2",
        "qualityNotes": f"基于公开仓库元数据趋势生成；信号来源：{', '.join(signal_names[:3])}",
        "webSignals": signal_names,
    }


def dedup_signals(signals: list[dict]) -> list[dict]:
    """Remove duplicate signals based on text similarity."""
    seen = set()
    unique = []
    for s in signals:
        key = (s.get("full_name") or s.get("title") or s.get("url", "")).lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


# ---------------------------------------------------------------------------
# Import into question bank
# ---------------------------------------------------------------------------

def load_question_bank() -> dict:
    """Load the curated-v2 question bank."""
    if not QB_FILE.exists():
        raise FileNotFoundError(f"Question bank not found: {QB_FILE}")
    return json.loads(QB_FILE.read_text(encoding="utf-8"))


def backup_question_bank():
    """Create a timestamped backup of the question bank."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"question_bank_{ts}.json"
    import shutil
    shutil.copy2(QB_FILE, backup_path)
    # Keep only MAX_BACKUPS backups
    backups = sorted(BACKUP_DIR.glob("question_bank_*.json"))
    for old in backups[:-MAX_BACKUPS]:
        old.unlink()
    return backup_path


def import_exercises(exercises: list[dict]) -> list[dict]:
    """Import generated exercises into the question bank.

    Strategy: replace the last exercise of the same level in each matching
    chapter. Keeps the bank size stable at 30 × 8 = 240.
    """
    qb = load_question_bank()
    chapters = {c["chapterId"]: c for c in qb.get("chapters", [])}
    existing_titles = {
        e.get("title")
        for c in chapters.values()
        for e in c.get("exercises", [])
    }

    imported = []
    for draft in exercises:
        cid = draft.get("chapterId")
        chapter = chapters.get(cid)
        if not chapter:
            continue
        if draft.get("title") in existing_titles:
            print(f"  SKIP (duplicate title): {draft['title']}")
            continue

        exercises_list = chapter.get("exercises", [])
        if not exercises_list:
            continue

        # Find last exercise of same level to replace
        draft_level = draft.get("level", "进阶")
        replace_index = None
        for i in range(len(exercises_list) - 1, -1, -1):
            if exercises_list[i].get("level") == draft_level:
                replace_index = i
                break
        if replace_index is None:
            replace_index = len(exercises_list) - 1

        # Build the new exercise
        new_ex = {k: v for k, v in draft.items() if k not in {"chapterId", "webSignals"}}
        old_id = exercises_list[replace_index].get("id", f"{cid}-latest")
        new_ex["id"] = old_id
        new_ex["source"] = "pystart-curated-v2"
        signals_str = "、".join(draft.get("webSignals") or [])
        new_ex["qualityNotes"] = (new_ex.get("qualityNotes", "") + f" 趋势信号：{signals_str}").strip()

        exercises_list[replace_index] = new_ex
        existing_titles.add(new_ex["title"])
        imported.append({"chapterId": cid, "title": new_ex["title"], "replacedId": old_id})
        print(f"  IMPORTED: {new_ex['title']} → {cid} (replaced {old_id})")

    return imported


def save_question_bank(qb: dict):
    """Save the updated question bank."""
    QB_FILE.write_text(json.dumps(qb, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print(f"PyStart Academy 每日题库更新 — {dt.date.today().isoformat()}")
    print("=" * 60)

    if DRY_RUN:
        print("[DRY RUN] 只采集信号和生成草稿，不导入题库")

    # Step 1: Collect signals from all sources
    print("\n[1/4] 采集网络信号...")
    all_signals = []

    print("\n--- GitHub Search API ---")
    gh_signals = collect_github_signals()
    print(f"  获取 {len(gh_signals)} 条 GitHub 信号")
    all_signals.extend(gh_signals)

    print("\n--- RSS Feeds ---")
    rss_signals = collect_rss_signals()
    print(f"  获取 {len(rss_signals)} 条 RSS 信号")
    all_signals.extend(rss_signals)

    print("\n--- Web Sources ---")
    web_signals = collect_web_signals()
    print(f"  获取 {len(web_signals)} 条 Web 信号")
    all_signals.extend(web_signals)

    # Step 2: Deduplicate
    print(f"\n[2/4] 去重处理（原始 {len(all_signals)} 条）...")
    all_signals = dedup_signals(all_signals)
    print(f"  去重后 {len(all_signals)} 条信号")

    # Step 3: Generate exercises
    print("\n[3/4] 生成原创练习...")
    grouped: dict[str, list[dict]] = {}
    for s in all_signals:
        cid = s.get("chapterId")
        if cid:
            grouped.setdefault(cid, []).append(s)

    exercises = []
    # Generate exercises for up to 8 chapters per run
    for idx, (cid, signals) in enumerate(sorted(grouped.items())[:8], 1):
        topic_info = TOPICS.get(cid, ("Python", "综合", ["Python", "练习"]))
        exercise = make_exercise(cid, topic_info[2], idx, signals)
        exercises.append(exercise)
        print(f"  生成: {exercise['title']} → {cid}")

    print(f"\n  共生成 {len(exercises)} 道原创练习")

    # Save intermediate drafts
    LATEST_FILE.parent.mkdir(exist_ok=True)
    payload = {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sourcePolicy": "Use public web metadata as trend signals only; do not copy third-party question text.",
        "signals": all_signals[:50],
        "exercises": exercises,
    }
    LATEST_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  草稿已保存: data/latest_python_questions.json")

    # Step 4: Import into question bank
    if not DRY_RUN:
        print("\n[4/4] 导入题库...")
        backup_path = backup_question_bank()
        print(f"  备份: {backup_path.name}")

        qb = load_question_bank()
        imported = import_exercises(exercises)
        save_question_bank(qb)

        print(f"\n  成功导入 {len(imported)} 道题")
        if imported:
            for imp in imported:
                print(f"    {imp['chapterId']}: {imp['title']}")
    else:
        print("\n[4/4] [DRY RUN] 跳过导入")

    print("\n" + "=" * 60)
    print(f"完成！生成 {len(exercises)} 道练习，信号 {len(all_signals)} 条")
    print("=" * 60)

    return len(exercises)


if __name__ == "__main__":
    main()
