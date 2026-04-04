from flask import Flask, jsonify, request, render_template
import json
import os
import uuid
from datetime import date, datetime, timezone

app = Flask(__name__)

SAVE_FILE = os.path.join(os.path.expanduser("~"), ".sticky_kanban.json")


def _get_supabase():
    """Supabaseクライアントを返す。未設定の場合はNone。"""
    try:
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if url and key:
            return create_client(url, key)
    except ImportError:
        pass
    return None


# ── JSON ファイルストレージ (Supabase 未設定時のフォールバック) ─────────────

def _file_load():
    if not os.path.exists(SAVE_FILE):
        return _get_samples()
    try:
        with open(SAVE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _get_samples()


def _file_save(tasks):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def _get_samples():
    today = str(date.today())
    samples = [
        {"id": str(uuid.uuid4())[:8], "title": "UIデザイン確認",   "assignee": "田中", "deadline": today, "color": "#FFD166", "column": "todo", "note": "ワイヤーフレームレビュー", "started_at": "", "finished_at": ""},
        {"id": str(uuid.uuid4())[:8], "title": "APIテスト",         "assignee": "佐藤", "deadline": today, "color": "#4CC9F0", "column": "todo", "note": "エンドポイント全件",       "started_at": "", "finished_at": ""},
        {"id": str(uuid.uuid4())[:8], "title": "バックエンド実装", "assignee": "鈴木", "deadline": "",    "color": "#06D6A0", "column": "wip",  "note": "認証モジュール",           "started_at": "", "finished_at": ""},
        {"id": str(uuid.uuid4())[:8], "title": "DB設計",            "assignee": "田中", "deadline": "",    "color": "#C77DFF", "column": "wip",  "note": "ER図作成",                 "started_at": "", "finished_at": ""},
        {"id": str(uuid.uuid4())[:8], "title": "要件定義",          "assignee": "高橋", "deadline": "",    "color": "#EF476F", "column": "done", "note": "承認済み",                 "started_at": "", "finished_at": ""},
    ]
    _file_save(samples)
    return samples


# ── タスク CRUD ──────────────────────────────────────────────────────────────

def load_tasks():
    supabase = _get_supabase()
    if supabase:
        try:
            res = supabase.table("tasks").select("*").order("created_at").execute()
            return res.data or []
        except Exception:
            pass
    return _file_load()


def _create_task_file(data):
    task = {
        "id":          str(uuid.uuid4())[:8],
        "title":       data.get("title", ""),
        "assignee":    data.get("assignee", ""),
        "deadline":    data.get("deadline", ""),
        "color":       data.get("color", "#FFD166"),
        "column":      data.get("column", "todo"),
        "note":        data.get("note", ""),
        "started_at":  data.get("started_at", ""),
        "finished_at": data.get("finished_at", ""),
        "created_at":  datetime.now(timezone.utc).isoformat(),
    }
    tasks = _file_load()
    tasks.append(task)
    _file_save(tasks)
    return task


def _update_task_file(task_id, data):
    tasks = _file_load()
    for task in tasks:
        if task["id"] == task_id:
            for k, v in data.items():
                if k != "id":
                    task[k] = v
            _file_save(tasks)
            return task
    return None


def _delete_task_file(task_id):
    tasks = _file_load()
    tasks = [t for t in tasks if t["id"] != task_id]
    _file_save(tasks)


# ── ルート ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    return jsonify(load_tasks())


@app.route("/api/assignees", methods=["GET"])
def get_assignees():
    tasks = load_tasks()
    assignees = sorted({t.get("assignee") for t in tasks if t.get("assignee")})
    return jsonify(assignees)


@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json()
    supabase = _get_supabase()
    if supabase:
        try:
            payload = {k: v for k, v in data.items() if v is not None and str(v).strip() != ""}
            payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
            res = supabase.table("tasks").insert(payload).execute()
            return jsonify(res.data[0] if res.data else payload), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    task = _create_task_file(data)
    return jsonify(task), 201


@app.route("/api/tasks/<task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.get_json()
    supabase = _get_supabase()
    if supabase:
        try:
            res = supabase.table("tasks").update(data).eq("id", task_id).execute()
            return jsonify(res.data[0] if res.data else data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    task = _update_task_file(task_id, data)
    if task is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(task)


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    supabase = _get_supabase()
    if supabase:
        try:
            supabase.table("tasks").delete().eq("id", task_id).execute()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    _delete_task_file(task_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
