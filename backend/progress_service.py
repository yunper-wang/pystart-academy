from . import data_service


def pct(done, total):
    return round(done / total * 100) if total else 0


def normalize_progress(progress):
    progress = progress or {}
    return {
        'completedLessons': list(dict.fromkeys(progress.get('completedLessons') or [])),
        'completedProjects': list(dict.fromkeys(progress.get('completedProjects') or [])),
        'quizResults': progress.get('quizResults') or {},
        'reviewItems': list(dict.fromkeys(progress.get('reviewItems') or [])),
        'currentLessonId': progress.get('currentLessonId'),
    }


def lesson_status(chapter_id, progress):
    if chapter_id in progress['completedLessons']:
        return 'done'
    if chapter_id == progress.get('currentLessonId'):
        return 'learning'
    return 'todo'


def summarize(progress, data=None):
    data = data or data_service.load_data()
    progress = normalize_progress(progress)
    chapters = data_service.get_chapters(data)
    stages = data_service.get_stages(data)
    projects = data_service.get_projects(data)
    completed_lessons = set(progress['completedLessons'])
    completed_projects = set(progress['completedProjects'])
    lesson_status_map = {c.get('id'): lesson_status(c.get('id'), progress) for c in chapters}
    project_status_map = {p.get('id'): ('done' if p.get('id') in completed_projects else 'todo') for p in projects}
    stage_progress = []
    for stage in stages:
        stage_chapters = [c for c in chapters if c.get('stageId') == stage.get('id')]
        done = sum(1 for c in stage_chapters if c.get('id') in completed_lessons)
        stage_progress.append({
            'id': stage.get('id'),
            'title': stage.get('title'),
            'desc': stage.get('desc', ''),
            'done': done,
            'total': len(stage_chapters),
            'percent': pct(done, len(stage_chapters)),
        })
    next_lesson = next((c for c in chapters if c.get('id') not in completed_lessons), None)
    done_count = len(completed_lessons)
    project_done_count = len(completed_projects)
    achievements = [
        {'title': '🌱 完成第一章', 'unlocked': done_count >= 1},
        {'title': '🧱 掌握基础语法', 'unlocked': done_count >= 5},
        {'title': '📦 会使用数据结构', 'unlocked': done_count >= 12},
        {'title': '🚀 完成第一个项目', 'unlocked': project_done_count >= 1},
    ]
    review_titles = []
    for lesson_id in progress['reviewItems'][-5:]:
        chapter = data_service.chapter_by_id(lesson_id, data)
        if chapter:
            review_titles.append(chapter.get('title'))
    return {
        'progress': progress,
        'completedLessonCount': done_count,
        'totalLessonCount': len(chapters),
        'completedProjectCount': project_done_count,
        'totalProjectCount': len(projects),
        'totalProgress': pct(done_count, len(chapters)),
        'nextLesson': {'id': next_lesson.get('id'), 'title': next_lesson.get('title')} if next_lesson else None,
        'stageProgress': stage_progress,
        'achievements': achievements,
        'reviewTitles': review_titles,
        'lessonStatusMap': lesson_status_map,
        'projectStatusMap': project_status_map,
    }
