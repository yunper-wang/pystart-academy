from html import escape as _escape


def esc(value):
    return _escape('' if value is None else str(value), quote=True)


def attrs(**kwargs):
    parts = []
    for key, value in kwargs.items():
        if value is None or value is False:
            continue
        name = key.rstrip('_').replace('_', '-')
        if value is True:
            parts.append(name)
        else:
            parts.append(f'{name}="{esc(value)}"')
    return (' ' + ' '.join(parts)) if parts else ''


def tag(name, content='', **kwargs):
    return f'<{name}{attrs(**kwargs)}>{content}</{name}>'


def badge(text, cls='badge'):
    return f'<span class="{esc(cls)}">{esc(text)}</span>'


def tags(items):
    return ''.join(f'<span class="tag">{esc(item)}</span>' for item in (items or []))


def status_label(status):
    mapping = {
        'done': '已完成',
        'learning': '学习中',
        'todo': '未开始',
    }
    return f'<span class="status {esc(status)}">{mapping.get(status, status)}</span>'


def ul(items, cls='summary-list'):
    return f'<ul class="{esc(cls)}">' + ''.join(f'<li>{esc(x)}</li>' for x in (items or [])) + '</ul>'


def raw_ul(items, cls='summary-list'):
    return f'<ul class="{esc(cls)}">' + ''.join(f'<li>{x}</li>' for x in (items or [])) + '</ul>'


def code_block(code, cls='code-block'):
    return f'<pre class="{esc(cls)}"><code>{esc(code)}</code></pre>'


def inline_output(text):
    return f'<pre class="inline-output">{esc(text)}</pre>'
