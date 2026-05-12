from . import data_service


def normalize_answer(value):
    return ''.join(str(value or '').split()).lower()


def answer_is_correct(question, answer):
    expected = normalize_answer(question.get('answer'))
    actual = normalize_answer(answer)
    return bool(actual) and expected in actual


def advice_for_score(score):
    if score >= 85:
        return '掌握很好，可以进入下一章或挑战项目。'
    if score >= 60:
        return '基本理解，但建议回看本章常见错误并再做 2 道练习。'
    return '建议重新学习本章概念和示例，重点复习错题。'


def submit(lesson_id, answers, data=None):
    data = data or data_service.load_data()
    chapter = data_service.chapter_by_id(lesson_id, data)
    if not chapter:
        return {'ok': False, 'error': '章节不存在。'}
    quiz = chapter.get('quiz') or []
    answers = answers or []
    results = []
    correct = 0
    for i, question in enumerate(quiz):
        user_answer = answers[i] if i < len(answers) else ''
        ok = answer_is_correct(question, user_answer)
        if ok:
            correct += 1
        results.append({
            'ok': ok,
            'type': question.get('type'),
            'question': question.get('question', ''),
            'userAnswer': user_answer or '未填写',
            'correctAnswer': question.get('answer', ''),
            'explain': question.get('explain', ''),
        })
    score = round(correct / len(quiz) * 100) if quiz else 0
    return {
        'ok': True,
        'lessonId': chapter.get('id'),
        'lessonTitle': chapter.get('title'),
        'score': score,
        'correct': correct,
        'total': len(quiz),
        'results': results,
        'advice': advice_for_score(score),
        'reviewLessonId': None if score >= 85 else chapter.get('id'),
    }
