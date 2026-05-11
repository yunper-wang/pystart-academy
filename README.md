# PyStart Academy

Python 初学者在线学习平台 —— 从零基础到独立完成小项目。

## 功能特点

- 30 个核心章节，覆盖 Python 基础到综合实践
- 457 道练习题，含基础巩固、综合应用和拓展挑战
- 内置 Python 运行环境（后端 /api/run 接口）
- 交互式闯关学习模式
- 7 个项目实战（BMI、计算器、猜数字等）
- 章节测验与学习进度跟踪
- 代码块一键复制
- 知识点详解参考廖雪峰 Python 教程体系

## 启动方式

```bash
cd python-learning-site
python3 server.py
```

然后访问 http://127.0.0.1:8765/

## 项目结构

```
├── index.html        # 主页面
├── style.css         # 样式
├── app.js            # 前端交互逻辑
├── data.json         # 课程数据（章节、练习、测验、项目）
├── server.py         # Python 后端（数据接口 + 代码运行）
├── script.js         # 旧版前端（保留兼容）
├── data.js           # 旧版数据（保留兼容）
└── import_futurecoder.py  # futurecoder 内容导入脚本
```

## 技术栈

- 前端：HTML + CSS + 原生 JavaScript（无框架）
- 后端：Python 标准库 http.server
- 数据：JSON 文件 + localStorage 学习进度
- 代码运行：后端临时目录执行，带超时和安全限制
