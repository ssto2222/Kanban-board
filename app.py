from flask import Flask, jsonify, request, render_template
import json
import os
import uuid
from datetime import date

app = Flask(__name__)

SAVE_FILE = os.path.join(os.path.expanduser("~"), ".sticky_kanban.json")


def load_tasks():
    if not os.path.exists(SAVE_FILE):
        return _get_samples()
    try:
        with open(SAVE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _get_samples()


def save_tasks(tasks):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def _get_samples():
    today = str(date.today())
    samples = [
        {"id": str(uuid.uuid4())[:8], "title": "UIデザイン確認",   "assignee": "田中", "deadline": today, "color": "#FFD166", "column": "todo", "note": "ワイヤーフレームレビュー"},
        {"id": str(uuid.uuid4())[:8], "title": "APIテスト",         "assignee": "佐藤", "deadline": today, "color": "#4CC9F0", "column": "todo", "note": "エンドポイント全件"},
        {"id": str(uuid.uuid4())[:8], "title": "バックエンド実装", "assignee": "鈴木", "deadline": "",    "color": "#06D6A0", "column": "wip",  "note": "認証モジュール"},
        {"id": str(uuid.uuid4())[:8], "title": "DB設計",            "assignee": "田中", "deadline": "",    "color": "#C77DFF", "column": "wip",  "note": "ER図作成"},
        {"id": str(uuid.uuid4())[:8], "title": "要件定義",          "assignee": "高橋", "deadline": "",    "color": "#EF476F", "column": "done", "note": "承認済み"},
    ]
    save_tasks(samples)
    return samples


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    return jsonify(load_tasks())


@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json()
    task = {
        "id":       str(uuid.uuid4())[:8],
        "title":    data.get("title", ""),
        "assignee": data.get("assignee", ""),
        "deadline": data.get("deadline", ""),
        "color":    data.get("color", "#FFD166"),
        "column":   data.get("column", "todo"),
        "note":     data.get("note", ""),
    }
    tasks = load_tasks()
    tasks.append(task)
    save_tasks(tasks)
    return jsonify(task), 201


@app.route("/api/tasks/<task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.get_json()
    tasks = load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            for k, v in data.items():
                if k != "id":
                    task[k] = v
            save_tasks(tasks)
            return jsonify(task)
    return jsonify({"error": "Not found"}), 404


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    tasks = load_tasks()
    tasks = [t for t in tasks if t["id"] != task_id]
    save_tasks(tasks)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
