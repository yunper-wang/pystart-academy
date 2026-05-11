const STORE_KEY = 'pystart_academy_progress_v2';
const PLAYGROUND_KEY = 'pystart_python_playground_code_v1';
let DATA = null;
let state = loadState();
let currentLessonId = null;
let currentPracticeIndex = 0;
let currentProjectId = null;
let currentGuidedLessonId = null;
let currentGuidedStepIndex = 0;
function loadState(){try{return JSON.parse(localStorage.getItem(STORE_KEY)) || {completedLessons:[], completedProjects:[], quizResults:{}, reviewItems:[], currentLessonId:null};}catch(e){return {completedLessons:[], completedProjects:[], quizResults:{}, reviewItems:[], currentLessonId:null};}}
function saveState(){state.currentLessonId=currentLessonId;localStorage.setItem(STORE_KEY, JSON.stringify(state));}
function $(id){return document.getElementById(id)}
function esc(s){return String(s).replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));}
function lesson(){return DATA.chapters.find(c=>c.id===currentLessonId)||DATA.chapters[0]}
function stageOf(id){return DATA.stages.find(s=>s.id===id)}
function statusFor(c){if(state.completedLessons.includes(c.id))return ['done','已完成']; if(c.id===currentLessonId)return ['learning','学习中']; return ['todo','未开始'];}
function pct(a,b){return b?Math.round(a/b*100):0}
function go(id){location.hash=id; document.querySelectorAll('.nav a').forEach(a=>a.classList.toggle('active',a.dataset.nav===id));}
function setLesson(id,target='courses'){currentLessonId=id;saveState();renderAll();go(target)}
function openPractice(lessonId, exerciseIndex=0){const ps=allPractices();const idx=ps.findIndex(p=>p.lessonId===lessonId&&p.index===exerciseIndex);currentPracticeIndex=idx>=0?idx:0;currentLessonId=lessonId;saveState();renderPractice();go('practice');setTimeout(()=>$('codeEditor')?.focus(),80);}
function toggleLessonDone(id){state.completedLessons=state.completedLessons.includes(id)?state.completedLessons.filter(x=>x!==id):[...state.completedLessons,id];saveState();renderAll();}
function toggleProjectDone(id){state.completedProjects=state.completedProjects.includes(id)?state.completedProjects.filter(x=>x!==id):[...state.completedProjects,id];saveState();renderAll();}
function renderHome(){const total=DATA.chapters.length,done=state.completedLessons.length;$('heroStats').innerHTML=`<div class="stat-chip"><strong>${DATA.stages.length}</strong>学习阶段</div><div class="stat-chip"><strong>${total}</strong>核心章节</div><div class="stat-chip"><strong>${pct(done,total)}%</strong>当前进度</div>`;$('homeStages').innerHTML=DATA.stages.map((s,i)=>{const cs=DATA.chapters.filter(c=>c.stageId===s.id);const d=cs.filter(c=>state.completedLessons.includes(c.id)).length;return `<article class="stage-card"><span class="badge">阶段 ${i+1}</span><h3>${s.title}</h3><p>${s.desc}</p><div class="progress-bar"><div class="progress-fill" style="width:${pct(d,cs.length)}%"></div></div><div class="meta-row"><span class="tag">${cs.length} 章</span><span class="tag">完成 ${d}/${cs.length}</span></div></article>`}).join('');}

function renderKnowledgeDetail(c){
  const kd=c.knowledgeDetail;
  if(!kd)return '';
  return `<section class="knowledge-detail"><div class="knowledge-head"><span class="eyebrow">Knowledge Notes</span><h4>系统知识点详解</h4><p>${esc(kd.inspiredBy||'')}</p></div><div class="knowledge-topic-row">${(kd.sourceTopics||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div><div class="knowledge-grid">${(kd.sections||[]).map(sec=>`<article class="knowledge-card"><h5>${esc(sec.title)}</h5><p>${esc(sec.body)}</p></article>`).join('')}</div><div class="content-grid"><div class="info-panel"><h4>建议学习步骤</h4><ol class="step-list">${(kd.learningSteps||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ol></div><div class="info-panel"><h4>本章易错点</h4><ul class="mistake-list">${(kd.pitfalls||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div></div></section>`;
}


function enhanceCodeCopyButtons(root=document){
  root.querySelectorAll('pre.code-block, pre.inline-output, .futurecoder-html pre').forEach((pre)=>{
    if(pre.dataset.copyReady==='1')return;
    pre.dataset.copyReady='1';
    const wrap=document.createElement('div');
    wrap.className='copy-code-wrap';
    pre.parentNode.insertBefore(wrap,pre);
    wrap.appendChild(pre);
    const btn=document.createElement('button');
    btn.type='button';
    btn.className='copy-code-btn';
    btn.textContent='复制代码';
    btn.setAttribute('aria-label','复制代码块内容');
    btn.onclick=async()=>{
      const text=pre.innerText || pre.textContent || '';
      try{
        if(navigator.clipboard && window.isSecureContext){
          await navigator.clipboard.writeText(text);
        }else{
          const ta=document.createElement('textarea');
          ta.value=text;
          ta.style.position='fixed';
          ta.style.left='-9999px';
          document.body.appendChild(ta);
          ta.focus();
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
        }
        btn.textContent='已复制 ✓';
        btn.classList.add('copied');
        setTimeout(()=>{btn.textContent='复制代码';btn.classList.remove('copied');},1400);
      }catch(err){
        btn.textContent='复制失败';
        setTimeout(()=>btn.textContent='复制代码',1400);
      }
    };
    wrap.appendChild(btn);
  });
}

function renderCourseControls(){$('stageFilter').innerHTML='<option value="all">全部阶段</option>'+DATA.stages.map(s=>`<option value="${s.id}">${s.title}</option>`).join('');$('stageSidebar').innerHTML='<button class="side-btn active" data-stage="all">全部课程</button>'+DATA.stages.map((s,i)=>`<button class="side-btn" data-stage="${s.id}">阶段 ${i+1}<br><small>${s.title.replace(/^阶段.：/,'')}</small></button>`).join('');document.querySelectorAll('.side-btn').forEach(btn=>btn.onclick=()=>{document.querySelectorAll('.side-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');$('stageFilter').value=btn.dataset.stage;renderCourses();});$('stageFilter').onchange=()=>renderCourses();$('courseSearch').oninput=()=>renderCourses();}
function renderCourses(){const filter=$('stageFilter').value,q=$('courseSearch').value.trim().toLowerCase();const blocks=DATA.stages.map((s,i)=>{if(filter!=='all'&&filter!==s.id)return '';let cs=DATA.chapters.filter(c=>c.stageId===s.id);if(q)cs=cs.filter(c=>(c.title+c.goal+c.tags.join(',')).toLowerCase().includes(q));if(!cs.length)return '';const done=cs.filter(c=>state.completedLessons.includes(c.id)).length;return `<section class="course-stage"><div class="course-stage-header"><div><span class="eyebrow">Stage ${i+1}</span><h3>${s.title}</h3><p>${s.desc}</p></div><div class="badge">${done}/${cs.length} 完成</div></div><div class="course-grid">${cs.map(c=>{const st=statusFor(c);return `<article class="course-card ${c.id===currentLessonId?'active':''}" data-lesson="${c.id}"><div class="lesson-title-row"><h4>${c.order}. ${c.title}</h4><span class="status ${st[0]}">${st[1]}</span></div><p>${c.goal}</p><div class="meta-row"><span class="badge">${c.difficulty}</span><span class="tag">${c.duration}</span>${c.tags.map(t=>`<span class="tag">${t}</span>`).join('')}</div></article>`}).join('')}</div></section>`}).join('');$('courseStageList').innerHTML=blocks||'<div class="empty">没有找到匹配课程。</div>';document.querySelectorAll('.course-card').forEach(card=>card.onclick=()=>setLesson(card.dataset.lesson));}
function renderLesson(){const c=lesson(),idx=DATA.chapters.findIndex(x=>x.id===c.id),st=statusFor(c);$('lessonList').innerHTML=DATA.chapters.map(x=>`<button class="lesson-btn ${x.id===c.id?'active':''}" data-lesson="${x.id}">${x.order}. ${x.title}<br><small>${stageOf(x.stageId).title}</small></button>`).join('');document.querySelectorAll('.lesson-btn').forEach(b=>b.onclick=()=>setLesson(b.dataset.lesson));$('lessonDetail').innerHTML=`<div class="lesson-title-row"><div><span class="eyebrow">${stageOf(c.stageId).title}</span><h3>${c.order}. ${c.title}</h3><p>${c.goal}</p></div><span class="status ${st[0]}">${st[1]}</span></div><div class="meta-row"><span class="badge">${c.difficulty}</span><span class="tag">${c.duration}</span>${c.tags.map(t=>`<span class="tag">${t}</span>`).join('')}</div><div class="divider"></div><div class="content-grid"><div class="info-panel"><h4>学习目标</h4><p>${c.goal}</p></div><div class="info-panel"><h4>生活化理解</h4><p>${c.lifeCase}</p></div><div class="info-panel"><h4>核心概念</h4><p>${c.concept}</p></div><div class="info-panel"><h4>语法规则</h4><p>${c.syntax}</p></div></div><h4>示例代码</h4><pre class="code-block"><code>${esc(c.code)}</code></pre><h4>运行结果说明</h4><div class="output-result">${esc(c.output)}</div><div class="content-grid"><div class="info-panel"><h4>应用场景</h4><p>${c.application}</p></div><div class="info-panel"><h4>初学者常见错误</h4><ul class="mistake-list">${c.mistakes.map(m=>`<li>${m}</li>`).join('')}</ul></div></div><h4>课后练习</h4><div class="mini-exercises">${c.exercises.map((e,i)=>`<button class="mini-exercise exercise-link" data-lesson="${c.id}" data-exercise="${i}" type="button"><span class="badge">${e.level}</span><strong> 练习 ${i+1}</strong><p>${e.text}</p><small>提示：${e.hint}</small><em>进入练习 →</em></button>`).join('')}</div><h4>本章总结</h4><ul class="summary-list">${c.summary.map(s=>`<li>${s}</li>`).join('')}</ul><div class="button-row"><button class="ghost-btn" ${idx===0?'disabled':''} id="prevLessonBtn">上一章</button><button class="primary-btn" id="markLessonBtn">${state.completedLessons.includes(c.id)?'取消完成':'标记完成'}</button><button class="soft-btn" id="practiceThisBtn">练习本章</button><button class="soft-btn" id="quizThisBtn">测验本章</button><button class="ghost-btn" ${idx===DATA.chapters.length-1?'disabled':''} id="nextLessonBtn">下一章</button></div>`;$('prevLessonBtn').onclick=()=>idx>0&&setLesson(DATA.chapters[idx-1].id);$('nextLessonBtn').onclick=()=>idx<DATA.chapters.length-1&&setLesson(DATA.chapters[idx+1].id);document.querySelectorAll('.exercise-link').forEach(btn=>btn.onclick=()=>openPractice(btn.dataset.lesson,+btn.dataset.exercise));$('markLessonBtn').onclick=()=>toggleLessonDone(c.id);$('practiceThisBtn').onclick=()=>go('practice');$('quizThisBtn').onclick=()=>{$('quizLessonSelect').value=c.id;renderQuiz();go('quiz');};}

function makePractice(c,e,i){
  const starter = e.starter || e.answerCode || e.answer || '# 请在这里完成练习';
  return {
    ...e,
    lessonId: c.id,
    lessonTitle: c.title,
    index: i,
    taskGoal: e.taskGoal || e.text,
    starter,
    expectedOutput: e.expectedOutput || '请运行参考答案查看输出。',
    answerCode: e.answerCode || starter,
    analysis: e.analysis || e.hint || '本题练习目标、题干、代码和输出均来自同一道练习。'
  };
}
function allPractices(){return DATA.chapters.flatMap(c=>c.exercises.map((e,i)=>makePractice(c,e,i)));}
function renderPractice(){
  const ps=allPractices();
  if(currentPracticeIndex>=ps.length)currentPracticeIndex=0;
  const p=ps[currentPracticeIndex];
  $('practicePicker').innerHTML=ps.map((x,i)=>`<button class="practice-btn ${i===currentPracticeIndex?'active':''}" data-i="${i}">${x.lessonTitle}<br><small>${x.level} · 练习 ${x.index+1}</small></button>`).join('');
  document.querySelectorAll('.practice-btn').forEach(b=>b.onclick=()=>{currentPracticeIndex=+b.dataset.i;renderPractice();});
  const futurecoderBlock=p.source==='futurecoder-authorized-copy'?`<div class="futurecoder-original"><h4>futurecoder 原文</h4><div class="futurecoder-html">${p.futurecoderOriginalHtml||''}</div>${p.futurecoderOriginalCode?`<h4>futurecoder 原题代码</h4><pre class="inline-output">${esc(p.futurecoderOriginalCode)}</pre>`:''}</div>`:'';
  $('practiceTask').innerHTML=`<span class="badge">${p.level}</span><h3>${p.lessonTitle}：练习 ${p.index+1}</h3><p><strong>任务目标：</strong>${p.taskGoal}</p><p><strong>原练习：</strong>${p.text}</p>${futurecoderBlock}<p><strong>预期运行结果：</strong></p><pre class="inline-output">${esc(p.expectedOutput)}</pre>`;
  if($('codeEditor').dataset.practice!==String(currentPracticeIndex)){$('codeEditor').value=p.starter;$('codeEditor').dataset.practice=String(currentPracticeIndex);$('codeOutput').textContent='点击“运行代码”查看结果';}
  $('practiceFeedback').classList.remove('show');
  $('hintBtn').onclick=()=>showFeedback('提示：'+p.hint);
  $('answerBtn').onclick=()=>{$('codeEditor').value=p.answerCode;showFeedback('参考答案已填入。解析：'+p.analysis)};
  $('resetCodeBtn').onclick=()=>{$('codeEditor').value=p.starter;$('codeOutput').textContent='已重置，请继续练习。';showFeedback('已恢复本题初始代码。')};
  $('runCodeBtn').onclick=runCode;
  enhanceCodeCopyButtons($('practiceTask'));
}

function showFeedback(t){$('practiceFeedback').textContent=t;$('practiceFeedback').classList.add('show')}
function pyString(v){if(typeof v==='string')return v;if(Array.isArray(v))return '['+v.map(pyString).join(', ')+']';if(typeof v==='boolean')return v?'True':'False';if(v===null||v===undefined)return 'None';return String(v)}
function splitArgs(src){let out=[],cur='',q=null,depth=0;for(let i=0;i<src.length;i++){const ch=src[i];if(q){cur+=ch;if(ch===q&&src[i-1]!=='\\')q=null;continue;}if(ch==='"'||ch==="'"){q=ch;cur+=ch;continue;}if(ch==='('||ch==='['||ch==='{')depth++;if(ch===')'||ch===']'||ch==='}')depth--;if(ch===','&&depth===0){out.push(cur.trim());cur='';}else cur+=ch;}if(cur.trim())out.push(cur.trim());return out}
function transformExpr(expr,env){
  let js=expr.trim();
  js=js.replace(/\bTrue\b/g,'true').replace(/\bFalse\b/g,'false').replace(/\bNone\b/g,'null');
  js=js.replace(/\band\b/g,'&&').replace(/\bor\b/g,'||').replace(/\bnot\b/g,'!');
  js=js.replace(/\blen\(([^()]+)\)/g,'__len($1)');
  js=js.replace(/([A-Za-z_]\w*)\.upper\(\)/g,'__upper($1)');
  js=js.replace(/([A-Za-z_]\w*)\.lower\(\)/g,'__lower($1)');
  js=js.replace(/(["'][^"']*["'])\.join\(([^()]+)\)/g,'__join($1,$2)');
  js=js.replace(/\bmath\.sqrt\(/g,'__math_sqrt(');
  js=js.replace(/\bmath\.floor\(/g,'__math_floor(');
  js=js.replace(/\bmath\.ceil\(/g,'__math_ceil(');
  js=js.replace(/\bmath\.round\(/g,'__math_round(');
  js=js.replace(/\bmath\.pow\(/g,'__math_pow(');
  js=js.replace(/\bmath\.pi\b/g,'Math.PI');
  return js;
}
function evalExpr(expr,env){
  const names=Object.keys(env), vals=Object.values(env);
  const helpers={
    __len:x=>x?.length ?? 0,
    __upper:x=>String(x).toUpperCase(),
    __lower:x=>String(x).toLowerCase(),
    __join:(sep,arr)=>Array.isArray(arr)?arr.join(sep):'',
    __math_sqrt:x=>Math.sqrt(x),
    __math_floor:x=>Math.floor(x),
    __math_ceil:x=>Math.ceil(x),
    __math_round:x=>Math.round(x),
    __math_pow:(a,b)=>Math.pow(a,b),
    range:(a,b,step=1)=>{let start=b===undefined?0:a,end=b===undefined?a:b,r=[];for(let i=start;step>0?i<end:i>end;i+=step)r.push(i);return r;}
  };
  try{return Function(...names,...Object.keys(helpers),`"use strict";return (${transformExpr(expr,env)});`)(...vals,...Object.values(helpers));}
  catch(e){throw new Error('表达式无法运行：'+expr+'。请检查变量名、括号或运算符。')}
}
function indentOf(line){return (line.match(/^\s*/)||[''])[0].length}
function runLines(lines,start,end,env,out,limit){
  let i=start,steps=0;
  while(i<end){
    if(++steps>limit.count)throw new Error('运行步数过多，请检查 while 循环是否会结束。');
    let raw=lines[i], line=raw.trim();
    if(!line||line.startsWith('#')){i++;continue;}
    if(/^import\s+math\s*$/.test(line)){env.math={};i++;continue;}
    if(/^from\s+math\s+import\s+sqrt\s*$/.test(line)){env.sqrt=Math.sqrt;i++;continue;}
    if(/^print\((.*)\)$/.test(line)){const inner=line.match(/^print\((.*)\)$/)[1];const vals=splitArgs(inner).map(a=>pyString(evalExpr(a,env)));out.push(vals.join(' '));i++;continue;}
    if(/^([A-Za-z_]\w*)\.append\((.*)\)$/.test(line)){const m=line.match(/^([A-Za-z_]\w*)\.append\((.*)\)$/);if(!Array.isArray(env[m[1]]))throw new Error(m[1]+' 不是列表，不能 append。');env[m[1]].push(evalExpr(m[2],env));i++;continue;}
    if(/^for\s+([A-Za-z_]\w*)\s+in\s+range\((.*)\):$/.test(line)){const m=line.match(/^for\s+([A-Za-z_]\w*)\s+in\s+range\((.*)\):$/);let j=i+1,base=indentOf(lines[i+1]||'');while(j<end&&indentOf(lines[j])>=base&&lines[j].trim())j++;const args=splitArgs(m[2]).map(a=>evalExpr(a,env));const arr=evalExpr(`range(${args.join(',')})`,env);for(const val of arr){env[m[1]]=val;runLines(lines,i+1,j,env,out,limit)}i=j;continue;}
    if(/^for\s+([A-Za-z_]\w*)\s+in\s+([A-Za-z_]\w*)\s*:$/.test(line)){const m=line.match(/^for\s+([A-Za-z_]\w*)\s+in\s+([A-Za-z_]\w*)\s*:/);let j=i+1,base=indentOf(lines[i+1]||'');while(j<end&&indentOf(lines[j])>=base&&lines[j].trim())j++;for(const val of (env[m[2]]||[])){env[m[1]]=val;runLines(lines,i+1,j,env,out,limit)}i=j;continue;}
    if(/^if\s+(.+):$/.test(line)){const cond=line.match(/^if\s+(.+):$/)[1];let thenStart=i+1,base=indentOf(lines[thenStart]||''),j=thenStart;while(j<end&&indentOf(lines[j])>=base&&lines[j].trim())j++;let elseStart=-1,elseEnd=j;if(j<end&&lines[j].trim()==='else:'){elseStart=j+1;let eb=indentOf(lines[elseStart]||'');elseEnd=elseStart;while(elseEnd<end&&indentOf(lines[elseEnd])>=eb&&lines[elseEnd].trim())elseEnd++;}if(evalExpr(cond,env))runLines(lines,thenStart,j,env,out,limit);else if(elseStart>0)runLines(lines,elseStart,elseEnd,env,out,limit);i=elseEnd;continue;}
    if(/^while\s+(.+):$/.test(line)){const cond=line.match(/^while\s+(.+):$/)[1];let j=i+1,base=indentOf(lines[j]||'');while(j<end&&indentOf(lines[j])>=base&&lines[j].trim())j++;while(evalExpr(cond,env)){runLines(lines,i+1,j,env,out,limit);if(++steps>limit.count)throw new Error('while 循环运行太久，请确认条件会变为 False。')}i=j;continue;}
    if(/^([A-Za-z_]\w*)\s*=\s*(.+)$/.test(line)){const m=line.match(/^([A-Za-z_]\w*)\s*=\s*(.+)$/);env[m[1]]=evalExpr(m[2],env);i++;continue;}
    if(/^import\s+/.test(line))throw new Error('当前浏览器练习器只支持 import math。其他模块请在本地 Python 中运行。');
    throw new Error('暂不支持这行语法：'+line);
  }
}
function simulatePython(code){const env={},out=[];const lines=code.replace(/\t/g,'    ').split(/\n/);runLines(lines,0,lines.length,env,out,{count:2000});return out.join('\n')||'程序运行完成，但没有 print() 输出。'}

function friendlyRunError(data){return '友好错误提示：'+(data.error || data.output || '代码运行失败。')+'\n\n你可以检查：\n1. print() 括号是否完整；\n2. if/for/while 后面是否有冒号；\n3. 缩进是否使用 4 个空格；\n4. 变量是否先赋值再使用。'}
async function runPythonCode(code, outputId, fallback=true){
  $(outputId).textContent='正在运行...';
  try{
    const res=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code})});
    const data=await res.json();
    if(data.ok){$(outputId).textContent=data.output || '程序运行完成，但没有 print() 输出。';return {ok:true,data};}
    $(outputId).textContent=friendlyRunError(data);return {ok:false,data};
  }catch(err){
    if(fallback){
      try{$(outputId).textContent=simulatePython(code);return {ok:true,fallback:true};}
      catch(inner){$(outputId).textContent=friendlyRunError({error:inner.message});return {ok:false,error:inner};}
    }
    $(outputId).textContent='无法连接本地 Python 运行服务。请确认使用 python3 server.py 启动，并通过 8766 后端地址访问。';
    return {ok:false,error:err};
  }
}

async function runCode(){
  const result=await runPythonCode($('codeEditor').value,'codeOutput',true);
  if(result.fallback)showFeedback('提示：当前没有连接本地 Python 运行服务，已使用浏览器基础模拟器运行。复杂语法请启动 server.py 后再试。');
}




function guidedStepsFor(c){
  const ex=(c.exercises||[]).slice(0,3);
  const conceptCode=c.code || 'print("开始学习 Python")';
  return [
    {kind:'read',title:'先观察：这一章要解决什么问题？',goal:c.goal,explain:`${c.lifeCase || c.concept} 先不要急着背语法，先运行一小段代码，观察屏幕输出和变量变化。`,starter:conceptCode,expected:c.output || '运行示例代码，观察输出。',hint:'先点击运行，看看代码做了什么；再试着改一处字符串或数字。',answer:conceptCode},
    ...ex.map((e,i)=>({kind:'practice',title:`动手 ${i+1}：${e.text}`,goal:e.taskGoal || e.text,explain:e.analysis || e.hint || '修改代码并运行，直到输出接近预期结果。',starter:e.starter || e.answerCode || e.answer || '# 在这里写代码',expected:e.expectedOutput || '运行后观察输出。',hint:e.hint || '先看变量，再看 print 输出。',answer:e.answerCode || e.starter || e.answer || '# 暂无参考答案'})),
    {kind:'reflect',title:'复盘：我能解释这段代码吗？',goal:'用自己的话总结本章核心点。',explain:'futurecoder 类网站很强调边做边想。最后一步不是新语法，而是确认你能解释代码为什么这样写。',starter:`# 复盘本章：${c.title}\nprint("我学会了：${(c.summary||[])[0] || c.goal}")`,expected:'输出一句自己的学习总结。',hint:'把 print 里的文字改成你自己的总结。',answer:`print("我学会了 ${c.title} 的核心用法，并能写一个小例子。")`}
  ];
}
function guidedLessons(){return DATA.chapters.slice(0, Math.min(DATA.chapters.length, 30));}
function setGuidedLesson(id,step=0){currentGuidedLessonId=id;currentLessonId=id;currentGuidedStepIndex=step;saveState();renderLesson();renderGuided();go('courses');setTimeout(()=>$('guidedEditor')?.focus(),60)}
function renderGuided(){
  if(!$('guidedToc'))return;
  const lessons=guidedLessons();
  const current=DATA.chapters.find(c=>c.id===currentGuidedLessonId)||lesson()||lessons[0];
  currentGuidedLessonId=current.id;
  const steps=guidedStepsFor(current);
  if(currentGuidedStepIndex>=steps.length)currentGuidedStepIndex=0;
  const step=steps[currentGuidedStepIndex];
  $('guidedToc').innerHTML=lessons.map(c=>{
    const done=state.completedLessons.includes(c.id);
    return `<button class="guided-toc-btn ${c.id===current.id?'active':''}" data-guided="${c.id}"><span>${c.order}. ${c.title}</span><small>${done?'已完成':'未完成'} · ${stageOf(c.stageId).title}</small></button>`
  }).join('');
  document.querySelectorAll('.guided-toc-btn').forEach(b=>b.onclick=()=>setGuidedLesson(b.dataset.guided,0));
  $('guidedHeader').innerHTML=`<div><span class="eyebrow">Step-by-step Course</span><h3>${current.order}. ${current.title}</h3><p>${current.goal}</p></div><button class="soft-btn" id="guidedOpenLessonBtn">查看完整课程详情</button>`;
  $('guidedOpenLessonBtn').onclick=()=>setLesson(current.id,'courses');
  $('guidedStepper').innerHTML=steps.map((st,i)=>`<button class="step-pill ${i===currentGuidedStepIndex?'active':''}" data-step="${i}">${i+1}. ${st.kind==='read'?'观察':st.kind==='practice'?'练习':'复盘'}</button>`).join('');
  document.querySelectorAll('.step-pill').forEach(b=>b.onclick=()=>{currentGuidedStepIndex=+b.dataset.step;renderGuided();});
  $('guidedContent').innerHTML=`<span class="badge">${step.kind==='read'?'观察代码':step.kind==='practice'?'动手练习':'复盘总结'}</span><h3>${step.title}</h3><p><strong>目标：</strong>${step.goal}</p><p>${step.explain}</p><p><strong>期待结果：</strong></p><pre class="inline-output">${esc(step.expected)}</pre>`;
  if($('guidedEditor').dataset.lesson!==current.id || $('guidedEditor').dataset.step!==String(currentGuidedStepIndex)){
    $('guidedEditor').value=step.starter;
    $('guidedEditor').dataset.lesson=current.id;
    $('guidedEditor').dataset.step=String(currentGuidedStepIndex);
    $('guidedOutput').textContent='点击“运行并检查”查看结果。';
  }
  $('guidedFeedback').classList.remove('show');
  $('runGuidedBtn').onclick=async()=>{
    const result=await runPythonCode($('guidedEditor').value,'guidedOutput',false);
    if(result.ok){
      showGuidedFeedback('运行成功。你可以继续修改代码观察变化，或进入下一步。');
      if(currentGuidedStepIndex<steps.length-1){currentGuidedStepIndex++;setTimeout(()=>renderGuided(),650)}
    }
  };
  $('guidedHintBtn').onclick=()=>showGuidedFeedback('提示：'+step.hint);
  $('guidedAnswerBtn').onclick=()=>{$('guidedEditor').value=step.answer;showGuidedFeedback('已填入参考答案。建议先运行，再对照理解每一行。')};
  $('guidedResetBtn').onclick=()=>{$('guidedEditor').value=step.starter;$('guidedOutput').textContent='已重置本步骤代码。';showGuidedFeedback('已恢复本步骤初始代码。')};
  enhanceCodeCopyButtons($('guidedContent'));
}
function showGuidedFeedback(t){const box=$('guidedFeedback');if(!box)return;box.textContent=t;box.classList.add('show')}

function renderQuiz(){const sel=$('quizLessonSelect');if(!sel.options.length)sel.innerHTML=DATA.chapters.map(c=>`<option value="${c.id}">${c.order}. ${c.title}</option>`).join('');if(!sel.value)sel.value=currentLessonId;const c=DATA.chapters.find(x=>x.id===sel.value)||lesson();$('quizList').innerHTML=c.quiz.map((q,i)=>`<article class="quiz-card" data-i="${i}"><span class="badge">${q.type}</span><h4>${i+1}. ${q.question.replace(/\n/g,'<br>')}</h4>${renderAnswerInput(q,i)}<div class="quiz-result" id="qr-${i}" style="display:none"></div></article>`).join('');sel.onchange=renderQuiz;$('submitQuizBtn').onclick=submitQuiz;$('quizAdvice').classList.remove('show');}
function renderAnswerInput(q,i){if(q.type==='single')return q.options.map(o=>`<label class="option"><input type="radio" name="q${i}" value="${esc(o)}"> ${o}</label>`).join('');if(q.type==='judge')return ['正确','错误'].map(o=>`<label class="option"><input type="radio" name="q${i}" value="${o}"> ${o}</label>`).join('');return `<input class="text-answer" id="qa-${i}" placeholder="请输入你的答案">`;}
function getAns(q,i){if(q.type==='single'||q.type==='judge'){const el=document.querySelector(`input[name="q${i}"]:checked`);return el?el.value:''}return($('qa-'+i)?.value||'').trim();}
function submitQuiz(){const c=DATA.chapters.find(x=>x.id===$('quizLessonSelect').value);let score=0;c.quiz.forEach((q,i)=>{const ans=getAns(q,i);const ok=ans&&ans.replace(/\s/g,'').includes(String(q.answer).replace(/\s/g,''));if(ok)score++;const box=$('qr-'+i);box.style.display='block';box.innerHTML=`<strong>${ok?'回答正确 ✅':'需要复习 ❗'}</strong><p>你的答案：${ans||'未填写'}</p><p>正确答案：${esc(q.answer)}</p><p>解析：${q.explain}</p>`;if(!ok&&!state.reviewItems.includes(c.id))state.reviewItems.push(c.id);});const final=Math.round(score/c.quiz.length*100);state.quizResults[c.id]={score:final,date:new Date().toLocaleDateString()};saveState();const advice=final>=85?'掌握很好，可以进入下一章或挑战项目。':final>=60?'基本理解，但建议回看本章常见错误并再做 2 道练习。':'建议重新学习本章概念和示例，重点复习错题。';$('quizAdvice').className='quiz-advice show';$('quizAdvice').innerHTML=`<strong>得分：${final} 分</strong><p>${advice}</p><p>推荐复习章节：${state.reviewItems.slice(-3).map(id=>DATA.chapters.find(c=>c.id===id)?.title).filter(Boolean).join('、')||'暂无'}</p>`;renderProgress();}
function renderProjects(){
  $('projectGrid').innerHTML=DATA.projects.map(p=>`<article class="project-card ${p.id===currentProjectId?'active':''}" data-project="${p.id}"><h3>${p.title}</h3><p>${p.goal}</p><div class="meta-row"><span class="badge">${p.difficulty}</span><span class="tag">${p.time}</span>${p.tags.slice(0,4).map(t=>`<span class="tag">${t}</span>`).join('')}</div><div class="meta-row"><span class="status ${state.completedProjects.includes(p.id)?'done':'todo'}">${state.completedProjects.includes(p.id)?'已完成':'未完成'}</span></div></article>`).join('');
  document.querySelectorAll('.project-card').forEach(card=>card.onclick=()=>{currentProjectId=card.dataset.project;renderProjects();});
  const p=DATA.projects.find(x=>x.id===currentProjectId)||DATA.projects[0];
  $('projectDetail').innerHTML=`<span class="eyebrow">Project Lab</span><h3>${p.title}</h3><p class="project-goal">${p.goal}</p><div class="meta-row"><span class="badge">${p.difficulty}</span><span class="tag">${p.time}</span>${p.tags.map(t=>`<span class="tag">${t}</span>`).join('')}</div>
  <div class="project-section"><h4>项目目标</h4><p>${p.goal}</p></div>
  <div class="project-section"><h4>需求说明</h4><div class="requirements">${p.requirements.map(r=>`<div class="info-panel">${r}</div>`).join('')}</div></div>
  <div class="project-section"><h4>实现步骤</h4><ol class="step-list">${p.steps.map(s=>`<li>${s}</li>`).join('')}</ol></div>
  <div class="project-section"><h4>核心代码</h4><pre class="code-block"><code>${esc(p.keyCode)}</code></pre></div>
  <div class="project-section"><h4>完整可运行代码</h4><pre class="code-block"><code>${esc(p.fullCode)}</code></pre></div>
  <div class="project-section"><h4>测试示例</h4><ul class="summary-list">${p.examples.map(e=>`<li>${e}</li>`).join('')}</ul></div>
  <div class="project-section"><h4>常见错误</h4><ul class="mistake-list">${p.mistakes.map(e=>`<li>${e}</li>`).join('')}</ul></div>
  <div class="project-section"><h4>拓展方向</h4><ul class="summary-list">${p.extend.map(e=>`<li>${e}</li>`).join('')}</ul></div>
  <button class="primary-btn" id="markProjectBtn">${state.completedProjects.includes(p.id)?'取消完成项目':'标记完成项目'}</button>`;
  $('markProjectBtn').onclick=()=>toggleProjectDone(p.id);
}
function renderProgress(){const done=state.completedLessons.length,total=DATA.chapters.length,pdone=state.completedProjects.length,next=DATA.chapters.find(c=>!state.completedLessons.includes(c.id));$('progressDashboard').innerHTML=`<div class="progress-overview"><div class="progress-card"><h3>总进度</h3><strong>${pct(done,total)}%</strong><div class="progress-bar"><div class="progress-fill" style="width:${pct(done,total)}%"></div></div></div><div class="progress-card"><h3>已完成章节</h3><strong>${done}/${total}</strong></div><div class="progress-card"><h3>已完成项目</h3><strong>${pdone}/${DATA.projects.length}</strong></div><div class="progress-card"><h3>推荐下一步</h3><p>${next?next.title:'进入更多项目实战'}</p></div></div><div class="progress-card"><h3>阶段进度</h3><div class="stage-progress-grid">${DATA.stages.map(s=>{const cs=DATA.chapters.filter(c=>c.stageId===s.id),d=cs.filter(c=>state.completedLessons.includes(c.id)).length;return `<div><strong>${s.title}</strong><div class="progress-bar"><div class="progress-fill" style="width:${pct(d,cs.length)}%"></div></div><small>${d}/${cs.length}</small></div>`}).join('')}</div></div><div class="progress-card"><h3>学习成就</h3><div class="achievement-grid"><div class="achievement ${done>=1?'':'locked'}">🌱 完成第一章</div><div class="achievement ${done>=5?'':'locked'}">🧱 掌握基础语法</div><div class="achievement ${done>=12?'':'locked'}">📦 会使用数据结构</div><div class="achievement ${pdone>=1?'':'locked'}">🚀 完成第一个项目</div></div></div><div class="progress-card"><h3>错题提示与复习建议</h3><p>${state.reviewItems.length?state.reviewItems.slice(-5).map(id=>DATA.chapters.find(c=>c.id===id)?.title).filter(Boolean).join('、'):'暂无错题。完成测验后这里会显示需要复习的章节。'}</p></div>`;}

const PLAYGROUND_EXAMPLE = `# 自由练习：统计分数并给出建议
scores = [88, 92, 76, 95]
average = sum(scores) / len(scores)
print("平均分：", average)

if average >= 90:
    print("表现优秀，继续保持！")
else:
    print("已经不错，再练几题会更稳。")`;
function showPlaygroundFeedback(t){const box=$('playgroundFeedback');if(!box)return;box.textContent=t;box.classList.add('show')}
function initPlayground(){
  const editor=$('playgroundEditor');
  if(!editor)return;
  const saved=localStorage.getItem(PLAYGROUND_KEY);
  editor.value=saved || PLAYGROUND_EXAMPLE;
  editor.addEventListener('input',()=>localStorage.setItem(PLAYGROUND_KEY,editor.value));
  $('runPlaygroundBtn').onclick=()=>runPythonCode(editor.value,'playgroundOutput',false);
  $('savePlaygroundBtn').onclick=()=>{localStorage.setItem(PLAYGROUND_KEY,editor.value);showPlaygroundFeedback('草稿已保存到浏览器本地。')};
  $('loadExampleBtn').onclick=()=>{editor.value=PLAYGROUND_EXAMPLE;localStorage.setItem(PLAYGROUND_KEY,editor.value);$('playgroundOutput').textContent='已载入示例，点击“运行代码”查看结果。';showPlaygroundFeedback('已载入一个包含列表、平均值和 if 判断的示例。')};
  $('clearPlaygroundBtn').onclick=()=>{editor.value='';localStorage.setItem(PLAYGROUND_KEY,'');$('playgroundOutput').textContent='已清空，可以开始写新代码。';showPlaygroundFeedback('编辑器已清空。')};
}

function renderAll(){renderHome();renderCourses();renderLesson();renderPractice();renderGuided();renderQuiz();renderProjects();renderProgress();setTimeout(()=>enhanceCodeCopyButtons(),0);}
async function loadCourseData(){const res=await fetch('/api/data',{cache:'no-store'});if(!res.ok)throw new Error('后端数据接口不可用：'+res.status);return await res.json();}
async function init(){try{DATA=await loadCourseData();}catch(err){document.body.insertAdjacentHTML('afterbegin',`<div class="api-error">数据加载失败：${esc(err.message)}。请用 python3 server.py 启动后端，而不是普通静态服务器。</div>`);throw err;}currentLessonId=state.currentLessonId || DATA.chapters[0].id;currentProjectId=DATA.projects[0].id;currentGuidedLessonId=currentLessonId;renderCourseControls();renderAll();initPlayground();$('startBtn').onclick=()=>setLesson(DATA.chapters.find(c=>!state.completedLessons.includes(c.id))?.id||DATA.chapters[0].id);document.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>go(b.dataset.go));$('menuBtn').onclick=()=>$('nav').classList.toggle('open');window.addEventListener('hashchange',()=>go((location.hash||'#home').slice(1)));window.addEventListener('scroll',()=>$('toTopBtn').classList.toggle('show',scrollY>500));$('toTopBtn').onclick=()=>scrollTo({top:0,behavior:'smooth'});go((location.hash||'#home').slice(1));}
init();
