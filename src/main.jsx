import React, {useEffect, useMemo, useState} from 'react';
import {createRoot} from 'react-dom/client';
import './styles.css';

const STORE_KEY = 'pystart_academy_progress_v2';
const PLAYGROUND_KEY = 'pystart_python_playground_code_v1';
const DEFAULT_PROGRESS = {completedLessons: [], completedProjects: [], quizResults: {}, reviewItems: [], currentLessonId: null};
const NAV = [
  ['dashboard', '驾驶舱', '⌂'],
  ['learn', '学习路径', '◇'],
  ['practice', '练习中心', '✦'],
  ['quiz', '测验中心', '◉'],
  ['projects', '项目实战', '▣'],
  ['report', '学习报告', '✓'],
];
const PLAYGROUND_EXAMPLE = `# 自由练习：统计分数并给出建议
scores = [88, 92, 76, 95]
average = sum(scores) / len(scores)
print("平均分：", average)

if average >= 90:
    print("表现优秀，继续保持！")
else:
    print("已经不错，再练几题会更稳。")`;

function safeJson(raw, fallback) { try { return JSON.parse(raw) || fallback; } catch { return fallback; } }
function normalizeProgress(raw) {
  return {...DEFAULT_PROGRESS, ...(raw || {}), completedLessons: raw?.completedLessons || [], completedProjects: raw?.completedProjects || [], quizResults: raw?.quizResults || {}, reviewItems: raw?.reviewItems || []};
}
async function api(path, payload) {
  const options = payload === undefined ? {cache: 'no-store'} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload || {})};
  const res = await fetch(path, options);
  const data = await res.json();
  if (!res.ok || data.ok === false) throw new Error(data.error || `接口失败：${path}`);
  return data;
}
function stripHtml(html = '') {
  const box = document.createElement('div');
  box.innerHTML = html;
  return box.textContent || box.innerText || '';
}
function pct(done, total) { return total ? Math.round(done * 100 / total) : 0; }
function chapterText(chapter) { return `${chapter.title} ${chapter.goal} ${(chapter.tags || []).join(' ')}`.toLowerCase(); }
function statusText(status) { return status === 'done' ? '已完成' : status === 'learning' ? '学习中' : '未开始'; }

function usePersistentProgress() {
  const [progress, setProgress] = useState(() => normalizeProgress(safeJson(localStorage.getItem(STORE_KEY), DEFAULT_PROGRESS)));
  useEffect(() => localStorage.setItem(STORE_KEY, JSON.stringify(progress)), [progress]);
  return [progress, setProgress];
}
function useToast() {
  const [toasts, setToasts] = useState([]);
  const push = (message, type='success') => {
    const id = Date.now() + Math.random();
    setToasts(list => [...list, {id, message, type}]);
    setTimeout(() => setToasts(list => list.filter(t => t.id !== id)), 2600);
  };
  return {toasts, push};
}

function ToastHost({toasts}) {
  return <div className="toast-host" aria-live="polite">{toasts.map(t => <div className={`toast ${t.type}`} key={t.id}>{t.message}</div>)}</div>;
}
function Loader({text='正在加载...'}) { return <div className="loader"><span></span>{text}</div>; }
function Empty({title, desc, action}) { return <div className="empty-state"><strong>{title}</strong><p>{desc}</p>{action}</div>; }
function ErrorBox({error, onRetry}) { return <div className="error-box"><strong>加载失败</strong><p>{error?.message || String(error)}</p>{onRetry && <button className="btn secondary" onClick={onRetry}>重试</button>}</div>; }
function ProgressBar({value}) { return <div className="progress-track"><div style={{width: `${value || 0}%`}} /></div>; }

function App() {
  const [progress, setProgress] = usePersistentProgress();
  const [data, setData] = useState(null);
  const [bootstrap, setBootstrap] = useState(null);
  const [summary, setSummary] = useState(null);
  const [route, setRoute] = useState(location.hash.replace('#', '') || 'dashboard');
  const [activeLessonId, setActiveLessonId] = useState(progress.currentLessonId);
  const [activeProjectId, setActiveProjectId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const toast = useToast();

  useEffect(() => {
    const onHash = () => setRoute(location.hash.replace('#', '') || 'dashboard');
    addEventListener('hashchange', onHash);
    return () => removeEventListener('hashchange', onHash);
  }, []);
  const refreshSummary = async (nextProgress = progress) => setSummary(await api('/api/progress/summary', {progress: nextProgress}));
  const load = async () => {
    setLoading(true); setError(null);
    try {
      const [boot, courseData] = await Promise.all([api('/api/app/bootstrap'), api('/api/data')]);
      setBootstrap(boot); setData(courseData);
      const firstLesson = progress.currentLessonId || boot.defaultIds.lessonId;
      setActiveLessonId(firstLesson); setActiveProjectId(boot.defaultIds.projectId);
      await refreshSummary({...progress, currentLessonId: firstLesson});
    } catch (err) { setError(err); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const updateProgress = (updater, message) => {
    setProgress(prev => {
      const next = normalizeProgress(typeof updater === 'function' ? updater(prev) : updater);
      if (activeLessonId) next.currentLessonId = activeLessonId;
      refreshSummary(next).catch(err => toast.push(err.message, 'error'));
      if (message) toast.push(message);
      return next;
    });
  };
  const navigate = (next) => { location.hash = next; setRoute(next); };
  const selectLesson = (lessonId, goLearn=true) => {
    setActiveLessonId(lessonId);
    updateProgress(prev => ({...prev, currentLessonId: lessonId}));
    if (goLearn) navigate('learn');
  };

  if (loading) return <Splash />;
  if (error) return <main className="fatal"><ErrorBox error={error} onRetry={load}/></main>;
  if (!data || !bootstrap || !summary) return null;

  const ctx = {data, bootstrap, summary, progress, setProgress: updateProgress, activeLessonId, setActiveLessonId: selectLesson, activeProjectId, setActiveProjectId, navigate, toast};
  return <>
    <div className="app-shell">
      <Sidebar route={route} navigate={navigate}/>
      <div className="workspace">
        <Topbar ctx={ctx}/>
        <main className="content-area">
          {route === 'dashboard' && <Dashboard ctx={ctx}/>} 
          {route === 'learn' && <LessonWorkspace ctx={ctx}/>} 
          {route === 'practice' && <PracticeCenter ctx={ctx}/>} 
          {route === 'quiz' && <QuizCenter ctx={ctx}/>} 
          {route === 'projects' && <ProjectBoard ctx={ctx}/>} 
          {route === 'report' && <Report ctx={ctx}/>} 
        </main>
      </div>
    </div>
    <ToastHost toasts={toast.toasts}/>
  </>;
}
function Splash() { return <main className="splash"><div className="brand-mark">Py</div><h1>PyStart Academy</h1><Loader text="正在装载学习应用..."/></main>; }
function Sidebar({route, navigate}) {
  return <aside className="sidebar"><div className="side-brand"><span>Py</span><div><strong>PyStart</strong><small>Academy</small></div></div><nav>{NAV.map(([id, label, icon]) => <button key={id} className={route === id ? 'active' : ''} onClick={() => navigate(id)}><b>{icon}</b>{label}</button>)}</nav><div className="side-note">零基础 Python 学习工作台</div></aside>;
}
function Topbar({ctx}) {
  const lesson = ctx.data.chapters.find(c => c.id === ctx.activeLessonId) || ctx.data.chapters[0];
  return <header className="topbar-app"><div><small>当前章节</small><strong>{lesson?.order}. {lesson?.title}</strong></div><div className="top-actions"><span className="service-ok">● 后端运行中</span><button className="btn primary" onClick={() => ctx.navigate('learn')}>继续学习</button></div></header>;
}

function Dashboard({ctx}) {
  const {summary, data, navigate, activeLessonId, setActiveLessonId} = ctx;
  const next = summary.nextLesson || data.chapters.find(c => c.id === activeLessonId) || data.chapters[0];
  const recentQuiz = Object.entries(ctx.progress.quizResults || {}).slice(-1)[0];
  return <section className="page-grid">
    <div className="hero-panel">
      <span className="kicker">Learning cockpit</span>
      <h1>欢迎回来，今天继续完成一个小目标。</h1>
      <p>你已经完成 {summary.completedLessonCount}/{summary.totalLessonCount} 个章节、{summary.completedProjectCount}/{summary.totalProjectCount} 个项目。系统建议你下一步学习：{next?.title}。</p>
      <div className="hero-buttons"><button className="btn primary large" onClick={() => {setActiveLessonId(next.id); navigate('learn');}}>继续学习</button><button className="btn secondary large" onClick={() => navigate('practice')}>做一道练习</button></div>
    </div>
    <div className="metric-card accent"><small>总进度</small><strong>{summary.totalProgress}%</strong><ProgressBar value={summary.totalProgress}/></div>
    <QuickCard title="当前课程" text={next?.title} action="打开课程" onClick={() => navigate('learn')}/>
    <QuickCard title="今日练习" text={`${ctx.bootstrap.stats.practices} 道练习可选`} action="进入练习" onClick={() => navigate('practice')}/>
    <QuickCard title="错题复习" text={summary.reviewTitles?.length ? summary.reviewTitles.join('、') : '暂无错题，先完成一次测验吧'} action="去测验" onClick={() => navigate('quiz')}/>
    <section className="panel wide"><h2>阶段地图</h2><div className="stage-map">{summary.stageProgress.map(s => <article key={s.id}><strong>{s.title}</strong><ProgressBar value={s.percent}/><small>{s.done}/{s.total} 完成</small></article>)}</div></section>
    <section className="panel"><h2>最近测验</h2>{recentQuiz ? <p>{recentQuiz[1].date} 得分 {recentQuiz[1].score}</p> : <p>还没有测验记录。</p>}</section>
  </section>;
}
function QuickCard({title, text, action, onClick}) { return <article className="quick-card"><h3>{title}</h3><p>{text}</p><button className="btn secondary" onClick={onClick}>{action}</button></article>; }

function LessonWorkspace({ctx}) {
  const [query, setQuery] = useState('');
  const [stage, setStage] = useState('all');
  const [mobileTab, setMobileTab] = useState('content');
  const chapters = useMemo(() => ctx.data.chapters.filter(c => (stage === 'all' || c.stageId === stage) && (!query || chapterText(c).includes(query.toLowerCase()))), [ctx.data, stage, query]);
  const lesson = ctx.data.chapters.find(c => c.id === ctx.activeLessonId) || ctx.data.chapters[0];
  const lessonIndex = ctx.data.chapters.findIndex(c => c.id === lesson.id);
  const status = ctx.summary.lessonStatusMap[lesson.id] || 'todo';
  const toggleDone = () => ctx.setProgress(prev => ({...prev, completedLessons: prev.completedLessons.includes(lesson.id) ? prev.completedLessons.filter(id => id !== lesson.id) : [...prev.completedLessons, lesson.id]}), status === 'done' ? '已取消完成' : '本章已标记完成');
  return <section className="learn-layout">
    <div className="mobile-tabs"><button onClick={()=>setMobileTab('list')} className={mobileTab==='list'?'active':''}>目录</button><button onClick={()=>setMobileTab('content')} className={mobileTab==='content'?'active':''}>内容</button><button onClick={()=>setMobileTab('actions')} className={mobileTab==='actions'?'active':''}>操作</button></div>
    <aside className={`lesson-nav-pane ${mobileTab==='list'?'show':''}`}><input className="input" placeholder="搜索章节/知识点" value={query} onChange={e=>setQuery(e.target.value)}/><select className="input" value={stage} onChange={e=>setStage(e.target.value)}><option value="all">全部阶段</option>{ctx.data.stages.map(s=><option key={s.id} value={s.id}>{s.title}</option>)}</select><div className="lesson-list-new">{chapters.map(c => <button key={c.id} className={c.id === lesson.id ? 'active' : ''} onClick={() => {ctx.setActiveLessonId(c.id, false); setMobileTab('content');}}><span>{c.order}. {c.title}</span><small>{statusText(ctx.summary.lessonStatusMap[c.id])}</small></button>)}</div></aside>
    <article className={`lesson-reader ${mobileTab==='content'?'show':''}`}><span className="kicker">{stageTitle(ctx.data, lesson.stageId)}</span><h1>{lesson.order}. {lesson.title}</h1><p className="lead">{lesson.goal}</p><div className="tag-row"><span>{lesson.difficulty}</span><span>{lesson.duration}</span>{(lesson.tags||[]).map(t=><span key={t}>{t}</span>)}</div><InfoGrid lesson={lesson}/><h2>示例代码</h2><CodeRunner initialCode={lesson.code} title="课程示例" toast={ctx.toast}/><h2>常见错误</h2><ul className="clean-list">{(lesson.mistakes||[]).map((m,i)=><li key={i}>{m}</li>)}</ul><h2>知识点详解</h2><Knowledge chapter={lesson}/></article>
    <aside className={`action-pane ${mobileTab==='actions'?'show':''}`}><div className="sticky-card"><h2>下一步</h2><p>{statusText(status)} · 建议完成示例运行后进入练习。</p><button className="btn primary block" onClick={() => ctx.navigate('practice')}>做本章练习</button><button className="btn secondary block" onClick={() => ctx.navigate('quiz')}>参加章节测验</button><button className="btn ghost block" onClick={toggleDone}>{status === 'done' ? '取消完成' : '标记完成'}</button><div className="split"><button disabled={lessonIndex<=0} onClick={()=>ctx.setActiveLessonId(ctx.data.chapters[lessonIndex-1].id, false)}>上一章</button><button disabled={lessonIndex>=ctx.data.chapters.length-1} onClick={()=>ctx.setActiveLessonId(ctx.data.chapters[lessonIndex+1].id, false)}>下一章</button></div></div></aside>
  </section>;
}
function stageTitle(data, id) { return data.stages.find(s => s.id === id)?.title || ''; }
function InfoGrid({lesson}) { return <div className="info-grid"><article><h3>生活化理解</h3><p>{lesson.lifeCase}</p></article><article><h3>核心概念</h3><p>{lesson.concept}</p></article><article><h3>语法规则</h3><p>{lesson.syntax}</p></article><article><h3>应用场景</h3><p>{lesson.application}</p></article></div>; }
function Knowledge({chapter}) { const kd = chapter.knowledgeDetail; if (!kd) return <p>本章暂无扩展知识。</p>; return <div className="knowledge-new">{(kd.sections||[]).map(s=><article key={s.title}><h3>{s.title}</h3><p>{s.body}</p></article>)}</div>; }

function PracticeCenter({ctx}) {
  const [filter, setFilter] = useState({q:'', level:'all', lesson: ctx.activeLessonId || 'all'});
  const practices = useMemo(() => ctx.data.chapters.flatMap(ch => (ch.exercises||[]).map((e,i)=>({...e, lessonId: ch.id, lessonTitle: ch.title, order: ch.order, exerciseIndex:i}))), [ctx.data]);
  const list = practices.filter(p => (filter.lesson==='all'||p.lessonId===filter.lesson) && (filter.level==='all'||p.level===filter.level) && (!filter.q || `${p.text} ${p.hint} ${p.lessonTitle}`.toLowerCase().includes(filter.q.toLowerCase())));
  const [active, setActive] = useState(list[0]);
  useEffect(()=>{ if (list.length && !list.includes(active)) setActive(list[0]); }, [filter.q, filter.level, filter.lesson]);
  return <section className="practice-new"><aside className="filter-pane"><h2>练习题库</h2><input className="input" placeholder="搜索练习" value={filter.q} onChange={e=>setFilter({...filter,q:e.target.value})}/><select className="input" value={filter.lesson} onChange={e=>setFilter({...filter,lesson:e.target.value})}><option value="all">全部章节</option>{ctx.data.chapters.map(c=><option key={c.id} value={c.id}>{c.order}. {c.title}</option>)}</select><select className="input" value={filter.level} onChange={e=>setFilter({...filter,level:e.target.value})}><option value="all">全部难度</option><option>基础</option><option>进阶</option><option>挑战</option></select><div className="exercise-list">{list.map(p=><button key={`${p.lessonId}-${p.exerciseIndex}`} className={active===p?'active':''} onClick={()=>setActive(p)}><strong>{p.order}. {p.lessonTitle}</strong><small>{p.level} · 练习 {p.exerciseIndex+1}</small></button>)}</div></aside><main className="workbench">{active ? <><div className="task-head"><span className="kicker">{active.level}</span><h1>{active.lessonTitle}：练习 {active.exerciseIndex+1}</h1><p>{active.text}</p><p className="muted">提示：{active.hint}</p></div><CodeRunner initialCode={active.starter || active.answerCode || ''} answer={active.answerCode} title="练习代码" toast={ctx.toast}/></> : <Empty title="没有匹配练习" desc="换一个筛选条件试试。"/>}</main></section>;
}

function QuizCenter({ctx}) {
  const [lessonId, setLessonId] = useState(ctx.activeLessonId || ctx.bootstrap.defaultIds.lessonId);
  const lesson = ctx.data.chapters.find(c => c.id === lessonId) || ctx.data.chapters[0];
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(()=>{setAnswers({});setResult(null);},[lessonId]);
  const submit = async () => {
    const qs = lesson.quiz || [];
    const missing = qs.findIndex((_,i)=>!String(answers[i]||'').trim());
    if (missing >= 0) return ctx.toast.push(`第 ${missing+1} 题还没有作答`, 'error');
    setBusy(true);
    try { const data = await api('/api/quiz/submit', {lessonId, answers: qs.map((_,i)=>answers[i])}); setResult(data); ctx.setProgress(prev => ({...prev, quizResults:{...prev.quizResults,[lessonId]:{score:data.score,date:new Date().toLocaleDateString()}}, reviewItems: data.reviewLessonId && !prev.reviewItems.includes(data.reviewLessonId) ? [...prev.reviewItems, data.reviewLessonId] : prev.reviewItems}), '测验已提交'); }
    catch(err){ ctx.toast.push(err.message, 'error'); } finally { setBusy(false); }
  };
  return <section className="quiz-runner"><div className="quiz-head"><div><span className="kicker">Quiz runner</span><h1>{lesson.order}. {lesson.title}</h1><p>{(lesson.quiz||[]).length} 道题 · 已答 {Object.keys(answers).filter(k=>answers[k]).length} 道</p></div><select className="input" value={lessonId} onChange={e=>setLessonId(e.target.value)}>{ctx.data.chapters.map(c=><option key={c.id} value={c.id}>{c.order}. {c.title}</option>)}</select></div><div className="quiz-grid">{(lesson.quiz||[]).map((q,i)=><article className="question-card" key={i}><span>{i+1}</span><h3>{q.question}</h3>{q.type==='single' ? (q.options||[]).map(o=><label key={o}><input type="radio" name={`q${i}`} checked={answers[i]===o} onChange={()=>setAnswers({...answers,[i]:o})}/>{o}</label>) : q.type==='judge' ? ['正确','错误'].map(o=><label key={o}><input type="radio" name={`q${i}`} checked={answers[i]===o} onChange={()=>setAnswers({...answers,[i]:o})}/>{o}</label>) : <input className="input" value={answers[i]||''} onChange={e=>setAnswers({...answers,[i]:e.target.value})} placeholder="输入答案"/>}{result?.results?.[i] && <div className={result.results[i].ok?'answer good':'answer bad'}>{result.results[i].ok?'回答正确':'需要复习'}：{result.results[i].explain}</div>}</article>)}</div><div className="bottom-bar"><button className="btn primary" disabled={busy} onClick={submit}>{busy?'提交中...':'提交测验'}</button>{result && <strong className={result.score>=80?'score good':result.score>=60?'score warn':'score bad'}>得分 {result.score}</strong>}</div></section>;
}

function ProjectBoard({ctx}) {
  const current = ctx.data.projects.find(p=>p.id===ctx.activeProjectId) || ctx.data.projects[0];
  const status = ctx.summary.projectStatusMap[current.id] || 'todo';
  const toggle = () => ctx.setProgress(prev => ({...prev, completedProjects: prev.completedProjects.includes(current.id) ? prev.completedProjects.filter(id=>id!==current.id) : [...prev.completedProjects, current.id]}), status==='done'?'已取消项目完成':'项目已完成');
  return <section className="project-board"><aside className="project-list-new">{ctx.data.projects.map(p=><button key={p.id} className={p.id===current.id?'active':''} onClick={()=>ctx.setActiveProjectId(p.id)}><strong>{p.title}</strong><small>{p.difficulty} · {p.time}</small></button>)}</aside><main className="project-reader"><span className="kicker">Project lab</span><h1>{current.title}</h1><p className="lead">{current.goal}</p><div className="tag-row"><span>{current.difficulty}</span><span>{current.time}</span>{(current.tags||[]).map(t=><span key={t}>{t}</span>)}</div><h2>需求说明</h2><div className="info-grid">{(current.requirements||[]).map(r=><article key={r}>{r}</article>)}</div><h2>实现步骤</h2><ol className="steps">{(current.steps||[]).map(s=><li key={s}>{s}</li>)}</ol><CodeRunner initialCode={current.fullCode || current.keyCode || ''} title="项目代码" toast={ctx.toast}/><button className="btn primary" onClick={toggle}>{status==='done'?'取消完成项目':'标记完成项目'}</button></main></section>;
}
function Report({ctx}) { return <section className="report-page"><h1>学习报告</h1><div className="report-grid"><div className="metric-card"><small>总进度</small><strong>{ctx.summary.totalProgress}%</strong><ProgressBar value={ctx.summary.totalProgress}/></div><div className="metric-card"><small>章节</small><strong>{ctx.summary.completedLessonCount}/{ctx.summary.totalLessonCount}</strong></div><div className="metric-card"><small>项目</small><strong>{ctx.summary.completedProjectCount}/{ctx.summary.totalProjectCount}</strong></div></div><section className="panel"><h2>学习成就</h2><div className="achievement-grid">{ctx.summary.achievements.map(a=><span className={a.unlocked?'':'locked'} key={a.title}>{a.title}</span>)}</div></section><section className="panel"><h2>复习建议</h2><p>{ctx.summary.reviewTitles?.length ? ctx.summary.reviewTitles.join('、') : '暂无错题。完成测验后这里会显示需要复习的章节。'}</p></section></section>; }

function CodeRunner({initialCode='', answer='', title='代码运行器', toast}) {
  const [code, setCode] = useState(initialCode || '');
  const [output, setOutput] = useState('点击运行查看结果');
  const [state, setState] = useState('idle');
  useEffect(()=>setCode(initialCode || ''), [initialCode]);
  const run = async () => {
    if (!code.trim()) { setState('error'); setOutput('请先输入代码。'); return; }
    setState('running'); setOutput('正在运行，请稍候...');
    try { const data = await api('/api/run', {code}); setState(data.ok ? 'success' : 'error'); setOutput(data.ok ? (data.output || '程序运行完成，但没有 print() 输出。') : (data.friendlyMessage || data.error || data.output || '运行失败')); if (data.ok) toast.push('代码运行成功'); }
    catch(err){ setState('error'); setOutput(`运行服务连接失败：${err.message}`); }
  };
  return <div className="code-runner"><div className="runner-head"><strong>{title}</strong><div><button className="btn secondary" onClick={()=>navigator.clipboard?.writeText(code).then(()=>toast.push('代码已复制'))}>复制代码</button>{answer && <button className="btn secondary" onClick={()=>{setCode(answer);toast.push('已填入参考答案')}}>填入答案</button>}<button className="btn primary" disabled={state==='running'} onClick={run}>{state==='running'?'运行中...':'运行代码'}</button></div></div><textarea value={code} onChange={e=>setCode(e.target.value)} onKeyDown={e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter')run();}} spellCheck="false"/><pre className={`runner-output ${state}`}>{output}</pre></div>;
}

createRoot(document.getElementById('root')).render(<App />);
