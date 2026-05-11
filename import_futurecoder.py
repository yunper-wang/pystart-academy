import json, re, html
from pathlib import Path

pages_obj = json.loads(Path('/tmp/futurecoder_pages.json').read_text(encoding='utf-8'))
pages = pages_obj['pages']
slugs = pages_obj['pageSlugsList']

js = Path('/tmp/futurecoder_main.js').read_text(encoding='utf-8')
pos = 1868298
start = js.find("'", pos) + 1
i = start
esc = False
while i < len(js):
    ch = js[i]
    if esc:
        esc = False
    elif ch == '\\':
        esc = True
    elif ch == "'":
        break
    i += 1
chapters = json.loads(js[start:i].encode().decode('unicode_escape'))
slug_to_section = {}
for sec in chapters:
    for p in sec['pages']:
        slug_to_section[p['slug']] = sec['title']

def strip_tags(s):
    s = re.sub(r'<pre><code[^>]*>.*?</code></pre>', '[代码见编辑区]', s or '', flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()

def code_from_solution(sol):
    if not sol or not sol.get('tokens'):
        return ''
    return ''.join(sol['tokens'])

section_map = {
    'Shell': 'c02', '字符串基础': 'c04', '变量': 'c03', 'for 循环': 'c08',
    'if 语句': 'c07', '列表': 'c11', '关于字符串的更多内容': 'c10',
    '嵌套循环': 'c23', '函数': 'c13', '布尔运算符': 'c07',
    '井字棋项目': 'c30', '字典': 'c12'
}
page_map = {
    'UsingBreak': 'c09', 'IntroducingElif': 'c07', 'OtherComparisonOperators': 'c06',
    'TheEqualityOperator': 'c06', 'IntroducingFstrings': 'c10',
    'StringMethodsUnderstandingMutation': 'c10', 'EqualsVsIs': 'c20',
    'ModifyingWhileIterating': 'c23', 'TestingFunctions': 'c25',
    'ReturningValuesFromFunctions': 'c14', 'MoreOnReturn': 'c14',
    'DefiningFunctions': 'c13', 'CallingFunctionsWithinFunctions': 'c25',
    'InteractiveProgramsWithInput': 'c05', 'Types': 'c04',
    'IntroducingDictionaries': 'c12', 'UsingDictionaries': 'c24',
    'DictionaryKeysAndValues': 'c24', 'TheFullTicTacToeGame': 'c30',
    'MakingTheBoard': 'c23', 'NestedListAssignment': 'c23',
    'IntroducingNestedLists': 'c23', 'LoopingOverNestedLists': 'c23',
    'IntroducingOr': 'c07', 'IntroducingAnd': 'c07',
    'IntroducingNotPage': 'c07', 'MultiLineExpressions': 'c06',
    'CombiningAndAndOr': 'c07'
}

data_path = Path('/tmp/python-learning-site/data.json')
data = json.loads(data_path.read_text(encoding='utf-8'))
chap_by_id = {c['id']: c for c in data['chapters']}

for c in data['chapters']:
    c['exercises'] = [e for e in c.get('exercises', []) if not str(e.get('source', '')).startswith('futurecoder')]

added = 0
pages_added = 0
for slug in slugs:
    p = pages[slug]
    sec = slug_to_section.get(slug, '')
    cid = page_map.get(slug) or section_map.get(sec, 'c20')
    chapter = chap_by_id.get(cid) or data['chapters'][-1]
    page_added = 0
    for st in p.get('steps', []):
        original_html = st.get('text') or ''
        clean = strip_tags(original_html)
        original_code = code_from_solution(st.get('solution'))
        if not clean and not original_code:
            continue
        title = f"futurecoder《{p['title']}》：{st.get('name', '步骤')}"
        starter = original_code if original_code else '# 本步骤主要是阅读说明，不需要输入代码。\nprint("已阅读本步骤")'
        ex = {
            'level': 'futurecoder',
            'text': title,
            'hint': clean[:220] + ('...' if len(clean) > 220 else ''),
            'answer': starter,
            'starter': starter,
            'expectedOutput': '按 futurecoder 原步骤运行并观察结果；若是说明步骤，输出“已阅读本步骤”。',
            'answerCode': starter,
            'taskGoal': strip_tags(f"{sec} / {p['title']} / {st.get('name', '步骤')}") or title,
            'analysis': clean[:500] + ('...' if len(clean) > 500 else ''),
            'source': 'futurecoder-authorized-copy',
            'futurecoderSection': sec,
            'futurecoderPageSlug': slug,
            'futurecoderPageTitle': p['title'],
            'futurecoderStepName': st.get('name'),
            'futurecoderOriginalHtml': original_html,
            'futurecoderOriginalCode': original_code,
            'futurecoderRequirements': st.get('requirements'),
            'futurecoderSolution': st.get('solution'),
        }
        chapter['exercises'].append(ex)
        added += 1
        page_added += 1
    if page_added:
        pages_added += 1

data['futurecoderImport'] = {
    'sourceUrl': 'https://zh.futurecoder.io/course/#toc',
    'authorization': 'user stated authorization to copy original text and original code in chat',
    'pages': pages_added,
    'stepsImported': added,
    'mode': 'authorized copy; original HTML/code preserved in futurecoderOriginalHtml/futurecoderOriginalCode'
}

data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('imported', added, 'pages', pages_added, 'total', sum(len(c['exercises']) for c in data['chapters']))
for cid in ['c02','c04','c08','c11','c23','c30','c12','c24']:
    c = chap_by_id[cid]
    fc = sum(1 for e in c['exercises'] if e.get('source') == 'futurecoder-authorized-copy')
    print(cid, c['title'], len(c['exercises']), 'futurecoder', fc)
