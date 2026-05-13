import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK_ROOT = ROOT / 'question_banks'
MANIFEST_FILE = BANK_ROOT / 'manifest.json'
REQUIRED_EXERCISE_FIELDS = [
    'id', 'title', 'level', 'direction', 'tags', 'description', 'text',
    'taskGoal', 'starter', 'expectedOutput', 'answer', 'answerCode',
    'hint', 'analysis', 'examples', 'tests', 'qualityNotes', 'source',
]


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


def load_question_bank():
    path = bank_path()
    if not path.exists():
        raise QuestionBankError(f'题库文件不存在：{path.relative_to(ROOT)}')
    with path.open('r', encoding='utf-8') as f:
        bank = json.load(f)
    validate_question_bank(bank)
    return bank


def iter_exercises(bank=None):
    bank = bank or load_question_bank()
    for chapter in bank.get('chapters', []):
        chapter_id = chapter.get('chapterId')
        chapter_title = chapter.get('chapterTitle', '')
        for index, exercise in enumerate(chapter.get('exercises', [])):
            yield chapter_id, chapter_title, index, exercise


def exercises_by_chapter(bank=None):
    result = {}
    bank = bank or load_question_bank()
    for chapter in bank.get('chapters', []):
        result[chapter.get('chapterId')] = chapter.get('exercises') or []
    return result


def validate_question_bank(bank, course_data=None):
    if not isinstance(bank, dict):
        raise QuestionBankError('题库文件必须是 JSON 对象。')
    if bank.get('schemaVersion') != 'pystart-question-bank-v1':
        raise QuestionBankError('schemaVersion 必须是 pystart-question-bank-v1。')
    if not bank.get('id') or not isinstance(bank.get('id'), str):
        raise QuestionBankError('题库缺少字符串 id。')
    chapters = bank.get('chapters')
    if not isinstance(chapters, list) or not chapters:
        raise QuestionBankError('题库 chapters 必须是非空数组。')
    expected_ids = set()
    if course_data:
        expected_ids = {c.get('id') for c in course_data.get('chapters', []) if c.get('id')}
    seen_chapters = set()
    seen_exercises = set()
    total = 0
    for chapter_idx, chapter in enumerate(chapters, 1):
        if not isinstance(chapter, dict):
            raise QuestionBankError(f'第 {chapter_idx} 个章节题库必须是对象。')
        chapter_id = chapter.get('chapterId')
        if not chapter_id:
            raise QuestionBankError(f'第 {chapter_idx} 个章节题库缺少 chapterId。')
        if chapter_id in seen_chapters:
            raise QuestionBankError(f'章节题库重复：{chapter_id}')
        seen_chapters.add(chapter_id)
        if expected_ids and chapter_id not in expected_ids:
            raise QuestionBankError(f'题库章节 {chapter_id} 不在课程目录中。')
        exercises = chapter.get('exercises')
        if not isinstance(exercises, list):
            raise QuestionBankError(f'章节 {chapter_id} 的 exercises 必须是数组。')
        if not exercises:
            raise QuestionBankError(f'章节 {chapter_id} 至少需要 1 道题。')
        for ex_idx, exercise in enumerate(exercises, 1):
            prefix = f'{chapter_id} 第 {ex_idx} 题'
            if not isinstance(exercise, dict):
                raise QuestionBankError(f'{prefix} 必须是对象。')
            missing = [field for field in REQUIRED_EXERCISE_FIELDS if field not in exercise]
            if missing:
                raise QuestionBankError(f'{prefix} 缺少字段：{", ".join(missing)}')
            if not str(exercise.get('id') or '').strip():
                raise QuestionBankError(f'{prefix} id 不能为空。')
            if exercise['id'] in seen_exercises:
                raise QuestionBankError(f'题目 id 重复：{exercise["id"]}')
            seen_exercises.add(exercise['id'])
            if exercise.get('level') not in ('基础', '进阶', '挑战'):
                raise QuestionBankError(f'{prefix} level 必须是 基础/进阶/挑战。')
            if not isinstance(exercise.get('tags'), list) or not exercise.get('tags'):
                raise QuestionBankError(f'{prefix} tags 必须是非空数组。')
            if not isinstance(exercise.get('examples'), list):
                raise QuestionBankError(f'{prefix} examples 必须是数组。')
            if not isinstance(exercise.get('tests'), list):
                raise QuestionBankError(f'{prefix} tests 必须是数组。')
            for field in ('title', 'description', 'taskGoal', 'starter', 'answerCode', 'expectedOutput'):
                if not str(exercise.get(field) or '').strip():
                    raise QuestionBankError(f'{prefix} {field} 不能为空。')
            total += 1
    if expected_ids:
        missing_chapters = sorted(expected_ids - seen_chapters)
        if missing_chapters:
            raise QuestionBankError('题库缺少课程章节：' + ', '.join(missing_chapters[:8]))
    if total <= 0:
        raise QuestionBankError('题库中没有可用题目。')
    return {'ok': True, 'chapters': len(chapters), 'exercises': total}


def import_question_bank(bank, course_data=None):
    stats = validate_question_bank(bank, course_data)
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
    return {**stats, 'id': bank_id, 'title': meta['title']}


def safe_id(value):
    raw = ''.join(ch.lower() if ch.isalnum() else '-' for ch in str(value or '').strip())
    raw = '-'.join(part for part in raw.split('-') if part)
    if not raw:
        raise QuestionBankError('题库 id 不能为空。')
    return raw[:80]
