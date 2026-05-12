# PyStart Academy 后端主导大改造实施规划

> 目标：不再只是“把部分逻辑下沉”，而是把当前项目改造成以后端为核心的在线学习平台。前端只承担页面骨架、基础交互和少量 DOM 更新，课程组织、练习选择、闯关步骤、测验判分、进度计算、运行结果包装等全部由后端负责。

## 一、改造定位

当前项目本质上是“前端单页应用 + Python 运行接口”：

- `index.html` 提供所有页面容器；
- `app.js` 负责大部分页面组装、课程筛选、练习扁平化、闯关步骤生成、测验判分、进度计算、项目状态判断、甚至浏览器端 Python 简易模拟器；
- `server.py` 只负责返回 `data.json` 和执行 `/api/run`。

大改后的目标架构是：

- 后端成为业务中心；
- 前端不再理解完整业务规则；
- 前端尽量不直接处理原始 `data.json`；
- 前端请求“页面需要什么”，后端返回“可以直接渲染的数据或 HTML 片段”；
- 用户进度仍先保持本地浏览器存储，避免引入数据库和登录系统；
- 不引入 Flask、FastAPI、数据库等新依赖，继续使用 Python 标准库，保持项目轻量、易运行。

## 二、核心架构方案

### 1. 后端分层

保留单文件或少量文件结构，不做过度工程化。

推荐文件结构：

```text
├── server.py              # HTTP 路由层，只处理请求和响应
├── backend/
│   ├── __init__.py
│   ├── data_service.py    # 读取 data.json、构造课程索引
│   ├── page_service.py    # 构造各页面数据/HTML 片段
│   ├── progress_service.py# 进度、状态、成就、推荐下一步
│   ├── quiz_service.py    # 测验判分、解析、复习建议
│   ├── run_service.py     # Python 代码运行、安全限制、友好错误
│   └── html.py            # HTML 转义、组件渲染小工具
├── data.json
├── index.html
├── app.js
├── style.css
└── README.md
```

说明：

- 不引入复杂框架；
- `server.py` 仍然可以直接 `python3 server.py` 启动；
- `backend/*` 只是把业务函数拆开，避免 `server.py` 继续膨胀；
- 所有服务函数都应该是普通纯函数，便于测试和维护。

### 2. 后端返回方式

采用“JSON 页面模型 + 局部 HTML 片段”的折中方式。

原因：

- 纯 JSON：前端还要写大量模板拼接，逻辑仍然重；
- 纯服务端渲染整页：需要重写页面导航和交互，风险较大；
- JSON + HTML 片段：后端负责复杂组装，前端只把片段塞到对应容器里，兼容现有页面结构。

例如：

```json
{
  "page": "home",
  "html": {
    "heroStats": "<div class=\"stat-chip\">...</div>",
    "homeStages": "<article class=\"roadmap-item\">...</article>"
  },
  "state": {
    "currentLessonId": "ch01"
  }
}
```

前端只做：

```js
applyHtml(payload.html)
```

## 三、接口规划

### 1. GET /api/app/bootstrap

用途：初始化应用。

后端返回：

- 站点基础统计；
- 默认章节；
- 默认项目；
- 页面导航信息；
- 课程总数、练习总数、项目总数；
- 前端需要保留的最低限度配置。

前端职责：

- 保存 `APP` 基础信息；
- 根据 hash 请求对应页面；
- 不再加载原始 `/api/data` 作为主数据源。

兼容：

- 保留 `/api/data`，但只作为调试接口和兼容接口。

### 2. POST /api/page/home

请求：

```json
{
  "progress": {...}
}
```

后端负责：

- 计算总进度；
- 计算首页阶段路线；
- 生成首页统计卡片；
- 生成学习路径 HTML。

返回：

```json
{
  "html": {
    "heroStats": "...",
    "homeStages": "..."
  }
}
```

### 3. POST /api/page/courses

请求：

```json
{
  "progress": {...},
  "filter": "all",
  "query": "循环",
  "currentLessonId": "ch08"
}
```

后端负责：

- 阶段筛选；
- 关键词搜索；
- 阶段完成数；
- 章节状态：未开始、学习中、已完成；
- 课程卡片 HTML；
- 章节侧边栏 HTML；
- 当前章节详情 HTML；
- 当前章节的闯关区 HTML。

前端职责：

- 监听搜索框输入；
- 把搜索词发给后端；
- 替换 `courseStageList`、`lessonList`、`lessonDetail`、`guided*` 容器。

### 4. POST /api/page/practice

请求：

```json
{
  "progress": {...},
  "practiceIndex": 0,
  "lessonId": "ch03",
  "exerciseIndex": 2
}
```

后端负责：

- 扁平化所有练习；
- 根据 lessonId/exerciseIndex 定位练习；
- 生成练习选择器；
- 生成题目详情；
- 返回 starter、answerCode、hint、analysis；
- 处理 futurecoder 原文块。

前端职责：

- 维护当前练习 index；
- 点击提示时展示后端返回的 hint；
- 点击答案时把后端返回的 answerCode 写入编辑器；
- 不再执行 `makePractice()` 和 `allPractices()`。

### 5. POST /api/page/quiz

请求：

```json
{
  "lessonId": "ch01"
}
```

后端负责：

- 返回课程选择器 HTML；
- 返回测验题 HTML；
- 隐藏或不暴露正确答案到页面模型中。

前端职责：

- 收集表单输入；
- 调用 `/api/quiz/submit`；
- 展示后端判分结果。

### 6. POST /api/quiz/submit

请求：

```json
{
  "lessonId": "ch01",
  "answers": ["A", "正确", "print"]
}
```

后端负责：

- 标准化答案；
- 判分；
- 返回每题结果；
- 生成解析 HTML；
- 生成复习建议；
- 返回需要加入 reviewItems 的 lessonId。

返回：

```json
{
  "score": 80,
  "adviceHtml": "...",
  "resultHtmlByIndex": {
    "0": "...",
    "1": "..."
  },
  "reviewLessonId": "ch01"
}
```

### 7. POST /api/page/projects

请求：

```json
{
  "progress": {...},
  "projectId": "bmi"
}
```

后端负责：

- 项目列表状态；
- 当前项目详情；
- 项目完成状态；
- 代码 HTML 转义。

前端职责：

- 点击项目，传 projectId；
- 点击完成，更新本地 progress 后重新请求页面。

### 8. POST /api/page/progress

请求：

```json
{
  "progress": {...}
}
```

后端负责：

- 总进度；
- 阶段进度；
- 下一步推荐；
- 成就解锁；
- 错题复习章节标题；
- 生成完整进度 HTML。

前端职责：

- 只负责渲染返回的 `progressDashboard`。

### 9. POST /api/run

保留现有接口，但增强。

后端负责：

- 代码长度校验；
- 系统命令黑名单；
- 临时目录运行；
- 超时处理；
- stderr/stdout 合并；
- 友好错误提示；
- suggestions 数组。

前端职责：

- 发送代码；
- 展示 `output` 或 `friendlyMessage`；
- 不再包含浏览器 Python 模拟器。

## 四、前端改造方向

### 1. app.js 改成轻量客户端

新的 `app.js` 只保留这些类型的函数：

- `apiPost(path, payload)`；
- `applyHtml(htmlMap)`；
- `loadState()` / `saveState()`；
- `loadPage(page)`；
- `bindEvents()`；
- `runCode()`；
- `submitQuiz()`；
- `enhanceCodeCopyButtons()`；
- `esc()` 可保留少量展示保护，但主要转义在后端。

删除或迁移：

- `stageOf()` → 后端；
- `statusFor()` → 后端；
- `pct()` → 后端；
- `renderHome()` 内计算逻辑 → 后端；
- `renderCourses()` 内筛选和统计 → 后端；
- `renderLesson()` 详情拼装 → 后端；
- `makePractice()` → 后端；
- `allPractices()` → 后端；
- `guidedStepsFor()` → 后端；
- `guidedLessons()` → 后端；
- `renderQuiz()` 题目拼装 → 后端；
- `submitQuiz()` 判分 → 后端；
- `renderProjects()` 项目详情拼装 → 后端；
- `renderProgress()` 进度推导 → 后端；
- `pyString()`、`splitArgs()`、`transformExpr()`、`evalExpr()`、`runLines()`、`simulatePython()` → 删除。

### 2. HTML 保持基本不变

为了降低风险，不重写 `index.html` 的整体结构。

保留：

- 顶部导航；
- 各 section 容器；
- 原有 id；
- 原有 class；
- 原有 CSS。

这样用户体验基本不变，主要变化在 `app.js` 和后端。

### 3. localStorage 仍然保留

原因：

- 当前项目没有登录系统；
- 不引入数据库；
- 初学者本地运行更简单。

但 localStorage 只保存原始用户行为：

```json
{
  "completedLessons": [],
  "completedProjects": [],
  "quizResults": {},
  "reviewItems": [],
  "currentLessonId": "..."
}
```

所有衍生状态由后端计算。

## 五、实施步骤

### 阶段 1：建立后端服务层

1. 创建 `backend/__init__.py`。
2. 创建 `backend/html.py`，实现：
   - `esc()`；
   - `tag_list()`；
   - `status_class()` 等简单 HTML 工具。
3. 创建 `backend/data_service.py`，实现：
   - `load_data()`；
   - `get_chapter()`；
   - `get_project()`；
   - `flatten_practices()`；
   - `build_guided_steps()`。
4. 创建 `backend/progress_service.py`，实现：
   - `summarize_progress()`；
   - `lesson_status_map()`；
   - `project_status_map()`；
   - `stage_progress()`；
   - `achievements()`。

### 阶段 2：实现页面服务

1. 创建 `backend/page_service.py`。
2. 实现：
   - `render_home_page()`；
   - `render_courses_page()`；
   - `render_practice_page()`；
   - `render_quiz_page()`；
   - `render_projects_page()`；
   - `render_progress_page()`。
3. 每个函数返回：

```python
{
    "html": {
        "containerId": "<div>...</div>"
    },
    "data": {
        "minimalFrontEndState": "..."
    }
}
```

### 阶段 3：实现测验服务

1. 创建 `backend/quiz_service.py`。
2. 实现：
   - `normalize_answer()`；
   - `grade_quiz()`；
   - `build_quiz_result_html()`；
   - `build_quiz_advice()`。
3. 保证答案不再提前暴露给前端用于判分。

### 阶段 4：增强运行服务

1. 创建 `backend/run_service.py`。
2. 把 `/api/run` 逻辑从 `server.py` 移入该文件。
3. 增加：
   - `friendlyMessage`；
   - `suggestions`；
   - 统一错误结构。
4. 删除前端 Python 模拟器 fallback。

### 阶段 5：重写 server.py 路由层

1. 保留静态文件服务能力。
2. 增加 JSON body 解析工具。
3. 增加路由：
   - `GET /api/app/bootstrap`
   - `POST /api/page/home`
   - `POST /api/page/courses`
   - `POST /api/page/practice`
   - `POST /api/page/quiz`
   - `POST /api/quiz/submit`
   - `POST /api/page/projects`
   - `POST /api/page/progress`
   - `POST /api/run`
4. 保留：
   - `GET /api/data`

### 阶段 6：重写 app.js 为轻量客户端

1. 保留 localStorage 状态函数。
2. 实现统一请求：

```js
async function apiPost(path, payload) { ... }
```

3. 实现统一渲染：

```js
function applyHtml(html) {
  Object.entries(html).forEach(([id, value]) => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = value;
  });
}
```

4. 根据 hash 加载页面：

```js
async function loadPage(name) { ... }
```

5. 绑定事件：
   - 导航切换；
   - 课程搜索；
   - 课程点击；
   - 练习切换；
   - 提示/答案/重置；
   - 测验提交；
   - 项目完成；
   - 代码运行。

6. 删除所有前端业务计算函数。

### 阶段 7：验证和修复

必须验证：

1. `python3 server.py` 可启动；
2. `GET /api/app/bootstrap` 返回 200；
3. 首页正常渲染；
4. 课程搜索、阶段筛选正常；
5. 章节详情正常；
6. 闯关步骤正常；
7. 在线练习能切题、看提示、填答案、运行代码；
8. 章节测验由后端判分；
9. 项目详情正常显示；
10. 标记完成章节/项目后进度变化正确；
11. `/api/run` 能运行基础代码；
12. 后端不可用时前端给出明确提示；
13. Git 提交并推送到 GitHub。

## 六、风险与处理

### 风险 1：后端返回 HTML，前端灵活性下降

接受这个取舍。当前目标是后端完全替代前端业务逻辑，HTML 片段更符合目标。

### 风险 2：server.py 变复杂

通过 `backend/*` 服务层拆分，避免单文件过大。

### 风险 3：不使用数据库导致状态仍在前端

这是刻意保留。状态“存储”在前端，状态“计算”在后端。这样不破坏本地运行体验，也符合“不引入不必要依赖”。

### 风险 4：测验答案仍可能通过接口被看到

静态本地学习项目无法彻底防作弊，但可以避免把答案直接放在测验页面模型里。用户若查看 data.json 仍能看到答案，这是当前无数据库架构下的合理限制。

## 七、建议提交节奏

1. `refactor: add backend service layer`
2. `feat: add backend-driven page api`
3. `refactor: replace frontend course rendering with backend html`
4. `refactor: move quiz grading and progress summary to backend`
5. `refactor: simplify app.js and remove browser python simulator`
6. `docs: update architecture and usage notes`

## 八、最终效果

改造完成后：

- 后端承担主要业务逻辑；
- 前端代码量明显下降；
- 前端不再重复计算课程、练习、进度和测验规则；
- 接口返回内容更贴近页面容器；
- Python 运行逻辑只在后端；
- 项目结构从“前端大脚本”变成“后端服务层 + 轻量前端”；
- 用户看到的页面和使用路径基本不变。
