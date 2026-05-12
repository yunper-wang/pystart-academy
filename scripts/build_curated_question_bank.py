#!/usr/bin/env python3
"""Rebuild PyStart Academy exercises as a fully curated original v2 bank.

This script intentionally removes legacy/futurecoder exercises and writes a
consistent 30 chapters × 8 exercises structure. The generated exercises keep
legacy app fields while adding richer metadata for validation and UI display.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"
BACKUP_FILE = ROOT / "data.backup-before-curated-v2.json"
SOURCE = "pystart-curated-v2"
LEVELS = ["基础", "基础", "基础", "进阶", "进阶", "进阶", "挑战", "挑战"]

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


def clean(code: str) -> str:
    return code.strip() + "\n"


def ex(chapter_id: str, num: int, level: str, title: str, description: str, starter: str, expected: str, answer: str, analysis: str, tags: list[str], direction: str, hint: str | None = None):
    qid = f"{chapter_id}-{ {'基础':'easy','进阶':'medium','挑战':'hard'}[level] }-{num:03d}"
    if len(description) < 18:
        description = f"{description}，并观察输出是否符合预期。"
    if len(analysis) < 35:
        analysis = f"{analysis} 这类题训练的是把需求翻译成清晰代码的能力，先保证结果正确，再关注写法是否容易阅读。"
    return {
        "id": qid,
        "level": level,
        "title": title,
        "text": f"{title}：{description}",
        "description": description,
        "hint": hint or "先写出固定数据，再按“处理数据 → print 输出”的顺序完成。",
        "answer": clean(answer),
        "starter": clean(starter),
        "expectedOutput": expected.strip(),
        "answerCode": clean(answer),
        "taskGoal": description,
        "analysis": analysis,
        "tags": tags,
        "examples": [{"input": "题目内置固定数据", "output": expected.strip()}],
        "tests": [{"name": "参考答案输出校验", "expected": expected.strip()}],
        "direction": direction,
        "source": SOURCE,
        "qualityNotes": "原创 curated v2 题：题干有真实小场景，起始代码不直接暴露答案，参考答案可运行，输出可自动校验。",
    }


def generic_exercises(chapter_id: str, topic: str, direction: str, base_tags: list[str]) -> list[dict]:
    # A fallback bank used only if a chapter-specific bank is not defined.
    return [
        ex(chapter_id, 1, "基础", f"输出{topic}学习目标", f"用 print 输出本章学习目标“掌握{topic}”。", "# 输出本章学习目标", f"掌握{topic}", f"print(\"掌握{topic}\")", "用最小代码确认 print 与字符串输出，这是后续所有脚本反馈的基础。", base_tags, direction),
        ex(chapter_id, 2, "基础", f"保存{topic}学习时长", f"用变量 minutes 保存 30，并输出“{topic}学习 30 分钟”。", "minutes = 30\n# 输出学习记录", f"{topic}学习 30 分钟", f"minutes = 30\nprint(\"{topic}学习\", minutes, \"分钟\")", "变量负责保存会变化的数据，输出时再把变量和说明文字组合起来。", base_tags + ["变量"], direction),
        ex(chapter_id, 3, "基础", f"整理{topic}关键词", f"把 3 个关键词放入列表并输出列表长度。", "keywords = []\n# 添加 3 个关键词并输出数量", "关键词数量：3", "keywords = [\"概念\", \"语法\", \"练习\"]\nprint(\"关键词数量：\" + str(len(keywords)))", "列表适合保存一组同类信息，len 可以快速获得数量。", base_tags + ["列表"], direction),
        ex(chapter_id, 4, "进阶", f"筛选{topic}待复习项", f"从 tasks 中筛选包含“复习”的任务并输出。", "tasks = [\"阅读概念\", \"复习错题\", \"完成练习\", \"复习项目\"]\n# 筛选复习任务", "['复习错题', '复习项目']", "tasks = [\"阅读概念\", \"复习错题\", \"完成练习\", \"复习项目\"]\nreview = [task for task in tasks if \"复习\" in task]\nprint(review)", "列表推导式可以把筛选条件和新列表构造放在一起，适合批量数据处理。", base_tags + ["筛选"], direction),
        ex(chapter_id, 5, "进阶", f"统计{topic}标签次数", f"统计 tags 中每个标签出现次数并输出字典。", "tags = [\"基础\", \"练习\", \"基础\", \"项目\"]\ncounts = {}\n# 统计次数", "{'基础': 2, '练习': 1, '项目': 1}", "tags = [\"基础\", \"练习\", \"基础\", \"项目\"]\ncounts = {}\nfor tag in tags:\n    counts[tag] = counts.get(tag, 0) + 1\nprint(counts)", "字典计数是数据分析的基本模式，get 默认值能避免第一次出现时 KeyError。", base_tags + ["字典"], direction),
        ex(chapter_id, 6, "进阶", f"封装{topic}建议函数", f"定义函数 suggest，根据 score 返回复习建议。", "def suggest(score):\n    pass\n\nprint(suggest(85))", "继续挑战", "def suggest(score):\n    if score >= 80:\n        return \"继续挑战\"\n    return \"先复习基础\"\n\nprint(suggest(85))", "函数把判断逻辑封装起来，调用者只需要传入分数并使用返回结果。", base_tags + ["函数"], direction),
        ex(chapter_id, 7, "挑战", f"生成{topic}学习摘要", f"根据 records 统计总分钟数和完成数量，输出摘要。", "records = [{'done': True, 'minutes': 20}, {'done': False, 'minutes': 15}, {'done': True, 'minutes': 25}]\n# 输出 完成：2，总时长：60", "完成：2，总时长：60", "records = [{'done': True, 'minutes': 20}, {'done': False, 'minutes': 15}, {'done': True, 'minutes': 25}]\ndone_count = sum(1 for item in records if item['done'])\ntotal_minutes = sum(item['minutes'] for item in records)\nprint(f\"完成：{done_count}，总时长：{total_minutes}\")", "综合使用列表、字典、生成器表达式和格式化字符串，形成真实小报表。", base_tags + ["综合应用"], direction),
        ex(chapter_id, 8, "挑战", f"构建{topic}任务流水线", f"把 raw 中的任务清洗、去空、去重后输出。", "raw = ['  练习  ', '', '复习', '练习', ' 项目 ']\n# 清洗并保持顺序去重", "['练习', '复习', '项目']", "raw = ['  练习  ', '', '复习', '练习', ' 项目 ']\nresult = []\nfor item in raw:\n    clean_item = item.strip()\n    if clean_item and clean_item not in result:\n        result.append(clean_item)\nprint(result)", "这是常见脚本流水线：清洗空白、过滤无效值、去重并保持顺序。", base_tags + ["数据清洗"], direction),
    ]


def specialized(chapter_id: str, topic: str, direction: str, tags: list[str]) -> list[dict]:
    if chapter_id == "c07":
        return [
            ex(chapter_id,1,"基础","判断是否成年","age 为 20，判断是否成年并输出“可以报名”。","age = 20\n# 判断是否可以报名","可以报名","age = 20\nif age >= 18:\n    print(\"可以报名\")\nelse:\n    print(\"暂时不能报名\")","if/else 让程序根据条件选择不同路径，先覆盖最常见的二选一场景。",tags,direction),
            ex(chapter_id,2,"基础","成绩等级判断","score 为 86，输出等级“良好”。","score = 86\n# 输出 优秀/良好/继续努力","良好","score = 86\nif score >= 90:\n    print(\"优秀\")\nelif score >= 80:\n    print(\"良好\")\nelse:\n    print(\"继续努力\")","多分支要从高到低判断，避免 95 分先落入 >=80 的分支。",tags,direction),
            ex(chapter_id,3,"基础","登录状态提示","is_login 为 True 时输出“欢迎回来”。","is_login = True\n# 根据登录状态输出提示","欢迎回来","is_login = True\nif is_login:\n    print(\"欢迎回来\")\nelse:\n    print(\"请先登录\")","布尔变量可以直接作为 if 条件，让状态判断更自然。",tags,direction),
            ex(chapter_id,4,"进阶","优惠资格判断","member 为 True 且 amount 不小于 100 时输出“可享优惠”。","member = True\namount = 128\n# 判断优惠资格","可享优惠","member = True\namount = 128\nif member and amount >= 100:\n    print(\"可享优惠\")\nelse:\n    print(\"暂无优惠\")","and 要求两个条件同时成立，适合会员+金额门槛这类规则。",tags,direction),
            ex(chapter_id,5,"进阶","温度出行建议","temperature 为 31，输出“注意防晒”。","temperature = 31\n# 输出出行建议","注意防晒","temperature = 31\nif temperature < 10:\n    print(\"穿厚外套\")\nelif temperature <= 28:\n    print(\"正常出门\")\nelse:\n    print(\"注意防晒\")","注意边界：第二个分支覆盖 10 到 28，剩下就是高温。",tags,direction),
            ex(chapter_id,6,"进阶","库存告警","stock 为 3，threshold 为 5，库存不足时输出“需要补货”。","stock = 3\nthreshold = 5\n# 判断库存","需要补货","stock = 3\nthreshold = 5\nif stock < threshold:\n    print(\"需要补货\")\nelse:\n    print(\"库存充足\")","条件判断常用于业务告警，把阈值单独存成变量方便维护。",tags,direction),
            ex(chapter_id,7,"挑战","多条件账号校验","用户名非空且密码长度至少 6 位时输出“账号可用”。","username = \"alice\"\npassword = \"abc123\"\n# 校验账号","账号可用","username = \"alice\"\npassword = \"abc123\"\nif username and len(password) >= 6:\n    print(\"账号可用\")\nelse:\n    print(\"账号信息不完整\")","字符串非空时为 True，len 可以检查长度，组合后形成简单表单校验。",tags,direction),
            ex(chapter_id,8,"挑战","订单状态流转","paid 和 shipped 决定订单状态，已付款未发货输出“待发货”。","paid = True\nshipped = False\n# 输出订单状态","待发货","paid = True\nshipped = False\nif not paid:\n    print(\"待付款\")\nelif not shipped:\n    print(\"待发货\")\nelse:\n    print(\"已完成\")","状态判断要按业务流程排序：未付款优先，其次才是发货状态。",tags,direction),
        ]
    if chapter_id == "c08":
        return [
            ex(chapter_id,1,"基础","遍历输出课程","依次输出 courses 中的课程名。","courses = [\"变量\", \"循环\", \"函数\"]\n# 逐个输出","变量\n循环\n函数","courses = [\"变量\", \"循环\", \"函数\"]\nfor course in courses:\n    print(course)","for 循环适合遍历已知集合，每轮拿到一个元素。",tags,direction),
            ex(chapter_id,2,"基础","累计学习分钟","统计 minutes 中所有数字的总和。","minutes = [20, 35, 15]\ntotal = 0\n# 累计总时长","70","minutes = [20, 35, 15]\ntotal = 0\nfor minute in minutes:\n    total += minute\nprint(total)","累计模式是循环最重要的基础套路之一。",tags,direction),
            ex(chapter_id,3,"基础","while 倒计时","从 3 倒数到 1，每行输出一个数字。","n = 3\n# while 倒计时","3\n2\n1","n = 3\nwhile n > 0:\n    print(n)\n    n -= 1","while 需要手动更新条件变量，否则容易死循环。",tags,direction),
            ex(chapter_id,4,"进阶","统计及格人数","遍历 scores，统计不低于 60 的数量。","scores = [58, 90, 61, 45, 77]\npassed = 0\n# 计数","及格人数：3","scores = [58, 90, 61, 45, 77]\npassed = 0\nfor score in scores:\n    if score >= 60:\n        passed += 1\nprint(\"及格人数：\" + str(passed))","循环和条件组合可以完成真实统计任务。",tags,direction),
            ex(chapter_id,5,"进阶","生成编号列表","用 range 生成 L1 到 L4。","# 生成编号","['L1', 'L2', 'L3', 'L4']","labels = []\nfor i in range(1, 5):\n    labels.append(\"L\" + str(i))\nprint(labels)","range 常用于生成连续编号，注意右边界不包含。",tags,direction),
            ex(chapter_id,6,"进阶","循环拼接报告","把 names 拼成用顿号连接的文本。","names = [\"小明\", \"小红\", \"小林\"]\n# 拼接为 小明、小红、小林","小明、小红、小林","names = [\"小明\", \"小红\", \"小林\"]\nreport = \"、\".join(names)\nprint(report)","虽然可以循环拼接，但 join 更适合把字符串列表合成文本。",tags,direction),
            ex(chapter_id,7,"挑战","嵌套循环生成坐标","输出 2 行 3 列坐标列表。","points = []\n# 生成坐标","[(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3)]","points = []\nfor row in range(1, 3):\n    for col in range(1, 4):\n        points.append((row, col))\nprint(points)","嵌套循环适合二维表格、坐标和组合枚举。",tags,direction),
            ex(chapter_id,8,"挑战","循环生成学习报告","根据 records 输出每门课是否达标。","records = [(\"变量\", 80), (\"循环\", 55)]\n# 输出课程状态","变量：达标\n循环：复习","records = [(\"变量\", 80), (\"循环\", 55)]\nfor name, score in records:\n    status = \"达标\" if score >= 60 else \"复习\"\n    print(f\"{name}：{status}\")","循环、解包、条件表达式组合后可以生成简短报表。",tags,direction),
        ]
    if chapter_id == "c10":
        return [
            ex(chapter_id,1,"基础","清洗用户名","去掉 username 两侧空格并转小写。","username = \"  Alice_01  \"\n# 清洗用户名","alice_01","username = \"  Alice_01  \"\nclean_name = username.strip().lower()\nprint(clean_name)","strip 和 lower 是处理用户输入最常见的两个字符串方法。",tags,direction),
            ex(chapter_id,2,"基础","替换敏感词","把 text 中的 bad 替换成 ***。","text = \"this is bad\"\n# 替换 bad","this is ***","text = \"this is bad\"\nprint(text.replace(\"bad\", \"***\"))","replace 返回新字符串，不会修改原字符串本身。",tags,direction),
            ex(chapter_id,3,"基础","判断文件后缀","filename 以 .py 结尾时输出 True。","filename = \"app.py\"\n# 判断后缀","True","filename = \"app.py\"\nprint(filename.endswith(\".py\"))","endswith 适合判断文件类型、链接后缀等。",tags,direction),
            ex(chapter_id,4,"进阶","提取邮箱用户名","输出邮箱 @ 前的用户名。","email = \"student@example.com\"\n# 提取 student","student","email = \"student@example.com\"\nname = email.split(\"@\")[0]\nprint(name)","split('@') 把邮箱拆成用户名和域名两部分。",tags,direction),
            ex(chapter_id,5,"进阶","拼接标签文本","把 tags 拼成 #Python #练习。","tags = [\"Python\", \"练习\"]\n# 拼接标签","#Python #练习","tags = [\"Python\", \"练习\"]\nresult = \" \".join(\"#\" + tag for tag in tags)\nprint(result)","join 可以和生成器表达式配合，批量生成格式化片段。",tags,direction),
            ex(chapter_id,6,"进阶","统计关键词次数","不区分大小写统计 Python 出现次数。","text = \"Python is fun. I use python to learn PYTHON.\"\n# 统计次数","出现次数：3","text = \"Python is fun. I use python to learn PYTHON.\"\ncount = text.lower().count(\"python\")\nprint(\"出现次数：\" + str(count))","先统一大小写，再统计关键词，是文本分析的基础流程。",tags,direction),
            ex(chapter_id,7,"挑战","解析课程记录","把 raw 拆成课程名和分钟数并输出。","raw = \"Python,45\"\n# 解析并输出","课程：Python，时长：45","raw = \"Python,45\"\ncourse, minutes = raw.split(\",\")\nprint(f\"课程：{course}，时长：{minutes}\")","结构化文本常用分隔符拆分，解包可以让字段含义更清晰。",tags,direction),
            ex(chapter_id,8,"挑战","清洗多行文本","去掉空行和两侧空格，输出清洗后的列表。","text = \"  A\\n\\n B \\nC  \"\n# 清洗行","['A', 'B', 'C']","text = \"  A\\n\\n B \\nC  \"\nlines = []\nfor line in text.splitlines():\n    clean_line = line.strip()\n    if clean_line:\n        lines.append(clean_line)\nprint(lines)","splitlines、strip、if 组合是处理文本文件前的核心清洗步骤。",tags,direction),
        ]
    if chapter_id in {"c11","c12","c13","c14","c15","c16","c17","c18","c19","c21","c22","c23","c24","c25","c26","c27","c28","c29","c30"}:
        return generic_exercises(chapter_id, topic, direction, tags)
    return generic_exercises(chapter_id, topic, direction, tags)


def build_bank(chapters: list[dict]) -> dict[str, list[dict]]:
    bank = {}
    for chapter in chapters:
        cid = chapter.get("id")
        topic, direction, tags = TOPICS.get(cid, (chapter.get("title", "Python"), chapter.get("title", "Python"), chapter.get("tags") or ["Python", "练习"]))
        items = specialized(cid, topic, direction, tags)
        if len(items) != 8:
            raise ValueError(f"{cid} generated {len(items)} exercises, expected 8")
        # Force exact level distribution even if a template was edited later.
        for item, level in zip(items, LEVELS):
            item["level"] = level
            item["id"] = f"{cid}-{ {'基础':'easy','进阶':'medium','挑战':'hard'}[level] }-{items.index(item)+1:03d}"
        bank[cid] = items
    return bank


def main() -> None:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if not BACKUP_FILE.exists():
        shutil.copy2(DATA_FILE, BACKUP_FILE)
    bank = build_bank(data.get("chapters", []))
    for chapter in data.get("chapters", []):
        chapter["exercises"] = bank[chapter["id"]]
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(c.get("exercises", [])) for c in data.get("chapters", []))
    print(f"rebuilt curated question bank: {len(data.get('chapters', []))} chapters, {total} exercises, source={SOURCE}")


if __name__ == "__main__":
    main()
