const STORE_KEY = 'pystart_academy_progress_v2';
const PLAYGROUND_KEY = 'pystart_python_playground_code_v1';

let bootstrap = null;
let state = loadState();
let currentLessonId = null;
let currentPracticeIndex = 0;
let currentProjectId = null;
let currentGuidedLessonId = null;
let currentGuidedStepIndex = 0;
let currentPractice = null;
let currentGuidedStep = null;
let lessonNav = {prevLessonId:null,nextLessonId:null};

function $(id){return document.getElementById(id)}
function esc(s){return String(s ?? '').replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));}
function loadState(){try{return JSON.parse(localStorage.getItem(STORE_KEY)) || {completedLessons:[], completedProjects:[], quizResults:{}, reviewItems:[], currentLessonId:null};}catch(e){return {completedLessons:[], completedProjects:[], quizResults:{}, reviewItems:[], currentLessonId:null};}}
function saveState(){state.currentLessonId=currentLessonId;localStorage.setItem(STORE_KEY, JSON.stringify(state));}
function applyHtml(html){Object.entries(html||{}).forEach(([id,content])=>{const el=$(id);if(el)el.innerHTML=content;});setTimeout(()=>enhanceCodeCopyButtons(),0);}
async function api(path, payload){const res=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload||{})});const data=await res.json();if(!res.ok||data.ok===false)throw new Error(data.error||('接口失败：'+path));return data;}
function progressPayload(){return {progress:state};}
function go(id){location.hash=id;document.querySelectorAll('.nav a').forEach(a=>a.classList.toggle('active',a.dataset.nav===id));}

function toggleInArray(arr,id){return arr.includes(id)?arr.filter(x=>x!==id):[...arr,id];}
async function setLesson(id,target='courses'){currentLessonId=id;currentGuidedLessonId=id;currentGuidedStepIndex=0;saveState();await renderCourses();await renderLesson();await renderGuided();await renderProgress();go(target);}
async function openPractice(lessonId, exerciseIndex=0){currentLessonId=lessonId;saveState();const data=await api('/api/page/practice',{lessonId,exerciseIndex});renderPracticePayload(data);go('practice');setTimeout(()=>$('codeEditor')?.focus(),80);}
async function toggleLessonDone(id){state.completedLessons=toggleInArray(state.completedLessons,id);saveState();await renderAll();}
async function toggleProjectDone(id){state.completedProjects=toggleInArray(state.completedProjects,id);saveState();await renderProjects();await renderProgress();}

function enhanceCodeCopyButtons(root=document){
  root.querySelectorAll('pre.code-block, pre.inline-output, .futurecoder-html pre').forEach((pre)=>{
    if(pre.dataset.copyReady)return;
    pre.dataset.copyReady='1';
    const wrap=document.createElement('div');
    wrap.className='copy-code-wrap';
    pre.parentNode.insertBefore(wrap,pre);
    wrap.appendChild(pre);
    const btn=document.createElement('button');
    btn.type='button';btn.className='copy-code-btn';btn.textContent='复制';
    btn.onclick=async()=>{
      const text=pre.innerText||pre.textContent||'';
      try{
        if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(text);}else{const ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove();}
        btn.textContent='已复制';btn.classList.add('copied');setTimeout(()=>{btn.textContent='复制';btn.classList.remove('copied');},1200);
      }catch(e){btn.textContent='复制失败';setTimeout(()=>btn.textContent='复制',1200);}
    };
    wrap.appendChild(btn);
  });
}

async function renderHome(){const data=await api('/api/page/home',progressPayload());applyHtml(data.html);}
async function renderCourses(){const data=await api('/api/page/courses',{...progressPayload(),stageFilter:$('stageFilter')?.value||'all',query:$('courseSearch')?.value||'',currentLessonId});applyHtml(data.html);bindCourseEvents();}
async function renderLesson(){const data=await api('/api/page/lesson',{...progressPayload(),lessonId:currentLessonId});currentLessonId=data.currentLessonId;lessonNav=data;saveState();applyHtml(data.html);bindLessonEvents();}
function bindCourseEvents(){document.querySelectorAll('.course-card').forEach(card=>card.onclick=()=>setLesson(card.dataset.lesson));}
function bindLessonEvents(){
  document.querySelectorAll('.lesson-btn').forEach(b=>b.onclick=()=>setLesson(b.dataset.lesson));
  document.querySelectorAll('.exercise-link').forEach(b=>b.onclick=()=>openPractice(b.dataset.lesson,+b.dataset.exercise));
  if($('prevLessonBtn'))$('prevLessonBtn').onclick=()=>lessonNav.prevLessonId&&setLesson(lessonNav.prevLessonId);
  if($('nextLessonBtn'))$('nextLessonBtn').onclick=()=>lessonNav.nextLessonId&&setLesson(lessonNav.nextLessonId);
  if($('markLessonBtn'))$('markLessonBtn').onclick=()=>toggleLessonDone(currentLessonId);
}
function renderCourseControls(){
  $('stageFilter').innerHTML=bootstrap.stageOptions;
  $('stageSidebar').innerHTML=bootstrap.stageSidebar;
  $('quizLessonSelect').innerHTML=bootstrap.quizLessonOptions;
  document.querySelectorAll('.side-btn').forEach(btn=>btn.onclick=async()=>{document.querySelectorAll('.side-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');$('stageFilter').value=btn.dataset.stage;await renderCourses();});
  $('stageFilter').onchange=renderCourses;
  $('courseSearch').oninput=renderCourses;
}

async function renderPractice(){const data=await api('/api/page/practice',{index:currentPracticeIndex});renderPracticePayload(data);}
function renderPracticePayload(data){currentPracticeIndex=data.currentPracticeIndex;currentPractice=data.practice;applyHtml(data.html);document.querySelectorAll('.practice-btn').forEach(b=>b.onclick=async()=>{currentPracticeIndex=+b.dataset.i;await renderPractice();});if(currentPractice){$('codeEditor').value=currentPractice.starter||'';$('codeOutput').textContent='点击“运行代码”查看结果';}$('practiceFeedback').classList.remove('show');$('hintBtn').onclick=()=>showFeedback('提示：'+(currentPractice?.hint||''));$('answerBtn').onclick=()=>{$('codeEditor').value=currentPractice?.answerCode||'';showFeedback('参考答案已填入。解析：'+(currentPractice?.analysis||''));};$('resetCodeBtn').onclick=()=>{$('codeEditor').value=currentPractice?.starter||'';$('codeOutput').textContent='已重置，请继续练习。';showFeedback('已恢复本题初始代码。')};$('runCodeBtn').onclick=runCode;}
function showFeedback(t){$('practiceFeedback').textContent=t;$('practiceFeedback').classList.add('show')}
async function runPythonCode(code, outputId){$(outputId).textContent='正在运行...';try{const data=await api('/api/run',{code});$(outputId).textContent=data.ok?(data.output||'程序运行完成，但没有 print() 输出。'):(data.friendlyMessage||data.error||data.output||'代码运行失败。');return {ok:data.ok,data};}catch(err){$(outputId).textContent='无法连接本地 Python 运行服务。请确认使用 python3 server.py 启动，并通过 8765 后端地址访问。';return {ok:false,error:err};}}
async function runCode(){await runPythonCode($('codeEditor').value,'codeOutput');}

async function renderGuided(){const data=await api('/api/page/guided',{...progressPayload(),lessonId:currentGuidedLessonId||currentLessonId,stepIndex:currentGuidedStepIndex});currentGuidedLessonId=data.currentGuidedLessonId;currentGuidedStepIndex=data.currentGuidedStepIndex;currentGuidedStep=data.step;applyHtml(data.html);$('guidedEditor').value=currentGuidedStep?.starter||'';$('guidedOutput').textContent='点击“运行并检查”查看结果。';$('guidedFeedback').classList.remove('show');bindGuidedEvents(data.stepCount);}
function bindGuidedEvents(stepCount){document.querySelectorAll('.guided-toc-btn').forEach(b=>b.onclick=async()=>{currentGuidedLessonId=b.dataset.guided;currentGuidedStepIndex=0;currentLessonId=currentGuidedLessonId;saveState();await renderGuided();await renderLesson();});document.querySelectorAll('.step-pill').forEach(b=>b.onclick=async()=>{currentGuidedStepIndex=+b.dataset.step;await renderGuided();});if($('guidedOpenLessonBtn'))$('guidedOpenLessonBtn').onclick=()=>setLesson(currentGuidedLessonId,'courses');$('runGuidedBtn').onclick=async()=>{const result=await runPythonCode($('guidedEditor').value,'guidedOutput');if(result.ok){showGuidedFeedback('运行成功。你可以继续修改代码观察变化，或进入下一步。');if(currentGuidedStepIndex<stepCount-1){currentGuidedStepIndex++;setTimeout(()=>renderGuided(),650);}}};$('guidedHintBtn').onclick=()=>showGuidedFeedback('提示：'+(currentGuidedStep?.hint||''));$('guidedAnswerBtn').onclick=()=>{$('guidedEditor').value=currentGuidedStep?.answer||'';showGuidedFeedback('已填入参考答案。建议先运行，再对照理解每一行。')};$('guidedResetBtn').onclick=()=>{$('guidedEditor').value=currentGuidedStep?.starter||'';$('guidedOutput').textContent='已重置本步骤代码。';showGuidedFeedback('已恢复本步骤初始代码。')};}
function showGuidedFeedback(t){const box=$('guidedFeedback');if(!box)return;box.textContent=t;box.classList.add('show')}

async function renderQuiz(){const lessonId=$('quizLessonSelect').value||currentLessonId;const data=await api('/api/page/quiz',{lessonId});applyHtml(data.html);$('quizAdvice').classList.remove('show');$('submitQuizBtn').onclick=()=>submitQuiz(data.questionCount);$('quizLessonSelect').onchange=renderQuiz;}
function getAns(i){const checked=document.querySelector(`input[name="q${i}"]:checked`);if(checked)return checked.value;return($('qa-'+i)?.value||'').trim();}
async function submitQuiz(questionCount){const lessonId=$('quizLessonSelect').value;const answers=Array.from({length:questionCount},(_,i)=>getAns(i));const data=await api('/api/quiz/submit',{lessonId,answers});$('quizAdvice').className='quiz-advice show';$('quizAdvice').innerHTML=data.html.adviceHtml;const temp=document.createElement('div');temp.innerHTML=data.html.resultHtml;temp.querySelectorAll('.quiz-result-block').forEach(block=>{const box=$('qr-'+block.dataset.i);if(box){box.style.display='block';box.innerHTML=block.innerHTML;}});state.quizResults[lessonId]={score:data.score,date:new Date().toLocaleDateString()};if(data.reviewLessonId&&!state.reviewItems.includes(data.reviewLessonId))state.reviewItems.push(data.reviewLessonId);saveState();await renderProgress();}

async function renderProjects(){const data=await api('/api/page/projects',{...progressPayload(),projectId:currentProjectId});currentProjectId=data.currentProjectId;applyHtml(data.html);document.querySelectorAll('.project-card').forEach(card=>card.onclick=async()=>{currentProjectId=card.dataset.project;await renderProjects();});$('markProjectBtn').onclick=()=>toggleProjectDone(currentProjectId);}
async function renderProgress(){const data=await api('/api/page/progress',progressPayload());applyHtml(data.html);}

const PLAYGROUND_EXAMPLE = `# 自由练习：统计分数并给出建议
scores = [88, 92, 76, 95]
average = sum(scores) / len(scores)
print("平均分：", average)

if average >= 90:
    print("表现优秀，继续保持！")
else:
    print("已经不错，再练几题会更稳。")`;
function showPlaygroundFeedback(t){const box=$('playgroundFeedback');if(!box)return;box.textContent=t;box.classList.add('show')}
function initPlayground(){const editor=$('playgroundEditor');if(!editor)return;editor.value=localStorage.getItem(PLAYGROUND_KEY)||PLAYGROUND_EXAMPLE;editor.addEventListener('input',()=>localStorage.setItem(PLAYGROUND_KEY,editor.value));$('runPlaygroundBtn').onclick=()=>runPythonCode(editor.value,'playgroundOutput');$('savePlaygroundBtn').onclick=()=>{localStorage.setItem(PLAYGROUND_KEY,editor.value);showPlaygroundFeedback('草稿已保存到浏览器本地。')};$('loadExampleBtn').onclick=()=>{editor.value=PLAYGROUND_EXAMPLE;localStorage.setItem(PLAYGROUND_KEY,editor.value);$('playgroundOutput').textContent='已载入示例，点击“运行代码”查看结果。';showPlaygroundFeedback('已载入一个包含列表、平均值和 if 判断的示例。')};$('clearPlaygroundBtn').onclick=()=>{editor.value='';localStorage.setItem(PLAYGROUND_KEY,'');$('playgroundOutput').textContent='已清空，可以开始写新代码。';showPlaygroundFeedback('编辑器已清空。')};}

async function renderAll(){await renderHome();await renderCourses();await renderLesson();await renderPractice();await renderGuided();await renderQuiz();await renderProjects();await renderProgress();}
async function init(){try{const res=await fetch('/api/app/bootstrap',{cache:'no-store'});bootstrap=await res.json();if(!res.ok)throw new Error('后端启动数据接口不可用');}catch(err){document.body.insertAdjacentHTML('afterbegin',`<div class="api-error">数据加载失败：${esc(err.message)}。请用 python3 server.py 启动后端。</div>`);throw err;}currentLessonId=state.currentLessonId||bootstrap.defaultIds.lessonId;currentProjectId=bootstrap.defaultIds.projectId;currentGuidedLessonId=currentLessonId;renderCourseControls();await renderAll();initPlayground();$('startBtn').onclick=()=>setLesson(currentLessonId);document.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>go(b.dataset.go));$('menuBtn').onclick=()=>$('nav').classList.toggle('open');window.addEventListener('hashchange',()=>go((location.hash||'#home').slice(1)));window.addEventListener('scroll',()=>$('toTopBtn').classList.toggle('show',scrollY>500));$('toTopBtn').onclick=()=>scrollTo({top:0,behavior:'smooth'});go((location.hash||'#home').slice(1));}
init();
