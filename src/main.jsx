import React, {useEffect, useMemo, useRef, useState} from 'react';
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
  const ctx = {data, bootstrap, summary, progress, setProgress: updateProgress, route, navigate, activeLessonId, setActiveLessonId: selectLesson, activeProjectId, setActiveProjectId, navigate, toast, reloadAppData};
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
  const pageInfo = {dashboard:['⌂','首页'],learn:['◇','学习路径'],practice:['✦','练习中心'],quiz:['◉','测验中心'],projects:['▣','项目实战'],report:['✓','学习报告'],admin:['⚙','后台管理']}[ctx.route] || ['⌂','首页'];
  return <header className="topbar-app">
    <div className="topbar-title"><span className="page-icon">{pageInfo[0]}</span><div><span className="page-name">{pageInfo[1]}</span>{ctx.route==='learn'&&lesson&&<small className="breadcrumb">{lesson.order}. {lesson.title}</small>}</div></div>
    <div className="top-actions"><span className={`status-pill ${status}`}>系统{statusTextForState(status)}</span>{ctx.route!=='learn'&&<button className="btn primary" onClick={() => ctx.navigate('learn')}>继续学习</button>}</div>
  </header>;
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
  const [tab, setTab] = useState('dashboard');
  const [authed, setAuthed] = useState(() => sessionStorage.getItem('pystart_admin_authed') === '1');
  const [loginPwd, setLoginPwd] = useState('');
  const [loginErr, setLoginErr] = useState('');
  const [loginBusy, setLoginBusy] = useState(false);
  const tabs = [['dashboard','仪表盄','◈'],['exercises','题目列表','☰'],['editor','编辑器','✎'],['import','导入题库','↑'],['export','导出题库','↓'],['versions','版本管理','↻'],['datasources','自动导入','⟳'],['system','系统状态','●']];
  const doLogin = async () => {
    if (!loginPwd.trim()) return setLoginErr('请输入密码');
    setLoginBusy(true); setLoginErr('');
    try {
      const r = await api('/api/admin/auth', {password: loginPwd});
      if (r.ok) { sessionStorage.setItem('pystart_admin_authed', '1'); setAuthed(true); }
      else setLoginErr('密码错误');
    } catch(e) { setLoginErr(e.message); }
    finally { setLoginBusy(false); }
  };
  if (!authed) return <section className="admin-page"><div className="admin-hero"><span className="kicker">Admin console</span><h1>后台管理</h1><p>题库运营中心：数据可视化、题目管理、导入导出和系统监控。</p></div><div className="login-box"><h2>管理员认证</h2><p>请输入管理员密码访问后台。</p><div className="login-form"><input className="input" type="password" placeholder="管理员密码" value={loginPwd} onChange={e=>setLoginPwd(e.target.value)} onKeyDown={e=>e.key==='Enter'&&doLogin()}/>{loginErr && <p className="login-error">{loginErr}</p>}<button className="btn primary" disabled={loginBusy} onClick={doLogin}>{loginBusy?'验证中...':'登录'}</button></div><p className="muted" style={{marginTop:12}}>默认密码：pystart2026</p></div></section>;
  return <section className="admin-page">
    <div className="admin-hero"><span className="kicker">Admin console</span><h1>后台管理</h1><p>题库运营中心：数据可视化、题目管理、导入导出和系统监控。</p></div>
    <nav className="admin-tabs">{tabs.map(([id,label,icon]) => <button key={id} className={tab===id?'active':''} onClick={()=>setTab(id)}><b>{icon}</b>{label}</button>)}</nav>
    {tab==='dashboard' && <DashboardPanel ctx={ctx}/>}
    {tab==='exercises' && <ExerciseListPanel ctx={ctx}/>}
    {tab==='editor' && <ExerciseEditorPanel ctx={ctx}/>}
    {tab==='import' && <ImportPanel ctx={ctx}/>}
    {tab==='export' && <ExportPanel ctx={ctx}/>}
    {tab==='versions' && <VersionPanel ctx={ctx}/>}
    {tab==='datasources' && <DataSourcesPanel ctx={ctx}/>}
    {tab==='system' && <SystemPanel ctx={ctx}/>}
  </section>;
}

function DashboardPanel({ctx}) {
  const [dash, setDash] = useState(null);
  const [busy, setBusy] = useState(true);
  const [err, setErr] = useState(null);
  useEffect(() => {
    let off = false;
    api('/api/question-bank/dashboard').then(d => { if(!off) setDash(d); }).catch(e => { if(!off) setErr(e); }).finally(() => { if(!off) setBusy(false); });
    return () => { off = true; };
  }, [ctx.data.questionBank?.updatedAt]);
  if (busy) return <Loader text="加载仪表盄数据..."/>;
  if (err) return <ErrorBox error={err}/>;
  if (!dash) return null;
  const levels = dash.levelDistribution || {};
  const dirs = dash.directionDistribution || {};
  const chs = dash.chapterCompleteness || [];
  const tgObj = dash.tagDistribution || {}; const tg = Object.entries(tgObj);
  const maxL = Math.max(...Object.values(levels), 1);
  const maxD = Math.max(...Object.values(dirs), 1);
  const dirEntries = Object.entries(dirs);
  const barClr = n => n==='基础'?'#22c55e':n==='进阶'?'#f59e0b':n==='挑战'?'#ef4444':'var(--accent)';
  return <>
    <div className="metric-row">
      <div className="metric-card-admin"><small>总题目数</small><strong>{dash.totalExercises}</strong></div>
      <div className="metric-card-admin"><small>总章节数</small><strong>{dash.totalChapters}</strong></div>
      <div className="metric-card-admin"><small>完整章节</small><strong>{dash.completeChapters}/{dash.totalChapters}</strong></div>
      <div className="metric-card-admin"><small>标签数量</small><strong>{tg.length}</strong></div>
    </div>
    <div className="admin-grid two">
      <section className="panel"><h2>难度分布</h2><div className="bar-chart">{Object.entries(levels).map(([n,c])=><div className="bar-row" key={n}><span className="bar-label">{n}</span><div className="bar-track"><div className="bar-fill" style={{width:`${c/maxL*100}%`,background:barClr(n)}}/></div><span className="bar-value">{c}</span></div>)}</div></section>
      <section className="panel"><h2>方向/题型分布</h2><div className="bar-chart">{dirEntries.map(([n,c])=><div className="bar-row" key={n}><span className="bar-label">{n}</span><div className="bar-track"><div className="bar-fill" style={{width:`${c/maxD*100}%`,background:'var(--accent)'}}/></div><span className="bar-value">{c}</span></div>)}</div></section>
    </div>
    <section className="panel wide"><h2>章节完整度 <small className="muted">每章 8 题为标准</small></h2><div className="chapter-grid">{chs.map(ch=><div className={`chapter-box ${ch.count>=ch.expected?'complete':ch.count>0?'partial':'empty'}`} key={ch.chapterId} title={`${ch.title}: ${ch.count}/${ch.expected}`}><strong>{ch.count}</strong><small>{ch.order}. {ch.title?.slice(0,6)}</small></div>)}</div></section>
    <section className="panel wide"><h2>热门标签</h2><div className="chip-group">{tg.map(([n,c])=><span key={n}>{n} ({c})</span>)}</div></section>
  </>;
}

function ExerciseListPanel({ctx}) {
  const all = useMemo(()=>ctx.data.chapters.flatMap(ch=>(ch.exercises||[]).map((ex,i)=>({...ex,chapterId:ch.id,chapterTitle:ch.title,chapterOrder:ch.order,exerciseIndex:i}))),[ctx.data]);
  const allDirs = useMemo(()=>[...new Set(all.map(e=>e.direction).filter(Boolean))],[all]);
  const allChs = useMemo(()=>ctx.data.chapters.map(c=>({id:c.id,title:`${c.order}. ${c.title}`})),[ctx.data]);
  const [f, setF] = useState({q:'',level:'all',direction:'all',chapter:'all'});
  const [page, setPage] = useState(0);
  const [expanded, setExpanded] = useState(null);
  const [busy, setBusy] = useState(false);
  const toast = ctx.toast;
  const PS = 20;
  const filtered = useMemo(()=>all.filter(ex=>{
    if(f.level!=='all'&&ex.level!==f.level) return false;
    if(f.direction!=='all'&&ex.direction!==f.direction) return false;
    if(f.chapter!=='all'&&ex.chapterId!==f.chapter) return false;
    if(f.q){const q=f.q.toLowerCase();const h=`${ex.title||''} ${ex.id||''} ${ex.description||''} ${(ex.tags||[]).join(' ')}`.toLowerCase();if(!h.includes(q)) return false;}
    return true;
  }),[all,f]);
  const tp = Math.ceil(filtered.length/PS);
  const items = filtered.slice(page*PS,(page+1)*PS);
  useEffect(()=>setPage(0),[f.q,f.level,f.direction,f.chapter]);
  const toggle = id => setExpanded(p=>p===id?null:id);
  const doQuickDelete = async (ex) => {
    if (!window.confirm(`确认删除题目 ${ex.id}？`)) return;
    setBusy(true);
    try {
      await api('/api/question-bank/exercise/delete', {exerciseId: ex.id});
      await ctx.reloadAppData();
      toast.push(`已删除 ${ex.id}`);
    } catch(e) { toast.push(e.message, 'error'); }
    finally { setBusy(false); }
  };
  const pageBtns = useMemo(()=>{
    if(tp<=7) return Array.from({length:tp},(_,i)=>i);
    const s = Math.max(0,Math.min(page-3,tp-7));
    return Array.from({length:7},(_,i)=>s+i);
  },[tp,page]);
  return <>
    <div className="filter-bar">
      <input className="input" placeholder="搜索题目标题/ID/标签" value={f.q} onChange={e=>setF({...f,q:e.target.value})}/>
      <select className="input" value={f.chapter} onChange={e=>setF({...f,chapter:e.target.value})}><option value="all">全部章节</option>{allChs.map(c=><option key={c.id} value={c.id}>{c.title}</option>)}</select>
      <select className="input" value={f.level} onChange={e=>setF({...f,level:e.target.value})}><option value="all">全部难度</option><option>基础</option><option>进阶</option><option>挑战</option></select>
      <select className="input" value={f.direction} onChange={e=>setF({...f,direction:e.target.value})}><option value="all">全部方向</option>{allDirs.map(d=><option key={d}>{d}</option>)}</select>
      <span className="count">共 {filtered.length} 题</span>
    </div>
    <div style={{overflowX:'auto'}}>
      <table className="exercise-table">
        <thead><tr><th>ID</th><th>标题</th><th>章节</th><th>难度</th><th>方向</th><th>标签</th><th>操作</th></tr></thead>
        <tbody>{items.map(ex=>{const eid=ex.id||`${ex.chapterId}-${ex.exerciseIndex}`;const exp=expanded===eid;return <React.Fragment key={eid}>
          <tr className={exp?'expanded':''} onClick={()=>toggle(eid)}><td><code style={{fontSize:11}}>{ex.id||'-'}</code></td><td>{ex.title||ex.text||'-'}</td><td>{ex.chapterOrder}. {ex.chapterTitle}</td><td><span className={`level-badge ${ex.level||''}`}>{ex.level||'-'}</span></td><td>{ex.direction||'-'}</td><td><div className="tag-chips">{(ex.tags||[]).slice(0,3).map(t=><span className="tag-chip" key={t}>{t}</span>)}{(ex.tags||[]).length>3&&<span className="tag-chip">+{ex.tags.length-3}</span>}</div></td><td className="row-actions" onClick={e=>e.stopPropagation()}><button className="btn-action delete" title="删除" disabled={busy} onClick={()=>doQuickDelete(ex)}>✕</button></td></tr>
          {exp&&<tr className="exercise-detail-row"><td colSpan={7}><div className="exercise-detail"><div className="admin-grid two" style={{gap:16}}><div><h4>题目描述</h4><p>{ex.description||ex.text||'暂无'}</p><h4>任务目标</h4><p>{ex.taskGoal||'暂无'}</p><h4>提示</h4><p>{ex.hint||'暂无'}</p><h4>预期输出</h4><pre>{ex.expectedOutput||'暂无'}</pre></div><div><h4>起始代码</h4><pre>{ex.starter||'暂无'}</pre><h4>参考答案</h4><pre>{ex.answerCode||'暂无'}</pre><h4>解题分析</h4><p>{ex.analysis||'暂无'}</p></div></div></div></td></tr>}
        </React.Fragment>;})}</tbody>
      </table>
    </div>
    {tp>1&&<div className="pagination">
      <button disabled={page<=0} onClick={()=>setPage(0)}>{'«'}</button>
      <button disabled={page<=0} onClick={()=>setPage(page-1)}>{'‹'}</button>
      {pageBtns.map(p=><button key={p} className={p===page?'active':''} onClick={()=>setPage(p)}>{p+1}</button>)}
      <button disabled={page>=tp-1} onClick={()=>setPage(page+1)}>{'›'}</button>
      <button disabled={page>=tp-1} onClick={()=>setPage(tp-1)}>{'»'}</button>
    </div>}
  </>;
}

function ImportPanel({ctx}) {
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [flow, setFlow] = useState({file:null,bank:null,parseError:'',validation:null,strategy:'replace',result:null});
  const parsed = flow.bank ? countQuestionBank(flow.bank) : null;
  const v = flow.validation;
  const canImport = v && (flow.strategy==='validOnly'?v.validCount>0:v.ok) && !(flow.strategy==='append'&&v.duplicateExistingCount>0);
  const onSelect = async (ev) => {
    const file = ev.target.files?.[0]; ev.target.value=''; if(!file) return;
    setBusy(true); setFeedback({type:'info',message:`正在解析 ${file.name}...`});
    setFlow({file,bank:null,parseError:'',validation:null,strategy:'replace',result:null});
    try { const bd = await readJsonFile(file); const vr = await api('/api/question-bank/validate',{questionBank:bd});
      setFlow({file,bank:bd,parseError:'',validation:vr.validation,strategy:'replace',result:null});
      setFeedback({type:vr.validation.ok?'success':'warning',message:`解析完成：${vr.validation.validCount} 道可导入，${vr.validation.invalidCount} 道需处理。`});
    } catch(err) { setFlow({file,bank:null,parseError:err.message,validation:null,strategy:'replace',result:null}); setFeedback({type:'error',message:err.message}); }
    finally { setBusy(false); }
  };
  const doImport = async () => {
    if(!flow.bank||!v) return setFeedback({type:'error',message:'请先选择并校验题库文件。'});
    if(!canImport) return setFeedback({type:'error',message:'当前校验结果不满足所选导入策略。'});
    const label = flow.strategy==='replace'?'覆盖当前题库':flow.strategy==='append'?'追加到当前题库':'仅导入有效题目';
    if(!window.confirm(`确认${label}？`)) return;
    setBusy(true);
    try { const r = await api('/api/question-bank/import',{questionBank:flow.bank,strategy:flow.strategy});
      setFlow(f=>({...f,result:r})); await ctx.reloadAppData('导入完成');
      setFeedback({type:'success',message:`导入完成：${r.questionBank?.exerciseCount||r.stats?.exercises} 道题。`});
    } catch(err) { setFeedback({type:'error',message:err.message}); } finally { setBusy(false); }
  };
  return <>
    <Feedback item={feedback}/>
    <section className="panel wide admin-section">
      <div className="section-head"><div><span className="kicker">Import workflow</span><h2>题库导入</h2><p>选择文件 → 解析 → 预览 → 校验 → 策略 → 确认 → 导入。</p></div><label className={`btn secondary file-btn ${busy?'disabled':''}`}>选择题库 JSON<input type="file" accept="application/json,.json" disabled={busy} onChange={onSelect}/></label></div>
      <div className="import-steps"><span className={flow.file?'done':''}>1 选择文件</span><span className={flow.bank||flow.parseError?'done':''}>2 解析文件</span><span className={v?'done':''}>3 校验结果</span><span className={flow.result?'done':''}>4 导入完成</span></div>
      {flow.file&&<div className="file-card"><StatRow label="文件名" value={flow.file.name}/><StatRow label="文件大小" value={formatBytes(flow.file.size)}/><StatRow label="解析状态" value={flow.parseError?'失败':flow.bank?'成功':'等待解析'}/></div>}
      {parsed&&<div className="preview-grid"><article className="sub-panel"><h3>导入预览</h3><StatRow label="题库" value={flow.bank.title||flow.bank.id}/><StatRow label="题目数量" value={`${parsed.exercises} 道`}/><StatRow label="章节数量" value={`${parsed.chapters} 章`}/><div className="chip-group">{compactPairs(parsed.directions,10).map(([k,val])=><span key={k}>{k} {val}</span>)}</div></article><article className="sub-panel"><h3>样例题目</h3><DetailList items={parsed.samples} render={ex=><><strong>{ex.title||ex.id}</strong><small>{ex.chapterId} · {ex.level} · {ex.direction}</small></>}/></article></div>}
      {v&&<div className={`validation-panel ${v.ok?'ok':'warning'}`}>
        <h3>校验结果：{v.ok?'全部可导入':'存在需要处理的问题'}</h3>
        <div className="validation-metrics"><StatRow label="可导入题目" value={`${v.validCount} 道`}/><StatRow label="无效题目" value={`${v.invalidCount} 道`}/><StatRow label="缺失字段" value={`${v.missingFieldCount} 个`}/><StatRow label="重复题目" value={`${v.duplicateCount+v.duplicateExistingCount} 项`}/><StatRow label="不支持题型" value={`${v.unsupportedTypeCount} 项`}/><StatRow label="格式错误" value={`${v.formatErrorCount} 项`}/></div>
        <div className="error-columns"><div><h4>缺失字段</h4><DetailList items={v.missingFields} render={it=>`${it.chapterId} 第 ${it.index} 题缺少：${it.fields.join(', ')}`}/></div><div><h4>重复题目</h4><DetailList items={[...(v.duplicateItems||[]),...(v.duplicateExisting||[])]} render={it=>`${it.id||it.chapterId}：${it.reason}`}/></div><div><h4>格式/题型错误</h4><DetailList items={[...(v.unsupportedTypes||[]),...(v.formatErrors||[])]} render={it=>`${it.id||it.path||it.chapterId||''}：${it.reason}`}/></div></div>
        <div className="confirm-row"><label>导入策略<select className="input" value={flow.strategy} onChange={e=>setFlow({...flow,strategy:e.target.value})}><option value="replace">覆盖当前题库</option><option value="append">追加到当前题库</option><option value="validOnly">仅导入有效题目</option></select></label><button className="btn primary" disabled={busy||!canImport} onClick={doImport}>{busy?'导入中...':'确认并导入'}</button></div>
        {!canImport&&<p className="muted danger">当前策略不可导入：覆盖/追加需要无格式错误；追加不能与当前题库重复。</p>}
      </div>}
      {flow.result&&<div className="feedback success">导入完成：当前题库 {flow.result.questionBank?.exerciseCount||flow.result.stats?.exercises} 道题。</div>}
    </section>
  </>;
}

function ExportPanel({ctx}) {
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [scope, setScope] = useState({mode:'all',direction:'',tag:'',level:'',query:'',tags:[]});
  const [preview, setPreview] = useState(null);
  const bank = ctx.data.questionBank||ctx.bootstrap.questionBank||{};
  const dirs = Object.keys(bank.typeDistribution||{});
  const tags = Object.keys(bank.tagDistribution||{});
  const buildScope = () => {
    const s = {};
    if(scope.mode==='direction'&&scope.direction) s.directions=[scope.direction];
    if(scope.mode==='tag'&&scope.tag) s.tags=[scope.tag];
    if(scope.mode==='level'&&scope.level) s.levels=[scope.level];
    if(scope.mode==='filtered'&&scope.query.trim()) s.query=scope.query.trim();
    if(scope.mode==='multiTag'&&scope.tags.length) s.tags=scope.tags;
    return s;
  };
  const doPreview = async () => { setBusy(true); try { const r=await api('/api/question-bank/export',{scope:buildScope()}); setPreview(r); setFeedback({type:'info',message:`预览：将导出 ${r.summary.exerciseCount} 道题。`}); } catch(e){setFeedback({type:'error',message:e.message});} finally{setBusy(false);} };
  const doExport = async () => { setBusy(true); try { const r=await api('/api/question-bank/export',{scope:buildScope()}); downloadJson(r.filename||`${bank.id||'pystart'}-question-bank.json`,r.questionBank); setFeedback({type:'success',message:`导出完成：${r.summary.exerciseCount} 道题，文件 ${r.filename}。`}); ctx.toast.push('题库已导出'); } catch(e){setFeedback({type:'error',message:e.message});} finally{setBusy(false);} };
  const toggleTag = t => setScope(p=>({...p,tags:p.tags.includes(t)?p.tags.filter(x=>x!==t):[...p.tags,t]}));
  return <>
    <Feedback item={feedback}/>
    <section className="panel wide admin-section">
      <div className="section-head"><div><span className="kicker">Export</span><h2>题库导出</h2><p>选择范围后预览或直接导出，文件名自动包含日期。</p></div><div style={{display:'flex',gap:8}}><button className="btn secondary" disabled={busy} onClick={doPreview}>{busy?'处理中...':'预览'}</button><button className="btn primary" disabled={busy} onClick={doExport}>{busy?'处理中...':'确认导出'}</button></div></div>
      <div className="form-grid">
        <label>导出范围<select className="input" value={scope.mode} onChange={e=>setScope({...scope,mode:e.target.value})}><option value="all">全部题目</option><option value="direction">按题型/方向</option><option value="level">按难度</option><option value="tag">按标签（单选）</option><option value="multiTag">按标签（多选组合）</option><option value="filtered">按关键词筛选</option></select></label>
        {scope.mode==='direction'&&<label>题型/方向<select className="input" value={scope.direction} onChange={e=>setScope({...scope,direction:e.target.value})}><option value="">请选择</option>{dirs.map(d=><option key={d}>{d}</option>)}</select></label>}
        {scope.mode==='level'&&<label>难度<select className="input" value={scope.level} onChange={e=>setScope({...scope,level:e.target.value})}><option value="">请选择</option><option>基础</option><option>进阶</option><option>挑战</option></select></label>}
        {scope.mode==='tag'&&<label>标签<select className="input" value={scope.tag} onChange={e=>setScope({...scope,tag:e.target.value})}><option value="">请选择</option>{tags.map(t=><option key={t}>{t}</option>)}</select></label>}
        {scope.mode==='filtered'&&<label>关键词<input className="input" value={scope.query} onChange={e=>setScope({...scope,query:e.target.value})} placeholder="按标题/描述/目标搜索"/></label>}
      </div>
      {scope.mode==='multiTag'&&<div style={{marginTop:12}}><p className="muted" style={{marginBottom:8}}>选择标签组合：</p><div className="multi-select">{tags.map(t=><label key={t} className={scope.tags.includes(t)?'selected':''}><input type="checkbox" checked={scope.tags.includes(t)} onChange={()=>toggleTag(t)}/>{t} ({(bank.tagDistribution||{})[t]||0})</label>)}</div></div>}
      {preview&&<div className="export-preview"><strong>预览：</strong> 将导出 {preview.summary.exerciseCount} 道题，{preview.summary.chapterCount} 个章节。{preview.filename&&<span> 文件名：{preview.filename}</span>}</div>}
    </section>
  </>;
}

function SystemPanel({ctx}) {
  const [busy, setBusy] = useState(false);
  const [system, setSystem] = useState(ctx.bootstrap.systemStatus);
  const [feedback, setFeedback] = useState(null);
  const [pwdForm, setPwdForm] = useState({current:'',newPwd:'',confirm:''});
  const [pwdBusy, setPwdBusy] = useState(false);
  const refresh = async () => { setBusy(true); try { const n=await api('/api/system/status'); setSystem(n); setFeedback({type:n.overall==='ok'?'success':'warning',message:`系统状态：${statusTextForState(n.overall)}。`}); } catch(e){setFeedback({type:'error',message:e.message});} finally{setBusy(false);} };
  const changePwd = async () => {
    if (!pwdForm.current) return setFeedback({type:'error',message:'请输入当前密码'});
    if (pwdForm.newPwd.length < 4) return setFeedback({type:'error',message:'新密码长度不能少于 4 位'});
    if (pwdForm.newPwd !== pwdForm.confirm) return setFeedback({type:'error',message:'两次输入的新密码不一致'});
    setPwdBusy(true);
    try {
      const verify = await api('/api/admin/auth', {password: pwdForm.current});
      if (!verify.ok) { setFeedback({type:'error',message:'当前密码错误'}); return; }
      await api('/api/admin/change-password', {newPassword: pwdForm.newPwd});
      setFeedback({type:'success',message:'密码已更新。下次登录请使用新密码。'});
      setPwdForm({current:'',newPwd:'',confirm:''});
    } catch(e) { setFeedback({type:'error',message:e.message}); }
    finally { setPwdBusy(false); }
  };
  return <>
    <Feedback item={feedback}/>
    <section className="panel wide admin-section">
      <div className="section-head"><div><span className="kicker">System status</span><h2>系统状态</h2><p>真实 API 与题库健康状态。</p></div><button className="btn secondary" disabled={busy} onClick={refresh}>刷新状态</button></div>
      <div className="status-grid">{(system?.checks||[]).map(c=><StatusCard key={c.key} check={c}/>)}</div>
      <div className="status-summary"><StatRow label="检测时间" value={system?.checkedAt||'未检测'}/><StatRow label="整体状态" value={statusTextForState(system?.overall||'loading')}/></div>
    </section>
    <section className="panel wide admin-section">
      <div className="section-head"><div><span className="kicker">Security</span><h2>修改密码</h2><p>更改后台管理登录密码。</p></div></div>
      <div className="form-grid" style={{maxWidth:400}}>
        <label>当前密码<input className="input" type="password" value={pwdForm.current} onChange={e=>setPwdForm({...pwdForm,current:e.target.value})}/></label>
        <label>新密码<input className="input" type="password" value={pwdForm.newPwd} onChange={e=>setPwdForm({...pwdForm,newPwd:e.target.value})}/></label>
        <label>确认新密码<input className="input" type="password" value={pwdForm.confirm} onChange={e=>setPwdForm({...pwdForm,confirm:e.target.value})}/></label>
      </div>
      <div style={{marginTop:12}}><button className="btn primary" disabled={pwdBusy} onClick={changePwd}>{pwdBusy?'修改中...':'修改密码'}</button></div>
    </section>
  </>;
}
function ExerciseEditorPanel({ctx}) {
  const [mode, setMode] = useState('create');
  const [searchId, setSearchId] = useState('');
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [form, setForm] = useState(emptyExercise());
  const allChs = useMemo(()=>ctx.data.chapters.map(c=>({id:c.id,title:`${c.order}. ${c.title}`})),[ctx.data]);
  const set = (key, val) => setForm(f=>({...f,[key]:val}));
  const setTags = (val) => set('tags', val.split(',').map(s=>s.trim()).filter(Boolean));
  const loadExercise = async () => {
    if (!searchId.trim()) return setFeedback({type:'error',message:'请输入题目 ID'});
    setBusy(true);
    try {
      const r = await api(`/api/question-bank/exercise?id=${encodeURIComponent(searchId.trim())}`);
      if (r.ok && r.exercise) {
        setForm({...emptyExercise(), ...r.exercise, chapterId: r.chapterId});
        setMode('edit');
        setFeedback({type:'success',message:`已加载题目：${r.exercise.title || r.exercise.id}`});
      } else {
        setFeedback({type:'error',message:r.error || '找不到该题目'});
      }
    } catch(e) { setFeedback({type:'error',message:e.message}); }
    finally { setBusy(false); }
  };
  const doCreate = async () => {
    if (!form.chapterId) return setFeedback({type:'error',message:'请选择所属章节'});
    if (!form.title?.trim()) return setFeedback({type:'error',message:'请输入题目标题'});
    setBusy(true);
    try {
      const exercise = {...form};
      delete exercise.chapterId;
      const r = await api('/api/question-bank/exercise/create', {chapterId: form.chapterId, exercise});
      await ctx.reloadAppData();
      setFeedback({type:'success',message:`创建成功：${r.exerciseId}`});
      setForm(emptyExercise());
    } catch(e) { setFeedback({type:'error',message:e.message}); }
    finally { setBusy(false); }
  };
  const doUpdate = async () => {
    if (!form.id) return setFeedback({type:'error',message:'题目 ID 为空，无法更新'});
    setBusy(true);
    try {
      const updates = {...form};
      delete updates.chapterId;
      const r = await api('/api/question-bank/exercise/update', {exerciseId: form.id, updates});
      await ctx.reloadAppData();
      setFeedback({type:'success',message:`更新成功：${r.exerciseId}`});
    } catch(e) { setFeedback({type:'error',message:e.message}); }
    finally { setBusy(false); }
  };
  const doDelete = async () => {
    if (!form.id) return;
    if (!window.confirm(`确认删除题目 ${form.id}？此操作不可恢复。`)) return;
    setBusy(true);
    try {
      await api('/api/question-bank/exercise/delete', {exerciseId: form.id});
      await ctx.reloadAppData();
      setFeedback({type:'success',message:`已删除：${form.id}`});
      setForm(emptyExercise());
      setMode('create');
    } catch(e) { setFeedback({type:'error',message:e.message}); }
    finally { setBusy(false); }
  };
  return <>
    <Feedback item={feedback}/>
    <section className="panel wide admin-section">
      <div className="section-head"><div><span className="kicker">Exercise editor</span><h2>题目编辑器</h2><p>新建、编辑或删除题库中的练习题目。</p></div><div style={{display:'flex',gap:8,alignItems:'center'}}><button className={mode==='create'?'btn primary':'btn secondary'} onClick={()=>{setMode('create');setForm(emptyExercise());}}>新建模式</button><span className="muted">|</span><input className="input" style={{width:160}} placeholder="输入题目 ID" value={searchId} onChange={e=>setSearchId(e.target.value)} onKeyDown={e=>e.key==='Enter'&&loadExercise()}/><button className="btn secondary" disabled={busy} onClick={loadExercise}>查找</button></div></div>
      <div className="editor-form">
        <div className="form-grid">
          <label>所属章节<select className="input" value={form.chapterId||''} onChange={e=>set('chapterId',e.target.value)} disabled={mode==='edit'}><option value="">请选择</option>{allChs.map(c=><option key={c.id} value={c.id}>{c.title}</option>)}</select></label>
          <label>题目 ID<input className="input" value={form.id||''} onChange={e=>set('id',e.target.value)} disabled={mode==='edit'} placeholder="留空自动生成"/></label>
          <label>题目标题<input className="input" value={form.title||''} onChange={e=>set('title',e.target.value)} placeholder="简明扼要的标题"/></label>
          <label>难度<select className="input" value={form.level||'基础'} onChange={e=>set('level',e.target.value)}><option>基础</option><option>进阶</option><option>挑战</option></select></label>
          <label>方向/题型<input className="input" value={form.direction||''} onChange={e=>set('direction',e.target.value)} placeholder="如：填空题、编程题"/></label>
          <label>标签（逗号分隔）<input className="input" value={(form.tags||[]).join(', ')} onChange={e=>setTags(e.target.value)} placeholder="变量, 基础, 字符串"/></label>
        </div>
        <label>题目描述<textarea className="input editor-textarea" value={form.description||''} onChange={e=>set('description',e.target.value)} placeholder="题目背景描述"/></label>
        <label>题目正文<textarea className="input editor-textarea" value={form.text||''} onChange={e=>set('text',e.target.value)} placeholder="具体题目要求"/></label>
        <label>任务目标<textarea className="input editor-textarea" value={form.taskGoal||''} onChange={e=>set('taskGoal',e.target.value)} placeholder="完成这个题目需要做什么"/></label>
        <div className="editor-two-col">
          <label>起始代码<textarea className="input editor-codearea" value={form.starter||''} onChange={e=>set('starter',e.target.value)} placeholder="# 起始代码\n" spellCheck="false"/></label>
          <label>参考答案<textarea className="input editor-codearea" value={form.answerCode||''} onChange={e=>set('answerCode',e.target.value)} placeholder="# 参考答案\n" spellCheck="false"/></label>
        </div>
        <label>预期输出<textarea className="input editor-textarea" value={form.expectedOutput||''} onChange={e=>set('expectedOutput',e.target.value)} placeholder="程序运行后应输出的内容"/></label>
        <label>文字答案<input className="input" value={form.answer||''} onChange={e=>set('answer',e.target.value)} placeholder="非代码题的文字答案"/></label>
        <label>提示<textarea className="input editor-textarea" value={form.hint||''} onChange={e=>set('hint',e.target.value)} placeholder="给学习者的提示"/></label>
        <label>解题分析<textarea className="input editor-textarea" value={form.analysis||''} onChange={e=>set('analysis',e.target.value)} placeholder="解题思路和关键知识点"/></label>
        <div className="editor-actions">
          {mode==='create' ? <button className="btn primary" disabled={busy} onClick={doCreate}>{busy?'创建中...':'创建题目'}</button> : <>
            <button className="btn primary" disabled={busy} onClick={doUpdate}>{busy?'保存中...':'保存修改'}</button>
            <button className="btn danger" disabled={busy} onClick={doDelete}>{busy?'删除中...':'删除题目'}</button>
            <button className="btn secondary" onClick={()=>{setMode('create');setForm(emptyExercise());}}>取消编辑</button>
          </>}
        </div>
      </div>
    </section>
  </>;
}
function emptyExercise() {
  return {id:'',title:'',level:'基础',direction:'',tags:[],description:'',text:'',taskGoal:'',starter:'',expectedOutput:'',answer:'',answerCode:'',hint:'',analysis:'',examples:[],tests:[],qualityNotes:'',source:'manual'};
}

function VersionPanel({ctx}) {
  const [backups, setBackups] = useState([]);
  const [busy, setBusy] = useState(true);
  const [feedback, setFeedback] = useState(null);
  const load = async () => {
    setBusy(true);
    try { const r = await api('/api/question-bank/versions'); setBackups(r.backups||[]); }
    catch(e) { setFeedback({type:'error',message:e.message}); }
    finally { setBusy(false); }
  };
  useEffect(()=>{ load(); }, []);
  const doRollback = async (filename) => {
    if (!window.confirm(`确认回滚到备份 ${filename}？当前题库将被替换。`)) return;
    setBusy(true);
    try {
      await api('/api/question-bank/rollback', {filename});
      await ctx.reloadAppData();
      setFeedback({type:'success',message:`已回滚到 ${filename}`});
      await load();
    } catch(e) { setFeedback({type:'error',message:e.message}); }
    finally { setBusy(false); }
  };
  return <>
    <Feedback item={feedback}/>
    <section className="panel wide admin-section">
      <div className="section-head"><div><span className="kicker">Version control</span><h2>版本管理</h2><p>每次导入或编辑题库时自动创建备份。可随时回滚到历史版本。</p></div><button className="btn secondary" disabled={busy} onClick={load}>{busy?'加载中...':'刷新列表'}</button></div>
      {busy && backups.length===0 ? <Loader text="加载版本历史..."/> :
        backups.length===0 ? <p className="muted">暂无备份。每次导入或编辑题库时会自动创建备份。</p> :
        <div className="version-list">
          {backups.map(b => <div className="version-row" key={b.filename}>
            <div className="version-info"><strong>{b.filename}</strong><small>{b.createdAt} · {formatBytes(b.size)}</small></div>
            <button className="btn secondary" disabled={busy} onClick={()=>doRollback(b.filename)}>回滚</button>
          </div>)}
        </div>
      }
    </section>
  </>;
}

function DataSourcesPanel({ctx}) {
  const [sources, setSources] = useState([]);
  const [logs, setLogs] = useState([]);
  const [scheduler, setScheduler] = useState({});
  const [busy, setBusy] = useState(true);
  const [feedback, setFeedback] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState({name:'',source_type:'github_api',url:'',schedule:'',enabled:true});
  const [opts, setOpts] = useState({});
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [optsStr, setOptsStr] = useState('{}');
  const [logsExpanded, setLogsExpanded] = useState(false);
  const pollingRef = useRef(null);

  const load = async () => {
    setBusy(true);
    try {
      const [sr, lr, st] = await Promise.all([
        api('/api/data-sources'),
        api('/api/data-sources/logs'),
        api('/api/data-sources/status'),
      ]);
      setSources(sr.sources||[]);
      setLogs(lr.logs||[]);
      setScheduler(st.scheduler||{});
    } catch(e) { setFeedback({type:'error',message:e.message}); }
    finally { setBusy(false); }
  };
  useEffect(()=>{ load(); }, []);
  useEffect(()=>{ return ()=>{ if(pollingRef.current) clearInterval(pollingRef.current); }; }, []);

  const initPresets = async () => {
    setBusy(true);
    try { await api('/api/data-sources/init-presets', {}); await load(); setFeedback({type:'success',message:'预设数据源已初始化。'}); }
    catch(e) { setFeedback({type:'error',message:e.message}); }
    finally { setBusy(false); }
  };

  const startPolling = (sourceId, sourceName) => {
    if(pollingRef.current) clearInterval(pollingRef.current);
    let count = 0;
    pollingRef.current = setInterval(async () => {
      count++;
      try {
        const [lr, sr] = await Promise.all([api('/api/data-sources/logs'), api('/api/data-sources')]);
        setLogs(lr.logs||[]);
        setSources(sr.sources||[]);
        const latest = (lr.logs||[]).find(l => l.source_id === sourceId && l.status !== 'running');
        if(latest || count > 30) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
          if(latest) setFeedback({type:latest.status==='success'?'success':'warning', message:`「${sourceName}」导入完成：成功 ${latest.imported} 条，跳过 ${latest.skipped} 条${latest.errors?.length ? '，'+latest.errors.length+' 个错误' : ''}`});
          else setFeedback({type:'info',message:'导入超时，请手动刷新查看结果。'});
        }
      } catch(e) { /* ignore polling errors */ }
    }, 3000);
  };

  const TYPE_META = {
    github_api: {label:'GitHub API', ph:'https://github.com/用户名/仓库名', fields:[
      {key:'repo',label:'仓库（用户名/仓库名）',ph:'TheAlgorithms/Python'},
      {key:'path',label:'子目录路径',ph:'sorting_algorithms'},
      {key:'branch',label:'分支',ph:'master'},
      {key:'file_pattern',label:'文件匹配',ph:'*.py'},
    ]},
    rss: {label:'RSS/Atom', ph:'https://realpython.com/atom.xml', fields:[
      {key:'max_items',label:'最大条目数',ph:'50'},
    ]},
    web: {label:'网页解析', ph:'https://example.com/tutorials', fields:[
      {key:'section_selector',label:'CSS 选择器',ph:'.tutorial-item'},
      {key:'max_pages',label:'最大页数',ph:'5'},
    ]},
    file: {label:'本地文件', ph:'/path/to/exercises.json', fields:[
      {key:'format',label:'文件格式',ph:'json / csv / md'},
      {key:'encoding',label:'编码',ph:'utf-8'},
    ]},
  };
  const typeMeta = TYPE_META[form.source_type] || TYPE_META.github_api;

  const openCreate = () => {
    setForm({name:'',source_type:'github_api',url:'',schedule:'',enabled:true});
    setOpts({}); setOptsStr('{}'); setEditId(null); setShowAdvanced(false); setShowForm(true);
  };
  const openEdit = (src) => {
    setForm({name:src.name,source_type:src.source_type,url:src.url,schedule:src.schedule||'',enabled:src.enabled});
    const o = src.options||{};
    setOpts(o); setOptsStr(JSON.stringify(o,null,2)); setEditId(src.id); setShowAdvanced(false); setShowForm(true);
  };
  const closeForm = () => { setShowForm(false); setEditId(null); };

  const updateOpt = (key, val) => { const n={...opts,[key]:val}; setOpts(n); setOptsStr(JSON.stringify(n,null,2)); };
  const syncAdvanced = (v) => { setOptsStr(v); try { setOpts(JSON.parse(v)); } catch{} };

  const doSave = async () => {
    if(!form.name.trim()) return setFeedback({type:'error',message:'请输入名称'});
    if(!form.url.trim()) return setFeedback({type:'error',message:'请输入 URL'});
    let finalOpts = opts;
    if(showAdvanced) { try { finalOpts = JSON.parse(optsStr); } catch { return setFeedback({type:'error',message:'高级参数 JSON 格式错误'}); } }
    setBusy(true);
    try {
      if(editId) {
        await api('/api/data-sources/update',{...form,id:editId,options:finalOpts});
        setFeedback({type:'success',message:'数据源已更新。'});
      } else {
        await api('/api/data-sources/create',{...form,options:finalOpts});
        setFeedback({type:'success',message:'数据源已创建。'});
      }
      closeForm(); await load();
    } catch(e) { setFeedback({type:'error',message:e.message}); }
    finally { setBusy(false); }
  };

  const doDelete = async (id, name) => {
    if(!window.confirm(`确认删除数据源「${name}」？`)) return;
    setBusy(true);
    try { await api('/api/data-sources/delete',{id}); await load(); setFeedback({type:'success',message:'已删除。'}); }
    catch(e) { setFeedback({type:'error',message:e.message}); }
    finally { setBusy(false); }
  };

  const doTrigger = async (src) => {
    setBusy(true);
    try {
      await api('/api/data-sources/trigger',{id:src.id});
      setFeedback({type:'info',message:`「${src.name}」导入已启动，自动刷新中...`});
      await load();
      startPolling(src.id, src.name);
    } catch(e) { setFeedback({type:'error',message:e.message}); }
    finally { setBusy(false); }
  };

  const doToggle = async (src) => {
    try { await api('/api/data-sources/update',{id:src.id,enabled:!src.enabled}); await load(); }
    catch(e) { setFeedback({type:'error',message:e.message}); }
  };

  const schedulePreset = (val) => setForm({...form,schedule:val});
  const statusBadge = s => ({success:'badge-ok',partial:'badge-warn',error:'badge-err',running:'badge-run'}[s]||'');
  const lastLogFor = (sid) => logs.find(l=>l.source_id===sid);
  const visLogs = logsExpanded ? logs : logs.slice(0,5);

  return <>
    <Feedback item={feedback}/>
    <section className="panel wide admin-section">
      <div className="section-head">
        <div><span className="kicker">Auto Import</span><h2>数据源管理</h2><p>配置外部数据源，自动抓取并导入 Python 题目到题库。</p></div>
        <div className="head-actions">
          <button className="btn btn-sm secondary" onClick={load}>{busy?'刷新中...':'刷新'}</button>
          <button className="btn btn-sm secondary" onClick={initPresets}>加载预设</button>
          <button className="btn btn-sm primary" onClick={openCreate}>+ 新建数据源</button>
        </div>
      </div>
      <div className="scheduler-bar">
        <span className={`sched-dot ${scheduler.running?'on':'off'}`}/>
        <span>调度器：{scheduler.running?'运行中':'未启动'}</span>
        {pollingRef.current && <span className="source-running pulse" style={{marginLeft:'auto'}}>⏳ 导入轮询中...</span>}
      </div>
      {busy && sources.length===0 ? <Loader text="加载数据源..."/> :
        sources.length===0 ? <p className="muted">暂无数据源。点击「加载预设」初始化推荐数据源，或点击「新建数据源」手动添加。</p> :
        <div className="source-list">
          {sources.map(src => {
            const last = lastLogFor(src.id);
            return <div className={`source-card ${src.running?'running':''}`} key={src.id}>
              <div className="source-head">
                <strong>{src.name}</strong>
                <span className="source-type">{(TYPE_META[src.source_type]||{}).label || src.source_type}</span>
                {src.running && <span className="source-running pulse">● 导入中...</span>}
              </div>
              <div className="source-meta">
                <span className={`source-status-dot ${src.enabled?'enabled':'disabled'}`}/>{src.enabled?'启用':'禁用'}
                {src.schedule && <span className="meta-tag">定时: {src.schedule}</span>}
                {last && <span className="meta-tag">上次导入: {last.status==='success'?'✓':'⚠'} {last.imported||0} 条{last.skipped>0?' / 跳过 '+last.skipped:''}</span>}
                {src.last_sync && <span className="meta-tag">{src.last_sync}</span>}
              </div>
              <div className="source-actions">
                <button className="btn-action-text" disabled={busy||src.running} onClick={()=>doTrigger(src)}>⟳ 同步</button>
                <button className="btn-action-text" onClick={()=>openEdit(src)}>✎ 编辑</button>
                <button className="btn-action-text" onClick={()=>doToggle(src)}>{src.enabled?'⏸ 禁用':'▶ 启用'}</button>
                <button className="btn-action-text delete" onClick={()=>doDelete(src.id,src.name)}>✕ 删除</button>
              </div>
            </div>;
          })}
        </div>
      }
    </section>

    {showForm && <div className="modal-overlay" onClick={closeForm}>
      <div className="modal-content source-form-modal" onClick={e=>e.stopPropagation()}>
        <div className="modal-header">
          <h3>{editId?'编辑数据源':'新建数据源'}</h3>
          <button className="btn-action" onClick={closeForm}>✕</button>
        </div>
        <div className="form-grid admin-form-grid">
          <label>名称<input className="input" value={form.name} onChange={e=>setForm({...form,name:e.target.value})} placeholder="如：TheAlgorithms 排序算法"/></label>
          <label>类型<select className="input" value={form.source_type} onChange={e=>setForm({...form,source_type:e.target.value})}>
            {Object.entries(TYPE_META).map(([k,v])=><option key={k} value={k}>{v.label}</option>)}
          </select></label>
          <label className="form-full">URL<input className="input" value={form.url} onChange={e=>setForm({...form,url:e.target.value})} placeholder={typeMeta.ph}/></label>
          <label className="form-full">定时
            <div className="schedule-row">
              <input className="input" value={form.schedule} onChange={e=>setForm({...form,schedule:e.target.value})} placeholder="@daily / @weekly / 0 2 * * *（留空仅手动）"/>
              <button className={`schedule-chip ${form.schedule===''?'active':''}`} onClick={()=>schedulePreset('')}>手动</button>
              <button className={`schedule-chip ${form.schedule==='@daily'?'active':''}`} onClick={()=>schedulePreset('@daily')}>每天</button>
              <button className={`schedule-chip ${form.schedule==='@weekly'?'active':''}`} onClick={()=>schedulePreset('@weekly')}>每周</button>
            </div>
          </label>
        </div>
        <div className="opts-section">
          <div className="opts-head"><strong>参数配置</strong></div>
          <div className="opts-grid">
            {typeMeta.fields.map(f => <label key={f.key}>{f.label}<input className="input" value={opts[f.key]||''} onChange={e=>updateOpt(f.key,e.target.value)} placeholder={f.ph}/></label>)}
          </div>
          <button className="btn-text-toggle" onClick={()=>setShowAdvanced(!showAdvanced)}>{showAdvanced?'▾ 收起高级参数':'▸ 高级参数（JSON）'}</button>
          {showAdvanced && <textarea className="input editor-codearea" value={optsStr} onChange={e=>syncAdvanced(e.target.value)} spellCheck="false"/>}
        </div>
        <div className="editor-actions">
          <button className="btn primary" disabled={busy} onClick={doSave}>{busy?'保存中...':'保存'}</button>
          <button className="btn secondary" onClick={closeForm}>取消</button>
        </div>
      </div>
    </div>}

    <section className="panel wide admin-section">
      <div className="section-head"><div><span className="kicker">Logs</span><h2>导入日志</h2><p>最近导入记录。</p></div></div>
      {logs.length===0 ? <p className="muted">暂无导入日志。</p> :
        <>
        <div className="log-list">
          {visLogs.map((l,i) => <div className={`log-row ${l.status}`} key={i}>
            <div className="log-head">
              <span className={`log-badge ${statusBadge(l.status)}`}>{({success:'成功',partial:'部分成功',error:'失败',running:'运行中'}[l.status]||l.status)}</span>
              <strong>{l.source_name}</strong>
              <span className="log-time">{l.started_at}</span>
            </div>
            <div className="log-stats">
              <span>抓取: {l.fetched}</span>
              <span>导入: {l.imported}</span>
              <span>跳过: {l.skipped}</span>
            </div>
            {l.errors && l.errors.length > 0 && <div className="log-errors">{l.errors.map((e,j)=><p key={j}>{e}</p>)}</div>}
          </div>)}
        </div>
        {logs.length > 5 && <button className="btn-text-toggle" style={{marginTop:8}} onClick={()=>setLogsExpanded(!logsExpanded)}>{logsExpanded?`▾ 收起，只看最近 5 条`:`▸ 展开全部 ${logs.length} 条记录`}</button>}
        </>
      }
    </section>
  </>;
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
  return <div className={`code-runner${state==='running'?' runner-running':''}`}><div className="runner-head"><strong>{title}</strong><div><button className="btn secondary" onClick={()=>navigator.clipboard?.writeText(code).then(()=>toast.push('代码已复制'))}>复制代码</button>{answer && <button className="btn secondary" onClick={()=>{setCode(answer);toast.push('已填入参考答案')}}>填入答案</button>}<button className="btn primary" disabled={state==='running'} onClick={run}>{state==='running'?'运行中...':'运行代码'}</button></div></div><textarea value={code} onChange={e=>setCode(e.target.value)} onKeyDown={e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter')run();}} spellCheck="false"/><pre className={`runner-output ${state}`}>{output}</pre></div>;
}

createRoot(document.getElementById('root')).render(<App />);