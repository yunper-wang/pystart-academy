import os
import subprocess
import tempfile
from pathlib import Path


BLOCKED_SNIPPETS = ['__import__', 'subprocess', 'os.system']


def friendly_message(text):
    base = text or '代码运行失败。'
    suggestions = [
        'print() 括号是否完整',
        'if/for/while 后面是否有冒号',
        '缩进是否使用 4 个空格',
        '变量是否先赋值再使用',
    ]
    return '友好错误提示：' + base, suggestions


def run_python(code):
    code = str(code or '')
    if len(code) > 20000:
        msg, suggestions = friendly_message('代码太长，请缩短后再运行。')
        return {'ok': False, 'error': '代码太长，请缩短后再运行。', 'friendlyMessage': msg, 'suggestions': suggestions, 'returncode': None}
    if any(snippet in code for snippet in BLOCKED_SNIPPETS):
        msg, suggestions = friendly_message('为了安全，练习区不允许运行系统命令相关代码。')
        return {'ok': False, 'error': '为了安全，练习区不允许运行系统命令相关代码。', 'friendlyMessage': msg, 'suggestions': suggestions, 'returncode': None}
    try:
        with tempfile.TemporaryDirectory(prefix='pystart_run_') as tmp:
            script = Path(tmp) / 'main.py'
            script.write_text(code, encoding='utf-8')
            proc = subprocess.run(
                ['python3', str(script)],
                cwd=tmp,
                input='',
                text=True,
                capture_output=True,
                timeout=3,
                env={'PYTHONIOENCODING': 'utf-8', 'PATH': os.environ.get('PATH', '')},
            )
        output = (proc.stdout or '') + (proc.stderr or '')
        payload = {
            'ok': proc.returncode == 0,
            'output': output or '程序运行完成，但没有 print() 输出。',
            'returncode': proc.returncode,
        }
        if proc.returncode != 0:
            msg, suggestions = friendly_message(output)
            payload.update({'friendlyMessage': msg, 'suggestions': suggestions})
        return payload
    except subprocess.TimeoutExpired:
        msg, suggestions = friendly_message('程序运行超时，请检查是否有无法结束的循环。')
        return {'ok': False, 'error': '程序运行超时，请检查是否有无法结束的循环。', 'friendlyMessage': msg, 'suggestions': suggestions, 'returncode': None}
    except Exception as exc:
        msg, suggestions = friendly_message('运行服务出错：' + str(exc))
        return {'ok': False, 'error': '运行服务出错：' + str(exc), 'friendlyMessage': msg, 'suggestions': suggestions, 'returncode': None}
