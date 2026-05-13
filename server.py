#!/usr/bin/env python3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os

from backend import data_service, page_service, progress_service, quiz_service, run_service, question_bank_service

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data.json"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            payload = self.read_json_body()
            data = data_service.load_data()
            progress = payload.get("progress") or {}
            if path == "/api/run":
                self.send_json(run_service.run_python(payload.get("code", "")))
                return
            if path == "/api/progress/summary":
                self.send_json(progress_service.summarize(progress, data))
                return
            if path == "/api/question-bank/import":
                bank = payload.get("questionBank")
                stats = question_bank_service.import_question_bank(bank, data_service.load_course_data())
                data_service.clear_cache()
                refreshed = data_service.load_data()
                self.send_json({
                    "ok": True,
                    "message": "题库导入成功。",
                    "stats": stats,
                    "questionBank": refreshed.get("questionBank"),
                    "bootstrap": {
                        **data_service.bootstrap(refreshed),
                        "stages": data_service.get_stages(refreshed),
                        "chapters": data_service.get_chapters(refreshed),
                        "projects": data_service.get_projects(refreshed),
                        "practices": data_service.flatten_practices(refreshed),
                    },
                })
                return
            if path == "/api/page/home":
                self.send_json(page_service.page_home(progress, data))
                return
            if path == "/api/page/courses":
                self.send_json(page_service.page_courses(progress, payload.get("stageFilter", "all"), payload.get("query", ""), payload.get("currentLessonId"), data))
                return
            if path == "/api/page/lesson":
                self.send_json(page_service.page_lesson(progress, payload.get("lessonId"), data))
                return
            if path == "/api/page/practice":
                index = payload.get("index", 0)
                if payload.get("lessonId") is not None:
                    index = data_service.practice_index_for(payload.get("lessonId"), payload.get("exerciseIndex", 0), data)
                self.send_json(page_service.page_practice(index, data))
                return
            if path == "/api/page/guided":
                self.send_json(page_service.page_guided(progress, payload.get("lessonId"), payload.get("stepIndex", 0), data))
                return
            if path == "/api/page/quiz":
                self.send_json(page_service.page_quiz(payload.get("lessonId"), data))
                return
            if path == "/api/quiz/submit":
                result = quiz_service.submit(payload.get("lessonId"), payload.get("answers") or [], data)
                if result.get("ok"):
                    html_parts = page_service.quiz_result_html(result)
                    result["html"] = "".join(html_parts.values())
                    result["htmlParts"] = html_parts
                else:
                    result["html"] = ""
                    result["htmlParts"] = {}
                self.send_json(result, 200 if result.get("ok") else 400)
                return
            if path == "/api/page/projects":
                self.send_json(page_service.page_projects(progress, payload.get("projectId"), data))
                return
            if path == "/api/page/progress":
                self.send_json(page_service.page_progress(progress, data))
                return
        except json.JSONDecodeError:
            self.send_json({"ok": False, "error": "请求数据格式不正确。"}, 400)
            return
        except Exception as exc:
            self.send_json({"ok": False, "error": "服务端处理失败：" + str(exc)}, 500)
            return
        self.send_json({"error": "not found"}, 404)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/data":
            try:
                self.send_json(data_service.load_data())
            except FileNotFoundError:
                self.send_json({"error": "data.json or question bank not found"}, 404)
            except json.JSONDecodeError as exc:
                self.send_json({"error": "invalid json data", "detail": str(exc)}, 500)
            except question_bank_service.QuestionBankError as exc:
                self.send_json({"error": "invalid question bank", "detail": str(exc)}, 500)
            return
        if path == "/api/question-bank/export":
            self.send_json(question_bank_service.load_question_bank())
            return
        if path == "/api/app/bootstrap":
            data = data_service.load_data()
            self.send_json({
                **data_service.bootstrap(data),
                **page_service.course_controls(data),
                "stages": data_service.get_stages(data),
                "chapters": data_service.get_chapters(data),
                "projects": data_service.get_projects(data),
                "practices": data_service.flatten_practices(data),
                "questionBank": data.get("questionBank"),
            })
            return
        dist = ROOT / "dist"
        if dist.exists():
            if path == "/" or path == "/index.html":
                self.path = "/dist/index.html"
            elif (dist / path.lstrip("/")).exists():
                self.path = "/dist" + path
            elif "." not in Path(path).name:
                self.path = "/dist/index.html"
        return super().do_GET()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"PyStart backend running: http://127.0.0.1:{port}/")
    print(f"API: http://127.0.0.1:{port}/api/app/bootstrap")
    server.serve_forever()
