import json
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / 'data.json'


@lru_cache(maxsize=1)
def load_data():
    with DATA_FILE.open('r', encoding='utf-8') as f:
        return json.load(f)


def get_stages(data=None):
    data = data or load_data()
    return data.get('stages', [])


def get_chapters(data=None):
    data = data or load_data()
    return data.get('chapters', [])


def get_projects(data=None):
    data = data or load_data()
    return data.get('projects', [])


def chapter_by_id(chapter_id, data=None):
    chapters = get_chapters(data)
    return next((c for c in chapters if c.get('id') == chapter_id), chapters[0] if chapters else None)


def stage_by_id(stage_id, data=None):
    stages = get_stages(data)
    return next((s for s in stages if s.get('id') == stage_id), None)


def project_by_id(project_id, data=None):
    projects = get_projects(data)
    return next((p for p in projects if p.get('id') == project_id), projects[0] if projects else None)


def flatten_practices(data=None):
    data = data or load_data()
    practices = []
    for chapter in get_chapters(data):
        for index, exercise in enumerate(chapter.get('exercises', [])):
            starter = exercise.get('starter') or exercise.get('answerCode') or exercise.get('answer') or '# 请在这里完成练习'
            item = dict(exercise)
            item.update({
                'practiceId': f"{chapter.get('id')}::{index}",
                'lessonId': chapter.get('id'),
                'lessonTitle': chapter.get('title'),
                'lessonOrder': chapter.get('order'),
                'index': index,
                'taskGoal': exercise.get('taskGoal') or exercise.get('text') or '',
                'starter': starter,
                'expectedOutput': exercise.get('expectedOutput') or '请运行参考答案查看输出。',
                'answerCode': exercise.get('answerCode') or starter,
                'analysis': exercise.get('analysis') or exercise.get('hint') or '本题练习目标、题干、代码和输出均来自同一道练习。',
            })
            practices.append(item)
    return practices


def practice_by_index(index, data=None):
    practices = flatten_practices(data)
    if not practices:
        return None, 0
    try:
        index = int(index)
    except (TypeError, ValueError):
        index = 0
    index = max(0, min(index, len(practices) - 1))
    return practices[index], index


def practice_index_for(lesson_id, exercise_index=0, data=None):
    for idx, practice in enumerate(flatten_practices(data)):
        if practice.get('lessonId') == lesson_id and practice.get('index') == int(exercise_index or 0):
            return idx
    return 0


def guided_steps_for(chapter):
    exercises = (chapter.get('exercises') or [])[:3]
    concept_code = chapter.get('code') or 'print("开始学习 Python")'
    steps = [{
        'kind': 'read',
        'title': '先观察：这一章要解决什么问题？',
        'goal': chapter.get('goal', ''),
        'explain': f"{chapter.get('lifeCase') or chapter.get('concept') or ''} 先不要急着背语法，先运行一小段代码，观察屏幕输出和变量变化。",
        'starter': concept_code,
        'expected': chapter.get('output') or '运行示例代码，观察输出。',
        'hint': '先点击运行，看看代码做了什么；再试着改一处字符串或数字。',
        'answer': concept_code,
    }]
    for i, exercise in enumerate(exercises):
        starter = exercise.get('starter') or exercise.get('answerCode') or exercise.get('answer') or '# 在这里写代码'
        steps.append({
            'kind': 'practice',
            'title': f"动手 {i + 1}：{exercise.get('text', '')}",
            'goal': exercise.get('taskGoal') or exercise.get('text') or '',
            'explain': exercise.get('analysis') or exercise.get('hint') or '修改代码并运行，直到输出接近预期结果。',
            'starter': starter,
            'expected': exercise.get('expectedOutput') or '运行后观察输出。',
            'hint': exercise.get('hint') or '先看变量，再看 print 输出。',
            'answer': exercise.get('answerCode') or starter,
        })
    steps.append({
        'kind': 'reflect',
        'title': '复盘：我能解释这段代码吗？',
        'goal': '用自己的话总结本章核心点。',
        'explain': '最后一步不是新语法，而是确认你能解释代码为什么这样写。',
        'starter': f"# 复盘本章：{chapter.get('title', '')}\nprint(\"我学会了：{(chapter.get('summary') or [chapter.get('goal', '')])[0]}\")",
        'expected': '输出一句自己的学习总结。',
        'hint': '把 print 里的文字改成你自己的总结。',
        'answer': f"print(\"我学会了 {chapter.get('title', '')} 的核心用法，并能写一个小例子。\")",
    })
    return steps


def bootstrap(data=None):
    data = data or load_data()
    chapters = get_chapters(data)
    projects = get_projects(data)
    practices = flatten_practices(data)
    return {
        'stats': {
            'stages': len(get_stages(data)),
            'chapters': len(chapters),
            'projects': len(projects),
            'practices': len(practices),
        },
        'defaultIds': {
            'lessonId': chapters[0].get('id') if chapters else None,
            'projectId': projects[0].get('id') if projects else None,
        },
    }
