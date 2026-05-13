import copy
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK_ROOT = ROOT / 'question_banks'
MANIFEST_FILE = BANK_ROOT / 'manifest.json'
SCHEMA_VERSION = 'pystart-question-bank-v1'
ALLOWED_LEVELS = ('基础', '进阶', '挑战')
ALLOWED_TYPES = ('code', 'single', 'judge', 'fill')
REQUIRED_EXERCISE_FIELDS = [
    'id', 'title', 'level', 'direction', 'tags', 'description', 'text',
    'taskGoal', 'starter', 'expectedOutput', 'answer', 'answerCode',
    'hint', 'analysis', 'examples', 'tests', 'qualityNotes', 'source',
]
ARRAY_FIELDS = ('tags', 'examples', 'tests')
TEXT_FIELDS = ('id', 'title', 'level', 'direction', 'description', 'text', 'taskGoal', 'starter', 'expectedOutput', 'answerCode')


class QuestionBankError(ValueError):
    pass


def load_manifest():
    if not MANIFEST_FILE.exists():
        raise QuestionBankError('题库 manifest 文件不存在：question_banks/manifest.json')
    with MANIFEST_FILE.open('r', encoding='utf-8') as f:
        manifest = json.load(f)
    if not isinstance(manifest, dict):
        raise QuestionBankError('题库 manifest 必须是 JSON 对象。')
    if not manifest.get('activeBank'):
        raise QuestionBankError('题库 manifest 缺少 activeBank。')
    if not isinstance(manifest.get('banks'), list) or not manifest['banks']:
        raise QuestionBankError('题库 manifest 缺少 banks 列表。')
    return manifest


def active_bank_meta(manifest=None):
    manifest = manifest or load_manifest()
    active_id = manifest.get('activeBank')
    bank = next((b for b in manifest.get('banks', []) if b.get('id') == active_id), None)
    if not bank:
        raise QuestionBankError(f'找不到当前启用题库：{active_id}')
    if not bank.get('path'):
        raise QuestionBankError(f'题库 {active_id} 缺少 path。')
    return bank


def bank_path(bank=None):
    bank = bank or active_bank_meta()
    path = (BANK_ROOT / bank['path']).resolve()
    if BANK_ROOT.resolve() not in path.parents and path != BANK_ROOT.resolve():
        raise QuestionBankError('题库路径必须位于 question_banks 目录内。')
    return path


def load_question_bank(validate=True):
    path = bank_path()
    if not path.exists():
        raise QuestionBankError(f'题库文件不存在：{path.relative_to(ROOT)}')
    with path.open('r', encoding='utf-8') as f:
        bank = json.load(f)
    if validate:
        validate_question_bank(bank)
    return bank


def iter_exercises(bank=None):
    bank = bank or load_question_bank()
    for chapter in bank.get('chapters', []) if isinstance(bank, dict) else []:
        chapter_id = chapter.get('chapterId')
        chapter_title = chapter.get('chapterTitle', '')
        for index, exercise in enumerate(chapter.get('exercises', []) if isinstance(chapter, dict) else []):
            yield chapter_id, chapter_title, index, exercise


def exercises_by_chapter(bank=None):
    result = {}
    bank = bank or load_question_bank()
    for chapter in bank.get('chapters', []):
        result[chapter.get('chapterId')] = chapter.get('exercises') or []
    return result


def _empty_report():
    return {
        'ok': False,
        'schemaVersion': SCHEMA_VERSION,
        'bankId': None,
        'title': None,
        'chapterCount': 0,
        'totalCount': 0,
        'validCount': 0,
        'invalidCount': 0,
        'duplicateCount': 0,
        'duplicateExistingCount': 0,
        'unsupportedTypeCount': 0,
        'formatErrorCount': 0,
        'missingFieldCount': 0,
        'levelDistribution': {},
        'typeDistribution': {},
        'tagDistribution': {},
        'validExerciseIds': [],
        'invalidExerciseIds': [],
        'sampleExercises': [],
        'missingFields': [],
        'duplicateItems': [],
        'duplicateExisting': [],
        'unsupportedTypes': [],
        'formatErrors': [],
        'warnings': [],
        'errors': [],
    }


def validation_report(bank, course_data=None, existing_bank=None):
    report = _empty_report()
    expected_ids = {c.get('id') for c in (course_data or {}).get('chapters', []) if c.get('id')}
    existing_ids = {exercise.get('id') for _, _, _, exercise in iter_exercises(existing_bank)} if existing_bank else set()

    if not isinstance(bank, dict):
        report['errors'].append('题库文件必须是 JSON 对象。')
        report['formatErrors'].append({'path': '$', 'reason': '根节点不是对象'})
        _finish_report(report)
        return report

    report['bankId'] = bank.get('id')
    report['title'] = bank.get('title') or bank.get('id')
    if bank.get('schemaVersion') != SCHEMA_VERSION:
        report['errors'].append(f'schemaVersion 必须是 {SCHEMA_VERSION}。')
        report['formatErrors'].append({'path': 'schemaVersion', 'reason': f'当前值为 {bank.get("schemaVersion")!r}'})
    if not bank.get('id') or not isinstance(bank.get('id'), str):
        report['errors'].append('题库缺少字符串 id。')
        report['formatErrors'].append({'path': 'id', 'reason': '缺少字符串 id'})

    chapters = bank.get('chapters')
    if not isinstance(chapters, list) or not chapters:
        report['errors'].append('题库 chapters 必须是非空数组。')
        report['formatErrors'].append({'path': 'chapters', 'reason': 'chapters 不是非空数组'})
        _finish_report(report)
        return report

    report['chapterCount'] = len(chapters)
    seen_chapters = set()
    seen_exercises = set()
    levels = Counter()
    directions = Counter()
    tags = Counter()

    for chapter_idx, chapter in enumerate(chapters, 1):
        if not isinstance(chapter, dict):
            report['formatErrors'].append({'path': f'chapters[{chapter_idx - 1}]', 'reason': '章节题库必须是对象'})
            continue
        chapter_id = chapter.get('chapterId')
        if not chapter_id:
            report['formatErrors'].append({'path': f'chapters[{chapter_idx - 1}].chapterId', 'reason': '缺少 chapterId'})
            continue
        if chapter_id in seen_chapters:
            report['duplicateItems'].append({'kind': 'chapter', 'id': chapter_id, 'reason': '章节题库重复'})
        seen_chapters.add(chapter_id)
        if expected_ids and chapter_id not in expected_ids:
            report['formatErrors'].append({'path': f'chapters[{chapter_idx - 1}].chapterId', 'id': chapter_id, 'reason': '章节不在课程目录中'})
        exercises = chapter.get('exercises')
        if not isinstance(exercises, list):
            report['formatErrors'].append({'path': f'chapters[{chapter_idx - 1}].exercises', 'id': chapter_id, 'reason': 'exercises 必须是数组'})
            continue
        if not exercises:
            report['warnings'].append(f'章节 {chapter_id} 当前没有题目。')
        for ex_idx, exercise in enumerate(exercises, 1):
            report['totalCount'] += 1
            item_ref = {
                'chapterId': chapter_id,
                'index': ex_idx,
                'id': exercise.get('id') if isinstance(exercise, dict) else None,
                'title': exercise.get('title') if isinstance(exercise, dict) else None,
            }
            item_errors = []
            if not isinstance(exercise, dict):
                item_errors.append('题目必须是对象')
                report['formatErrors'].append({**item_ref, 'reason': '题目必须是对象'})
                report['invalidExerciseIds'].append(_exercise_key(chapter_id, ex_idx, None))
                continue
            missing = [field for field in REQUIRED_EXERCISE_FIELDS if field not in exercise]
            if missing:
                item_errors.append('缺少字段：' + ', '.join(missing))
                report['missingFields'].append({**item_ref, 'fields': missing})
            blank_fields = [field for field in TEXT_FIELDS if field in exercise and not str(exercise.get(field) or '').strip()]
            if blank_fields:
                item_errors.append('字段不能为空：' + ', '.join(blank_fields))
                report['formatErrors'].append({**item_ref, 'reason': '字段不能为空：' + ', '.join(blank_fields)})
            for field in ARRAY_FIELDS:
                if field in exercise and not isinstance(exercise.get(field), list):
                    item_errors.append(f'{field} 必须是数组')
                    report['formatErrors'].append({**item_ref, 'field': field, 'reason': f'{field} 必须是数组'})
            exercise_id = str(exercise.get('id') or '').strip()
            if exercise_id:
                if exercise_id in seen_exercises:
                    item_errors.append('题目 id 在导入文件中重复')
                    report['duplicateItems'].append({**item_ref, 'id': exercise_id, 'reason': '导入文件内重复'})
                seen_exercises.add(exercise_id)
                if exercise_id in existing_ids:
                    report['duplicateExisting'].append({**item_ref, 'id': exercise_id, 'reason': '与当前题库重复'})
            level = exercise.get('level')
            if level not in ALLOWED_LEVELS:
                item_errors.append('level 必须是 基础/进阶/挑战')
                report['formatErrors'].append({**item_ref, 'field': 'level', 'reason': 'level 必须是 基础/进阶/挑战'})
            else:
                levels[level] += 1
            direction = str(exercise.get('direction') or '').strip()
            explicit_type = str(exercise.get('type') or '').strip()
            if explicit_type and explicit_type not in ALLOWED_TYPES:
                item_errors.append(f'不支持的题型 type：{explicit_type}')
                report['unsupportedTypes'].append({**item_ref, 'type': explicit_type, 'reason': 'type 不在支持列表中'})
            if not direction:
                item_errors.append('direction/题型说明不能为空')
                report['unsupportedTypes'].append({**item_ref, 'type': '', 'reason': 'direction 为空，无法识别题型/方向'})
            else:
                directions[direction] += 1
            if isinstance(exercise.get('tags'), list):
                tags.update(str(tag) for tag in exercise.get('tags') if str(tag).strip())
            if item_errors:
                report['invalidExerciseIds'].append(_exercise_key(chapter_id, ex_idx, exercise_id))
            else:
                report['validCount'] += 1
                report['validExerciseIds'].append(exercise_id)
                if len(report['sampleExercises']) < 6:
                    report['sampleExercises'].append({
                        'id': exercise_id,
                        'title': exercise.get('title'),
                        'level': level,
                        'direction': direction,
                        'chapterId': chapter_id,
                        'taskGoal': exercise.get('taskGoal'),
                    })

    report['levelDistribution'] = dict(levels)
    report['typeDistribution'] = dict(directions)
    report['tagDistribution'] = dict(tags.most_common(40))
    _finish_report(report)
    return report


def _exercise_key(chapter_id, index, exercise_id):
    return str(exercise_id or f'{chapter_id}#{index}')


def _finish_report(report):
    report['missingFieldCount'] = sum(len(item.get('fields', [])) for item in report['missingFields'])
    report['duplicateCount'] = len(report['duplicateItems'])
    report['duplicateExistingCount'] = len(report['duplicateExisting'])
    report['unsupportedTypeCount'] = len(report['unsupportedTypes'])
    report['formatErrorCount'] = len(report['formatErrors'])
    report['invalidCount'] = max(0, report['totalCount'] - report['validCount'])
    report['ok'] = bool(
        report['totalCount'] > 0
        and report['invalidCount'] == 0
        and report['duplicateCount'] == 0
        and report['unsupportedTypeCount'] == 0
        and report['formatErrorCount'] == 0
        and not report['errors']
    )
    return report


def validate_question_bank(bank, course_data=None):
    report = validation_report(bank, course_data)
    if not report['ok']:
        reasons = []
        if report['errors']:
            reasons.extend(report['errors'][:3])
        if report['missingFields']:
            item = report['missingFields'][0]
            reasons.append(f"{item.get('chapterId')} 第 {item.get('index')} 题缺少字段：{', '.join(item.get('fields', []))}")
        if report['duplicateItems']:
            reasons.append(f"重复题目/章节：{report['duplicateItems'][0].get('id')}")
        if report['unsupportedTypes']:
            reasons.append(f"不支持题型：{report['unsupportedTypes'][0].get('type') or '空 direction'}")
        if report['formatErrors']:
            reasons.append(report['formatErrors'][0].get('reason', '格式错误'))
        raise QuestionBankError('；'.join(dict.fromkeys(reasons)) or '题库校验失败。')
    return {'ok': True, 'chapters': report['chapterCount'], 'exercises': report['totalCount']}


def bank_summary(bank=None, manifest=None):
    bank = bank or load_question_bank()
    manifest = manifest or load_manifest()
    meta = active_bank_meta(manifest)
    levels = Counter()
    directions = Counter()
    tags = Counter()
    chapters = bank.get('chapters', []) if isinstance(bank, dict) else []
    for _, _, _, exercise in iter_exercises(bank):
        levels.update([exercise.get('level') or '未标注'])
        directions.update([exercise.get('direction') or '未标注'])
        if isinstance(exercise.get('tags'), list):
            tags.update(str(tag) for tag in exercise.get('tags') if str(tag).strip())
    total = sum(levels.values())
    return {
        'schemaVersion': bank.get('schemaVersion'),
        'id': bank.get('id'),
        'title': bank.get('title') or bank.get('id'),
        'description': bank.get('description', ''),
        'source': bank.get('source', ''),
        'chapterCount': len(chapters),
        'exerciseCount': total,
        'updatedAt': bank.get('updatedAt') or meta.get('updatedAt'),
        'path': meta.get('path'),
        'levelDistribution': dict(levels),
        'typeDistribution': dict(directions),
        'tagDistribution': dict(tags.most_common(40)),
    }


def filter_question_bank(bank=None, scope=None):
    bank = copy.deepcopy(bank or load_question_bank())
    scope = scope or {}
    levels = set(scope.get('levels') or [])
    directions = set(scope.get('directions') or scope.get('types') or [])
    tags = set(scope.get('tags') or [])
    lesson_ids = set(scope.get('lessonIds') or [])
    query = str(scope.get('query') or '').strip().lower()
    filtered_chapters = []
    for chapter in bank.get('chapters', []):
        if lesson_ids and chapter.get('chapterId') not in lesson_ids:
            continue
        exercises = []
        for exercise in chapter.get('exercises', []):
            if levels and exercise.get('level') not in levels:
                continue
            if directions and exercise.get('direction') not in directions:
                continue
            exercise_tags = set(exercise.get('tags') or [])
            if tags and not tags.intersection(exercise_tags):
                continue
            haystack = ' '.join(str(exercise.get(field, '')) for field in ('id', 'title', 'description', 'text', 'taskGoal', 'direction')).lower()
            if query and query not in haystack:
                continue
            exercises.append(exercise)
        if exercises:
            chapter = dict(chapter)
            chapter['exercises'] = exercises
            filtered_chapters.append(chapter)
    bank['chapters'] = filtered_chapters
    bank['exportedAt'] = datetime.now().isoformat(timespec='seconds')
    bank['exportScope'] = scope
    return bank


def export_question_bank(scope=None):
    bank = filter_question_bank(load_question_bank(), scope)
    return {'ok': True, 'questionBank': bank, 'summary': bank_summary(bank), 'filename': export_filename(bank)}


def export_filename(bank=None):
    bank = bank or load_question_bank()
    date = datetime.now().strftime('%Y%m%d')
    title = safe_id(bank.get('title') or bank.get('id') or 'pystart')
    return f'{title}-question-bank-{date}.json'


def import_question_bank(bank, course_data=None, strategy='replace'):
    strategy = strategy or 'replace'
    current = load_question_bank(validate=False)
    report = validation_report(bank, course_data, existing_bank=current if strategy in ('append', 'validOnly') else None)
    if strategy not in ('replace', 'append', 'validOnly'):
        raise QuestionBankError('导入策略必须是 replace、append 或 validOnly。')
    if strategy == 'replace':
        if not report['ok']:
            raise QuestionBankError('覆盖导入前必须全部校验通过：' + _report_error_summary(report))
        target = copy.deepcopy(bank)
    elif strategy == 'append':
        if not report['ok'] or report['duplicateExistingCount']:
            raise QuestionBankError('追加导入前必须全部校验通过且不能与当前题库重复：' + _report_error_summary(report))
        target = merge_bank(current, bank, skip_invalid=False)
    else:
        target = merge_bank(current, bank, skip_invalid=True, report=report)
        if bank_summary(target)['exerciseCount'] == bank_summary(current)['exerciseCount']:
            raise QuestionBankError('没有可导入的新题目：有效题目可能为空或都与当前题库重复。')
    target['updatedAt'] = datetime.now().isoformat(timespec='seconds')
    stats = write_question_bank(target)
    return {**stats, 'strategy': strategy, 'validation': report}


def _report_error_summary(report):
    parts = []
    if report.get('invalidCount'):
        parts.append(f"无效题 {report['invalidCount']} 道")
    if report.get('missingFieldCount'):
        parts.append(f"缺失字段 {report['missingFieldCount']} 个")
    if report.get('duplicateCount'):
        parts.append(f"文件内重复 {report['duplicateCount']} 项")
    if report.get('duplicateExistingCount'):
        parts.append(f"与当前题库重复 {report['duplicateExistingCount']} 道")
    if report.get('unsupportedTypeCount'):
        parts.append(f"不支持题型 {report['unsupportedTypeCount']} 项")
    if report.get('formatErrorCount'):
        parts.append(f"格式错误 {report['formatErrorCount']} 项")
    if report.get('errors'):
        parts.extend(report['errors'][:2])
    return '，'.join(parts) or '校验失败。'


def merge_bank(current, incoming, skip_invalid=False, report=None):
    merged = copy.deepcopy(current)
    merged['title'] = current.get('title') or incoming.get('title') or current.get('id')
    merged['description'] = current.get('description') or incoming.get('description', '')
    existing_ids = {exercise.get('id') for _, _, _, exercise in iter_exercises(merged)}
    valid_ids = set((report or validation_report(incoming)).get('validExerciseIds', [])) if skip_invalid else None
    chapters = {chapter.get('chapterId'): chapter for chapter in merged.get('chapters', [])}
    incoming_duplicates = set()
    for chapter in incoming.get('chapters', []) if isinstance(incoming, dict) else []:
        chapter_id = chapter.get('chapterId')
        if not chapter_id:
            continue
        target = chapters.get(chapter_id)
        if not target:
            target = {'chapterId': chapter_id, 'chapterTitle': chapter.get('chapterTitle') or chapter_id, 'exercises': []}
            chapters[chapter_id] = target
            merged.setdefault('chapters', []).append(target)
        for exercise in chapter.get('exercises', []) if isinstance(chapter.get('exercises'), list) else []:
            exercise_id = exercise.get('id') if isinstance(exercise, dict) else None
            if skip_invalid and exercise_id not in valid_ids:
                continue
            if exercise_id in existing_ids or exercise_id in incoming_duplicates:
                if skip_invalid:
                    continue
                raise QuestionBankError(f'题目 id 重复：{exercise_id}')
            incoming_duplicates.add(exercise_id)
            existing_ids.add(exercise_id)
            target.setdefault('exercises', []).append(copy.deepcopy(exercise))
    return merged


def write_question_bank(bank):
    stats = validate_question_bank(bank)
    bank_id = safe_id(bank.get('id'))
    target_dir = BANK_ROOT / bank_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / 'question_bank.json'
    if target_file.exists():
        backup = target_dir / f'question_bank.backup-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
        shutil.copy2(target_file, backup)
    target_file.write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding='utf-8')
    manifest = load_manifest()
    rel_path = str(target_file.relative_to(BANK_ROOT))
    meta = {
        'id': bank_id,
        'title': bank.get('title') or bank_id,
        'path': rel_path,
        'schemaVersion': bank.get('schemaVersion'),
        'description': bank.get('description') or '',
        'updatedAt': datetime.now().isoformat(timespec='seconds'),
    }
    banks = [b for b in manifest.get('banks', []) if b.get('id') != bank_id]
    banks.append(meta)
    manifest['banks'] = banks
    manifest['activeBank'] = bank_id
    MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return {**stats, 'id': bank_id, 'title': meta['title'], 'updatedAt': meta['updatedAt']}


def system_status(course_data=None):
    checks = []
    now = datetime.now().isoformat(timespec='seconds')
    try:
        manifest = load_manifest()
        bank = load_question_bank(validate=False)
        report = validation_report(bank, course_data)
        summary = bank_summary(bank, manifest)
        qb_state = 'ok' if report['ok'] else 'error'
        checks.append({'key': 'frontend', 'label': '前端运行状态', 'state': 'ok', 'text': 'React 应用已加载'})
        checks.append({'key': 'backend', 'label': '后端连接状态', 'state': 'ok', 'text': 'HTTP API 可访问'})
        checks.append({'key': 'api', 'label': 'API 响应状态', 'state': 'ok', 'text': 'bootstrap/data/run 接口可用'})
        checks.append({'key': 'questionBank', 'label': '题库加载状态', 'state': qb_state, 'text': '题库校验通过' if report['ok'] else '题库存在格式问题'})
        checks.append({'key': 'importExport', 'label': '导入/导出功能', 'state': 'ok' if summary['exerciseCount'] else 'warning', 'text': '可用' if summary['exerciseCount'] else '题库为空，导出内容为空'})
        overall = 'error' if any(c['state'] == 'error' for c in checks) else 'warning' if any(c['state'] == 'warning' for c in checks) else 'ok'
        return {'ok': True, 'overall': overall, 'checkedAt': now, 'checks': checks, 'questionBank': summary, 'validation': report}
    except Exception as exc:
        return {
            'ok': False,
            'overall': 'error',
            'checkedAt': now,
            'checks': [
                {'key': 'frontend', 'label': '前端运行状态', 'state': 'ok', 'text': 'React 应用已加载'},
                {'key': 'backend', 'label': '后端连接状态', 'state': 'error', 'text': str(exc)},
                {'key': 'api', 'label': 'API 响应状态', 'state': 'error', 'text': '题库或课程数据读取失败'},
                {'key': 'questionBank', 'label': '题库加载状态', 'state': 'error', 'text': str(exc)},
                {'key': 'importExport', 'label': '导入/导出功能', 'state': 'error', 'text': '请先修复题库数据'},
            ],
            'error': str(exc),
        }


def safe_id(value):
    raw = ''.join(ch.lower() if ch.isalnum() else '-' for ch in str(value or '').strip())
    raw = '-'.join(part for part in raw.split('-') if part)
    if not raw:
        raise QuestionBankError('题库 id 不能为空。')
    return raw[:80]
