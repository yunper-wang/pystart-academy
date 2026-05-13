import React, {useEffect, useMemo, useState} from 'react';
import {createRoot} from 'react-dom/client';
import './styles.css';

const STORE_KEY = 'pystart_academy_progress_v2';
const DEFAULT_PROGRESS = {completedLessons: [], completedProjects: [], quizResults: {}, reviewItems: [], currentLessonId: null};
const NAV = [
  ['dashboard', '首页', '⌂'],
  ['learn', '学习路径', '◇'],
  ['practice', '练习中心', '✦'],
  ['quiz', '测验中心', '◉'],
  ['projects', '项目实战', '▣'],
  ['report', '学习报告', '✓'],
  ['admin', '后台管理', '⚙'],
];
const downloadJson = (filename, data) => {
  const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
};

const readJsonFile = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => {
    try { resolve(JSON.parse(reader.result)); }
    catch { reject(new Error('导入失败：文件不是有效的 JSON。')); }
  };
  reader.onerror = () => reject(new Error('导入失败：无法读取本地文件。'));
  reader.readAsText(file, 'utf-8');
});



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
      const boot = await api('/api/app/bootstrap');
      const courseData = {stages: boot.stages, chapters: boot.chapters, projects: boot.projects, questionBank: boot.questionBank};
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

  const reloadAppData = async (message) => {
    const boot = await api('/api/app/bootstrap');
    const courseData = {stages: boot.stages, chapters: boot.chapters, projects: boot.projects, questionBank: boot.questionBank};
    setBootstrap(boot); setData(courseData);
    await refreshSummary(progress);
    if (message) toast.push(message);
    return boot;
  };
  const ctx = {data, bootstrap, summary, progress, setProgress: updateProgress, activeLessonId, setActiveLessonId: selectLesson, activeProjectId, setActiveProjectId, navigate, toast, reloadAppData};
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
          {route === 'admin' && <AdminPanel ctx={ctx}/>} 
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
  const status = ctx.bootstrap.systemStatus?.overall || 'loading';
  return <header className="topbar-app"><div><small>当前章节</small><strong>{lesson?.order}. {lesson?.title}</strong></div><div className="top-actions"><span className={`status-pill ${status}`}>系统{statusTextForState(status)}</span><button className="btn primary" onClick={() => ctx.navigate('learn')}>继续学习</button></div></header>;
}

function Dashboard({ctx}) {
  const {summary, data, navigate, activeLessonId, setActiveLessonId} = ctx;
  const next = summary.nextLesson || data.chapters.find(c => c.id === activeLessonId) || data.chapters[0];
  const recentQuiz = Object.entries(ctx.progress.quizResults || {}).slice(-1)[0];
  return <section className="page-grid">
    <div className="hero-panel">
      <span className="kicker">首页</span>
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
  const practices = useMemo(() => ctx.data.chapters.flatMap(ch => (ch.exercises||[]).map((e,i)=>({...e, displayTitle: e.title || `练习 ${i+1}`, lessonId: ch.id, lessonTitle: ch.title, order: ch.order, exerciseIndex:i}))), [ctx.data]);
  const list = practices.filter(p => (filter.lesson==='all'||p.lessonId===filter.lesson) && (filter.level==='all'||p.level===filter.level) && (!filter.q || `${p.title || ''} ${p.description || ''} ${p.text} ${p.hint} ${p.lessonTitle} ${(p.tags||[]).join(' ')}`.toLowerCase().includes(filter.q.toLowerCase())));
  const [active, setActive] = useState(list[0]);
  useEffect(()=>{ if (list.length && !list.includes(active)) setActive(list[0]); }, [filter.q, filter.level, filter.lesson]);
  return <section className="practice-new"><aside className="filter-pane"><h2>练习题库</h2><input className="input" placeholder="搜索练习" value={filter.q} onChange={e=>setFilter({...filter,q:e.target.value})}/><select className="input" value={filter.lesson} onChange={e=>setFilter({...filter,lesson:e.target.value})}><option value="all">全部章节</option>{ctx.data.chapters.map(c=><option key={c.id} value={c.id}>{c.order}. {c.title}</option>)}</select><select className="input" value={filter.level} onChange={e=>setFilter({...filter,level:e.target.value})}><option value="all">全部难度</option><option>基础</option><option>进阶</option><option>挑战</option></select><div className="exercise-list">{list.map(p=><button key={`${p.lessonId}-${p.exerciseIndex}`} className={active===p?'active':''} onClick={()=>setActive(p)}><strong>{p.displayTitle}</strong><small>{p.order}. {p.lessonTitle} · {p.level}</small></button>)}</div></aside><main className="workbench">{active ? <><div className="task-head"><span className="kicker">{active.level} · {active.direction}</span><h1>{active.displayTitle}</h1><p>{active.description || active.text}</p><p><strong>任务目标：</strong>{active.taskGoal}</p><div className="tag-row">{(active.tags||[]).map(t=><span key={t}>{t}</span>)}</div><p className="muted">提示：{active.hint}</p><p className="muted">预期输出：{active.expectedOutput}</p></div><CodeRunner initialCode={active.starter || active.answerCode || ''} answer={active.answerCode} title="练习代码" toast={ctx.toast}/>{active.analysis && <section className="panel"><h2>解题思路</h2><p>{active.analysis}</p></section>}</> : <Empty title="没有匹配练习" desc="换一个筛选条件试试。"/>}</main></section>;
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



const STATE_LABELS = {ok: '正常', warning: '警告', error: '异常', loading: '检测中'};
function statusTextForState(state) { return STATE_LABELS[state] || state || '未知'; }
function formatBytes(bytes=0) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes, idx = 0;
  while (value >= 1024 && idx < units.length - 1) { value /= 1024; idx += 1; }
  return `${value.toFixed(value >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
}
function countQuestionBank(bank) {
  const chapters = Array.isArray(bank?.chapters) ? bank.chapters : [];
  const exercises = chapters.flatMap(ch => Array.isArray(ch.exercises) ? ch.exercises.map(ex => ({...ex, chapterId: ch.chapterId})) : []);
  const levels = exercises.reduce((acc, ex) => ({...acc, [ex.level || '未标注']: (acc[ex.level || '未标注'] || 0) + 1}), {});
  const directions = exercises.reduce((acc, ex) => ({...acc, [ex.direction || '未标注']: (acc[ex.direction || '未标注'] || 0) + 1}), {});
  const tags = {};
  exercises.forEach(ex => (Array.isArray(ex.tags) ? ex.tags : []).forEach(tag => { tags[tag] = (tags[tag] || 0) + 1; }));
  return {chapters: chapters.length, exercises: exercises.length, levels, directions, tags, samples: exercises.slice(0, 6)};
}
function compactPairs(obj={}, limit=8) { return Object.entries(obj).slice(0, limit); }
function Feedback({item}) { if (!item) return null; return <div className={`feedback ${item.type || 'info'}`}>{item.message}</div>; }
function StatRow({label, value}) { return <div className="stat-row"><span>{label}</span><strong>{value}</strong></div>; }
function StatusCard({check}) { return <article className={`status-card ${check.state}`}><span>{statusTextForState(check.state)}</span><strong>{check.label}</strong><p>{check.text}</p></article>; }
function DetailList({items, empty='暂无明细', render}) {
  const list = Array.isArray(items) ? items.slice(0, 8) : [];
  return list.length ? <ul className="detail-list">{list.map((item, idx)=><li key={idx}>{render ? render(item) : JSON.stringify(item)}</li>)}</ul> : <p className="muted">{empty}</p>;
}

function AdminPanel({ctx}) {
  const [busy, setBusy] = useState(false);
  const [system, setSystem] = useState(ctx.bootstrap.systemStatus);
  const [feedback, setFeedback] = useState({type:'info', message:'后台管理已拆分为系统状态和题库管理：状态只负责健康检查，题库管理只负责导入、导出、校验与维护。'});
  const [importFlow, setImportFlow] = useState({file:null, bank:null, parseError:'', validation:null, strategy:'replace', result:null});
  const [exportScope, setExportScope] = useState({mode:'all', direction:'', tag:'', level:'', query:''});
  const bank = ctx.data.questionBank || ctx.bootstrap.questionBank || {};
  const directions = Object.keys(bank.typeDistribution || {});
  const tags = Object.keys(bank.tagDistribution || {});
  const currentSummary = {
    exerciseCount: bank.exerciseCount || ctx.bootstrap.stats.practices,
    chapterCount: bank.chapterCount || ctx.bootstrap.stats.chapters,
    levels: bank.levelDistribution || {},
    directions: bank.typeDistribution || {},
    updatedAt: bank.updatedAt || '暂无记录',
  };
  const parsedSummary = importFlow.bank ? countQuestionBank(importFlow.bank) : null;
  const validation = importFlow.validation;
  const canImport = validation && (importFlow.strategy === 'validOnly' ? validation.validCount > 0 : validation.ok) && !(importFlow.strategy === 'append' && validation.duplicateExistingCount > 0);

  const refreshStatus = async () => {
    setBusy(true);
    try {
      const next = await api('/api/system/status');
      setSystem(next);
      setFeedback({type: next.overall === 'ok' ? 'success' : next.overall === 'warning' ? 'warning' : 'error', message: `系统状态已刷新：${statusTextForState(next.overall)}。`});
    } catch (err) {
      setFeedback({type:'error', message: err.message});
    } finally { setBusy(false); }
  };

  const onSelectImportFile = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setBusy(true);
    setFeedback({type:'info', message:`正在解析 ${file.name}...`});
    setImportFlow({file, bank:null, parseError:'', validation:null, strategy:'replace', result:null});
    try {
      const bankData = await readJsonFile(file);
      const validateRes = await api('/api/question-bank/validate', {questionBank: bankData});
      setImportFlow({file, bank: bankData, parseError:'', validation: validateRes.validation, strategy:'replace', result:null});
      const state = validateRes.validation.ok ? 'success' : 'warning';
      setFeedback({type: state, message:`解析完成：${validateRes.validation.validCount} 道可导入，${validateRes.validation.invalidCount} 道需要处理。请确认策略后再导入。`});
    } catch (err) {
      setImportFlow({file, bank:null, parseError:err.message, validation:null, strategy:'replace', result:null});
      setFeedback({type:'error', message:err.message});
    } finally { setBusy(false); }
  };

  const confirmImport = async () => {
    if (!importFlow.bank || !validation) return setFeedback({type:'error', message:'请先选择并校验题库文件。'});
    if (!canImport) return setFeedback({type:'error', message:'当前校验结果不满足所选导入策略，请查看错误明细或改用“仅导入有效题目”。'});
    const danger = importFlow.strategy === 'replace' ? '覆盖当前题库' : importFlow.strategy === 'append' ? '追加到当前题库' : '仅导入有效且不重复题目';
    if (!window.confirm(`确认${danger}？此操作会更新当前启用题库。`)) return;
    setBusy(true);
    try {
      const result = await api('/api/question-bank/import', {questionBank: importFlow.bank, strategy: importFlow.strategy});
      setImportFlow(flow => ({...flow, result}));
      const boot = await ctx.reloadAppData(`题库导入完成：${result.stats?.exercises || result.questionBank?.exerciseCount || validation.validCount} 道题`);
      setSystem(boot.systemStatus);
      setFeedback({type:'success', message:`导入完成：策略 ${danger}，当前题库 ${result.questionBank?.exerciseCount || result.stats?.exercises} 道题。`});
    } catch (err) {
      setFeedback({type:'error', message:err.message});
      ctx.toast.push(err.message, 'error');
    } finally { setBusy(false); }
  };

  const exportBank = async () => {
    setBusy(true);
    const scope = {};
    if (exportScope.mode === 'direction' && exportScope.direction) scope.directions = [exportScope.direction];
    if (exportScope.mode === 'tag' && exportScope.tag) scope.tags = [exportScope.tag];
    if (exportScope.mode === 'level' && exportScope.level) scope.levels = [exportScope.level];
    if (exportScope.mode === 'filtered' && exportScope.query.trim()) scope.query = exportScope.query.trim();
    try {
      const result = await api('/api/question-bank/export', {scope});
      downloadJson(result.filename || `${bank.id || 'pystart'}-question-bank.json`, result.questionBank);
      setFeedback({type:'success', message:`导出完成：${result.summary.exerciseCount} 道题，文件 ${result.filename}。`});
      ctx.toast.push('题库已导出');
    } catch (err) {
      setFeedback({type:'error', message:err.message});
      ctx.toast.push(err.message, 'error');
    } finally { setBusy(false); }
  };

  return <section className="admin-page">
    <div className="admin-hero"><span className="kicker">Admin console</span><h1>后台管理</h1><p>管理能力集中在这里：系统状态用于健康检查，题库管理用于导入、导出、校验、预览和维护，避免与首页快捷入口重复。</p></div>
    <Feedback item={feedback}/>

    <section className="panel wide admin-section">
      <div className="section-head"><div><span className="kicker">System status</span><h2>系统状态</h2><p>展示真实 API 与题库健康状态，不再使用静态“运行中”文案。</p></div><button className="btn secondary" disabled={busy} onClick={refreshStatus}>刷新状态</button></div>
      <div className="status-grid">{(system?.checks || []).map(check => <StatusCard key={check.key} check={check}/>)}</div>
      <div className="status-summary"><StatRow label="最近检测时间" value={system?.checkedAt || '未检测'}/><StatRow label="最近数据更新时间" value={bank.updatedAt || '暂无记录'}/><StatRow label="当前题库题目数" value={`${currentSummary.exerciseCount} 道`}/><StatRow label="整体状态" value={statusTextForState(system?.overall || 'loading')}/></div>
    </section>

    <section className="panel wide admin-section">
      <div className="section-head"><div><span className="kicker">Question bank</span><h2>题库管理</h2><p>负责题库导入、导出、校验、预览和维护。首页只保留学习概览与快捷入口。</p></div></div>
      <div className="admin-grid two">
        <article className="sub-panel"><h3>当前题库统计</h3><StatRow label="题库名称" value={bank.title || bank.id || '未加载'}/><StatRow label="题目总数" value={`${currentSummary.exerciseCount} 道`}/><StatRow label="章节覆盖" value={`${currentSummary.chapterCount} 章`}/><StatRow label="更新时间" value={currentSummary.updatedAt}/><div className="chip-group">{compactPairs(currentSummary.levels).map(([k,v])=><span key={k}>{k} {v}</span>)}</div></article>
        <article className="sub-panel"><h3>题型/方向分布</h3><div className="chip-group">{compactPairs(currentSummary.directions, 12).map(([k,v])=><span key={k}>{k} {v}</span>)}</div></article>
      </div>
    </section>

    <section className="panel wide admin-section">
      <div className="section-head"><div><span className="kicker">Export</span><h2>题库导出</h2><p>导出前先确认范围与统计，文件名会包含题库名称和日期。</p></div><button className="btn primary" disabled={busy} onClick={exportBank}>{busy?'处理中...':'确认导出'}</button></div>
      <div className="form-grid"><label>导出范围<select className="input" value={exportScope.mode} onChange={e=>setExportScope({...exportScope, mode:e.target.value})}><option value="all">全部题目</option><option value="direction">按题型/方向导出</option><option value="level">按难度导出</option><option value="tag">按分类/标签导出</option><option value="filtered">仅导出当前筛选结果</option></select></label>{exportScope.mode==='direction' && <label>题型/方向<select className="input" value={exportScope.direction} onChange={e=>setExportScope({...exportScope,direction:e.target.value})}><option value="">请选择</option>{directions.map(d=><option key={d}>{d}</option>)}</select></label>}{exportScope.mode==='level' && <label>难度<select className="input" value={exportScope.level} onChange={e=>setExportScope({...exportScope,level:e.target.value})}><option value="">请选择</option><option>基础</option><option>进阶</option><option>挑战</option></select></label>}{exportScope.mode==='tag' && <label>标签<select className="input" value={exportScope.tag} onChange={e=>setExportScope({...exportScope,tag:e.target.value})}><option value="">请选择</option>{tags.map(t=><option key={t}>{t}</option>)}</select></label>}{exportScope.mode==='filtered' && <label>筛选关键词<input className="input" value={exportScope.query} onChange={e=>setExportScope({...exportScope,query:e.target.value})} placeholder="按标题/描述/目标搜索"/></label>}</div>
    </section>

    <section className="panel wide admin-section">
      <div className="section-head"><div><span className="kicker">Import workflow</span><h2>题库导入</h2><p>选择文件 → 解析 → 预览 → 校验 → 选择策略 → 二次确认 → 导入反馈。</p></div><label className={`btn secondary file-btn ${busy?'disabled':''}`}>选择题库 JSON<input type="file" accept="application/json,.json" disabled={busy} onChange={onSelectImportFile}/></label></div>
      <div className="import-steps"><span className={importFlow.file?'done':''}>1 选择文件</span><span className={importFlow.bank||importFlow.parseError?'done':''}>2 解析文件</span><span className={validation?'done':''}>3 校验结果</span><span className={importFlow.result?'done':''}>4 导入完成</span></div>
      {importFlow.file && <div className="file-card"><StatRow label="文件名" value={importFlow.file.name}/><StatRow label="文件大小" value={formatBytes(importFlow.file.size)}/><StatRow label="解析状态" value={importFlow.parseError ? '失败' : importFlow.bank ? '成功' : '等待解析'}/></div>}
      {parsedSummary && <div className="preview-grid"><article className="sub-panel"><h3>导入预览</h3><StatRow label="题库" value={importFlow.bank.title || importFlow.bank.id}/><StatRow label="题目数量" value={`${parsedSummary.exercises} 道`}/><StatRow label="章节数量" value={`${parsedSummary.chapters} 章`}/><div className="chip-group">{compactPairs(parsedSummary.directions, 10).map(([k,v])=><span key={k}>{k} {v}</span>)}</div></article><article className="sub-panel"><h3>样例题目</h3><DetailList items={parsedSummary.samples} render={ex => <><strong>{ex.title || ex.id}</strong><small>{ex.chapterId} · {ex.level} · {ex.direction}</small></>}/></article></div>}
      {validation && <div className={`validation-panel ${validation.ok?'ok':'warning'}`}><h3>校验结果：{validation.ok ? '全部可导入' : '存在需要处理的问题'}</h3><div className="validation-metrics"><StatRow label="可导入题目" value={`${validation.validCount} 道`}/><StatRow label="无效题目" value={`${validation.invalidCount} 道`}/><StatRow label="缺失字段" value={`${validation.missingFieldCount} 个`}/><StatRow label="重复题目" value={`${validation.duplicateCount + validation.duplicateExistingCount} 项`}/><StatRow label="不支持题型" value={`${validation.unsupportedTypeCount} 项`}/><StatRow label="格式错误" value={`${validation.formatErrorCount} 项`}/></div><div className="error-columns"><div><h4>缺失字段</h4><DetailList items={validation.missingFields} render={item => `${item.chapterId} 第 ${item.index} 题缺少：${item.fields.join(', ')}`}/></div><div><h4>重复题目</h4><DetailList items={[...(validation.duplicateItems||[]), ...(validation.duplicateExisting||[])]} render={item => `${item.id || item.chapterId}：${item.reason}`}/></div><div><h4>格式/题型错误</h4><DetailList items={[...(validation.unsupportedTypes||[]), ...(validation.formatErrors||[])]} render={item => `${item.id || item.path || item.chapterId || ''}：${item.reason}`}/></div></div><div className="confirm-row"><label>导入策略<select className="input" value={importFlow.strategy} onChange={e=>setImportFlow({...importFlow, strategy:e.target.value})}><option value="replace">覆盖当前题库</option><option value="append">追加到当前题库</option><option value="validOnly">仅导入有效题目</option></select></label><button className="btn primary" disabled={busy || !canImport} onClick={confirmImport}>{busy?'导入中...':'二次确认并导入'}</button></div>{!canImport && <p className="muted danger">当前策略不可导入：覆盖/追加需要无格式错误；追加不能与当前题库重复；如需跳过错误项请选择“仅导入有效题目”。</p>}</div>}
      {importFlow.result && <div className="feedback success">导入结果摘要：当前题库 {importFlow.result.questionBank?.exerciseCount || importFlow.result.stats?.exercises} 道题，策略 {importFlow.result.stats?.strategy}，数据已刷新。</div>}
    </section>
  </section>;
}

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
