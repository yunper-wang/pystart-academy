from . import data_service, progress_service
from .html import esc, tags, status_label, ul, code_block, inline_output


def stage_title(stage_id, data):
    stage = data_service.stage_by_id(stage_id, data)
    return stage.get('title') if stage else ''


def page_home(progress=None, data=None):
    data = data or data_service.load_data()
    summary = progress_service.summarize(progress, data)
    hero_stats = (
        f'<div class="stat-chip"><strong>{len(data_service.get_stages(data))}</strong>学习阶段</div>'
        f'<div class="stat-chip"><strong>{len(data_service.get_chapters(data))}</strong>核心章节</div>'
        f'<div class="stat-chip"><strong>{summary["totalProgress"]}%</strong>当前进度</div>'
    )
    stage_cards = []
    for i, stage in enumerate(data_service.get_stages(data), 1):
        sp = next(x for x in summary['stageProgress'] if x['id'] == stage.get('id'))
        stage_cards.append(
            f'<article class="roadmap-item"><span>阶段 {i}</span><h3>{esc(stage.get("title"))}</h3>'
            f'<p>{esc(stage.get("desc", ""))}</p><div class="progress-bar"><div class="progress-fill" style="width:{sp["percent"]}%"></div></div>'
            f'<small>{sp["done"]}/{sp["total"]} 完成</small></article>'
        )
    return {'html': {'heroStats': hero_stats, 'homeStages': ''.join(stage_cards)}, 'summary': summary}


def course_controls(data=None):
    data = data or data_service.load_data()
    stage_options = '<option value="all">全部阶段</option>' + ''.join(
        f'<option value="{esc(s.get("id"))}">{esc(s.get("title"))}</option>' for s in data_service.get_stages(data)
    )
    sidebar = '<button class="side-btn active" data-stage="all">全部课程</button>' + ''.join(
        f'<button class="side-btn" data-stage="{esc(s.get("id"))}">阶段 {i}<br><small>{esc((s.get("title") or "").split("：")[-1])}</small></button>'
        for i, s in enumerate(data_service.get_stages(data), 1)
    )
    lesson_options = ''.join(
        f'<option value="{esc(c.get("id"))}">{esc(c.get("order"))}. {esc(c.get("title"))}</option>' for c in data_service.get_chapters(data)
    )
    return {'stageOptions': stage_options, 'stageSidebar': sidebar, 'quizLessonOptions': lesson_options}


def page_courses(progress=None, stage_filter='all', query='', current_lesson_id=None, data=None):
    data = data or data_service.load_data()
    summary = progress_service.summarize(progress, data)
    query_l = (query or '').strip().lower()
    blocks = []
    for i, stage in enumerate(data_service.get_stages(data), 1):
        if stage_filter != 'all' and stage_filter != stage.get('id'):
            continue
        chapters = [c for c in data_service.get_chapters(data) if c.get('stageId') == stage.get('id')]
        if query_l:
            chapters = [c for c in chapters if query_l in (c.get('title','') + c.get('goal','') + ','.join(c.get('tags') or [])).lower()]
        if not chapters:
            continue
        done = sum(1 for c in chapters if summary['lessonStatusMap'].get(c.get('id')) == 'done')
        cards = []
        for c in chapters:
            status = summary['lessonStatusMap'].get(c.get('id'), 'todo')
            active = ' active' if c.get('id') == current_lesson_id else ''
            cards.append(
                f'<article class="course-card{active}" data-lesson="{esc(c.get("id"))}"><div class="lesson-title-row"><h4>{esc(c.get("order"))}. {esc(c.get("title"))}</h4>{status_label(status)}</div>'
                f'<p>{esc(c.get("goal"))}</p><div class="meta-row"><span class="badge">{esc(c.get("difficulty"))}</span><span class="tag">{esc(c.get("duration"))}</span>{tags(c.get("tags"))}</div></article>'
            )
        blocks.append(
            f'<section class="course-stage"><div class="course-stage-header"><div><span class="eyebrow">Stage {i}</span><h3>{esc(stage.get("title"))}</h3><p>{esc(stage.get("desc", ""))}</p></div><div class="badge">{done}/{len(chapters)} 完成</div></div><div class="course-grid">{"".join(cards)}</div></section>'
        )
    return {'html': {'courseStageList': ''.join(blocks) or '<div class="empty">没有找到匹配课程。</div>'}, 'summary': summary}


def render_knowledge_detail(chapter):
    kd = chapter.get('knowledgeDetail')
    if not kd:
        return ''
    section_cards = ''.join(f'<article class="knowledge-card"><h5>{esc(s.get("title"))}</h5><p>{esc(s.get("body"))}</p></article>' for s in kd.get('sections') or [])
    topics = ''.join(f'<span class="tag">{esc(t)}</span>' for t in kd.get('sourceTopics') or [])
    steps = ul(kd.get('learningSteps') or [])
    pitfalls = ul(kd.get('pitfalls') or [], 'mistake-list')
    return f'<section class="knowledge-detail"><div class="knowledge-head"><span class="eyebrow">Knowledge Notes</span><h4>系统知识点详解</h4><p>{esc(kd.get("inspiredBy", ""))}</p></div><div class="knowledge-topic-row">{topics}</div><div class="knowledge-grid">{section_cards}</div><div class="content-grid"><div class="info-panel"><h4>学习步骤</h4>{steps}</div><div class="info-panel"><h4>常见陷阱</h4>{pitfalls}</div></div></section>'


def page_lesson(progress=None, lesson_id=None, data=None):
    data = data or data_service.load_data()
    progress = progress_service.normalize_progress(progress)
    chapter = data_service.chapter_by_id(lesson_id or progress.get('currentLessonId'), data)
    summary = progress_service.summarize({**progress, 'currentLessonId': chapter.get('id')}, data)
    chapters = data_service.get_chapters(data)
    idx = chapters.index(chapter)
    lesson_list = ''.join(
        f'<button class="lesson-btn {"active" if c.get("id") == chapter.get("id") else ""}" data-lesson="{esc(c.get("id"))}">{esc(c.get("order"))}. {esc(c.get("title"))}<br><small>{esc(stage_title(c.get("stageId"), data))}</small></button>'
        for c in chapters
    )
    exercises = ''.join(
        f'<button class="mini-exercise exercise-link" data-lesson="{esc(chapter.get("id"))}" data-exercise="{i}" type="button"><span class="badge">{esc(e.get("level"))}</span><strong> 练习 {i+1}</strong><p>{esc(e.get("text"))}</p><small>提示：{esc(e.get("hint"))}</small><em>进入练习 →</em></button>'
        for i, e in enumerate(chapter.get('exercises') or [])
    )
    status = summary['lessonStatusMap'].get(chapter.get('id'), 'todo')
    detail = f'''<div class="lesson-title-row"><div><span class="eyebrow">{esc(stage_title(chapter.get('stageId'), data))}</span><h3>{esc(chapter.get('order'))}. {esc(chapter.get('title'))}</h3><p>{esc(chapter.get('goal'))}</p></div>{status_label(status)}</div>
<div class="meta-row"><span class="badge">{esc(chapter.get('difficulty'))}</span><span class="tag">{esc(chapter.get('duration'))}</span>{tags(chapter.get('tags'))}</div><div class="divider"></div>
<div class="content-grid"><div class="info-panel"><h4>学习目标</h4><p>{esc(chapter.get('goal'))}</p></div><div class="info-panel"><h4>生活化理解</h4><p>{esc(chapter.get('lifeCase'))}</p></div><div class="info-panel"><h4>核心概念</h4><p>{esc(chapter.get('concept'))}</p></div><div class="info-panel"><h4>语法规则</h4><p>{esc(chapter.get('syntax'))}</p></div></div>
<h4>示例代码</h4>{code_block(chapter.get('code', ''))}<h4>运行结果说明</h4><div class="output-result">{esc(chapter.get('output'))}</div>
<div class="content-grid"><div class="info-panel"><h4>应用场景</h4><p>{esc(chapter.get('application'))}</p></div><div class="info-panel"><h4>初学者常见错误</h4>{ul(chapter.get('mistakes'), 'mistake-list')}</div></div>
{render_knowledge_detail(chapter)}<h4>课后练习</h4><div class="mini-exercises">{exercises}</div><h4>本章总结</h4>{ul(chapter.get('summary'))}
<div class="button-row"><button class="ghost-btn" {'disabled' if idx == 0 else ''} id="prevLessonBtn">上一章</button><button class="primary-btn" id="markLessonBtn">{'取消完成' if status == 'done' else '标记完成'}</button><button class="ghost-btn" {'disabled' if idx == len(chapters)-1 else ''} id="nextLessonBtn">下一章</button></div>'''
    return {'html': {'lessonList': lesson_list, 'lessonDetail': detail}, 'currentLessonId': chapter.get('id'), 'prevLessonId': chapters[idx-1].get('id') if idx > 0 else None, 'nextLessonId': chapters[idx+1].get('id') if idx < len(chapters)-1 else None}


def page_practice(index=0, data=None):
    data = data or data_service.load_data()
    practices = data_service.flatten_practices(data)
    practice, index = data_service.practice_by_index(index, data)
    picker = ''.join(
        f'<button class="practice-btn {"active" if i == index else ""}" data-i="{i}">{esc(p.get("lessonTitle"))}<br><small>{esc(p.get("level"))} · 练习 {p.get("index") + 1}</small></button>'
        for i, p in enumerate(practices)
    )
    futurecoder = ''
    if practice and practice.get('source') == 'futurecoder-authorized-copy':
        futurecoder = f'<div class="futurecoder-original"><h4>futurecoder 原文</h4><div class="futurecoder-html">{practice.get("futurecoderOriginalHtml") or ""}</div>'
        if practice.get('futurecoderOriginalCode'):
            futurecoder += f'<h4>futurecoder 原题代码</h4>{inline_output(practice.get("futurecoderOriginalCode"))}'
        futurecoder += '</div>'
    task = '' if not practice else f'<span class="badge">{esc(practice.get("level"))}</span><h3>{esc(practice.get("lessonTitle"))}：练习 {practice.get("index") + 1}</h3><p><strong>任务目标：</strong>{esc(practice.get("taskGoal"))}</p><p><strong>原练习：</strong>{esc(practice.get("text"))}</p>{futurecoder}<p><strong>预期运行结果：</strong></p>{inline_output(practice.get("expectedOutput"))}'
    return {'html': {'practicePicker': picker, 'practiceTask': task}, 'practice': practice, 'currentPracticeIndex': index, 'totalPractices': len(practices)}


def page_guided(progress=None, lesson_id=None, step_index=0, data=None):
    data = data or data_service.load_data()
    progress = progress_service.normalize_progress(progress)
    summary = progress_service.summarize(progress, data)
    chapters = data_service.get_chapters(data)
    current = data_service.chapter_by_id(lesson_id or progress.get('currentLessonId'), data)
    steps = data_service.guided_steps_for(current)
    step_index = max(0, min(int(step_index or 0), len(steps)-1))
    step = steps[step_index]
    toc = ''.join(
        f'<button class="guided-toc-btn {"active" if c.get("id") == current.get("id") else ""}" data-guided="{esc(c.get("id"))}"><span>{esc(c.get("order"))}. {esc(c.get("title"))}</span><small>{"已完成" if summary["lessonStatusMap"].get(c.get("id")) == "done" else "未完成"} · {esc(stage_title(c.get("stageId"), data))}</small></button>'
        for c in chapters[:30]
    )
    header = f'<div><span class="eyebrow">Step-by-step Course</span><h3>{esc(current.get("order"))}. {esc(current.get("title"))}</h3><p>{esc(current.get("goal"))}</p></div><button class="soft-btn" id="guidedOpenLessonBtn">查看完整课程详情</button>'
    stepper = ''.join(
        f'<button class="step-pill {"active" if i == step_index else ""}" data-step="{i}">{i+1}. {"观察" if s.get("kind") == "read" else "练习" if s.get("kind") == "practice" else "复盘"}</button>'
        for i, s in enumerate(steps)
    )
    content = f'<span class="badge">{"观察代码" if step.get("kind") == "read" else "动手练习" if step.get("kind") == "practice" else "复盘总结"}</span><h3>{esc(step.get("title"))}</h3><p><strong>目标：</strong>{esc(step.get("goal"))}</p><p>{esc(step.get("explain"))}</p><p><strong>期待结果：</strong></p>{inline_output(step.get("expected"))}'
    return {'html': {'guidedToc': toc, 'guidedHeader': header, 'guidedStepper': stepper, 'guidedContent': content}, 'currentGuidedLessonId': current.get('id'), 'currentGuidedStepIndex': step_index, 'step': step, 'stepCount': len(steps)}


def render_answer_input(question, i):
    qtype = question.get('type')
    if qtype == 'single':
        return ''.join(f'<label class="option"><input type="radio" name="q{i}" value="{esc(o)}"> {esc(o)}</label>' for o in question.get('options') or [])
    if qtype == 'judge':
        return ''.join(f'<label class="option"><input type="radio" name="q{i}" value="{o}"> {o}</label>' for o in ['正确', '错误'])
    return f'<input class="text-answer" id="qa-{i}" data-q="{i}" placeholder="请输入你的答案">'


def page_quiz(lesson_id=None, data=None):
    data = data or data_service.load_data()
    chapter = data_service.chapter_by_id(lesson_id, data)
    cards = ''.join(
        f'<article class="quiz-card" data-i="{i}"><span class="badge">{esc(q.get("type"))}</span><h4>{i+1}. {esc(q.get("question", "")).replace(chr(10), "<br>")}</h4>{render_answer_input(q, i)}<div class="quiz-result" id="qr-{i}" style="display:none"></div></article>'
        for i, q in enumerate(chapter.get('quiz') or [])
    )
    return {'html': {'quizList': cards}, 'lessonId': chapter.get('id'), 'lessonTitle': chapter.get('title'), 'questionCount': len(chapter.get('quiz') or [])}


def quiz_result_html(result):
    cards = []
    for i, item in enumerate(result.get('results') or []):
        cards.append(f'<div class="quiz-result-block" data-i="{i}"><strong>{"回答正确 ✅" if item.get("ok") else "需要复习 ❗"}</strong><p>你的答案：{esc(item.get("userAnswer"))}</p><p>正确答案：{esc(item.get("correctAnswer"))}</p><p>解析：{esc(item.get("explain"))}</p></div>')
    advice = f'<strong>得分：{result.get("score")} 分</strong><p>{esc(result.get("advice"))}</p>'
    return {'adviceHtml': advice, 'resultHtml': ''.join(cards)}


def page_projects(progress=None, project_id=None, data=None):
    data = data or data_service.load_data()
    summary = progress_service.summarize(progress, data)
    projects = data_service.get_projects(data)
    current = data_service.project_by_id(project_id, data)
    grid = ''.join(
        f'<article class="project-card {"active" if p.get("id") == current.get("id") else ""}" data-project="{esc(p.get("id"))}"><h3>{esc(p.get("title"))}</h3><p>{esc(p.get("goal"))}</p><div class="meta-row"><span class="badge">{esc(p.get("difficulty"))}</span><span class="tag">{esc(p.get("time"))}</span>{tags((p.get("tags") or [])[:4])}</div><div class="meta-row">{status_label(summary["projectStatusMap"].get(p.get("id"), "todo"))}</div></article>'
        for p in projects
    )
    status = summary['projectStatusMap'].get(current.get('id'), 'todo')
    reqs = ''.join(f'<div class="info-panel">{esc(r)}</div>' for r in current.get('requirements') or [])
    steps = ''.join(f'<li>{esc(s)}</li>' for s in current.get('steps') or [])
    detail = f'''<span class="eyebrow">Project Lab</span><h3>{esc(current.get('title'))}</h3><p class="project-goal">{esc(current.get('goal'))}</p><div class="meta-row"><span class="badge">{esc(current.get('difficulty'))}</span><span class="tag">{esc(current.get('time'))}</span>{tags(current.get('tags'))}</div>
<div class="project-section"><h4>项目目标</h4><p>{esc(current.get('goal'))}</p></div><div class="project-section"><h4>需求说明</h4><div class="requirements">{reqs}</div></div>
<div class="project-section"><h4>实现步骤</h4><ol class="step-list">{steps}</ol></div><div class="project-section"><h4>核心代码</h4>{code_block(current.get('keyCode', ''))}</div>
<div class="project-section"><h4>完整可运行代码</h4>{code_block(current.get('fullCode', ''))}</div><div class="project-section"><h4>测试示例</h4>{ul(current.get('examples'))}</div><div class="project-section"><h4>常见错误</h4>{ul(current.get('mistakes'), 'mistake-list')}</div><div class="project-section"><h4>拓展方向</h4>{ul(current.get('extend'))}</div><button class="primary-btn" id="markProjectBtn">{'取消完成项目' if status == 'done' else '标记完成项目'}</button>'''
    return {'html': {'projectGrid': grid, 'projectDetail': detail}, 'currentProjectId': current.get('id')}


def page_progress(progress=None, data=None):
    data = data or data_service.load_data()
    summary = progress_service.summarize(progress, data)
    achievements = ''.join(f'<div class="achievement {"" if a["unlocked"] else "locked"}">{esc(a["title"])}</div>' for a in summary['achievements'])
    stages = ''.join(f'<div><strong>{esc(s["title"])}</strong><div class="progress-bar"><div class="progress-fill" style="width:{s["percent"]}%"></div></div><small>{s["done"]}/{s["total"]}</small></div>' for s in summary['stageProgress'])
    review = '、'.join(summary['reviewTitles']) if summary['reviewTitles'] else '暂无错题。完成测验后这里会显示需要复习的章节。'
    next_title = summary['nextLesson']['title'] if summary['nextLesson'] else '进入更多项目实战'
    html = f'<div class="progress-overview"><div class="progress-card"><h3>总进度</h3><strong>{summary["totalProgress"]}%</strong><div class="progress-bar"><div class="progress-fill" style="width:{summary["totalProgress"]}%"></div></div></div><div class="progress-card"><h3>已完成章节</h3><strong>{summary["completedLessonCount"]}/{summary["totalLessonCount"]}</strong></div><div class="progress-card"><h3>已完成项目</h3><strong>{summary["completedProjectCount"]}/{summary["totalProjectCount"]}</strong></div><div class="progress-card"><h3>推荐下一步</h3><p>{esc(next_title)}</p></div></div><div class="progress-card"><h3>阶段进度</h3><div class="stage-progress-grid">{stages}</div></div><div class="progress-card"><h3>学习成就</h3><div class="achievement-grid">{achievements}</div></div><div class="progress-card"><h3>错题提示与复习建议</h3><p>{esc(review)}</p></div>'
    return {'html': {'progressDashboard': html}, 'summary': summary}
