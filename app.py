from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from functools import wraps
import json
import os
import uuid
from datetime import date, datetime, timezone

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-prod")

SAVE_FILE  = os.path.join(os.path.expanduser("~"), ".sticky_kanban.json")
USERS_FILE = os.path.join(os.path.expanduser("~"), ".sticky_kanban_users.json")


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


# ── ユーザーストレージ ────────────────────────────────────────────────────────

def _users_file_load():
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _users_file_save(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def load_users():
    supabase = _get_supabase()
    if supabase:
        try:
            res = supabase.table("users").select("id,username,display_name,created_at").order("created_at").execute()
            return res.data or []
        except Exception:
            pass
    return _users_file_load()


def find_user(username):
    for u in load_users():
        if u.get("username") == username:
            return u
    return None


def create_user(username, display_name, password):
    from werkzeug.security import generate_password_hash
    user = {
        "id":            str(uuid.uuid4())[:8],
        "username":      username,
        "display_name":  display_name or username,
        "password_hash": generate_password_hash(password),
        "created_at":    datetime.now(timezone.utc).isoformat(),
    }
    supabase = _get_supabase()
    if supabase:
        try:
            res = supabase.table("users").insert(user).execute()
            return res.data[0] if res.data else user
        except Exception:
            pass
    users = _users_file_load()
    users.append(user)
    _users_file_save(users)
    return user


def check_password(username, password):
    from werkzeug.security import check_password_hash
    supabase = _get_supabase()
    if supabase:
        try:
            res = supabase.table("users").select("*").eq("username", username).execute()
            if res.data:
                u = res.data[0]
                if check_password_hash(u["password_hash"], password):
                    return u
                return None
        except Exception:
            pass
    for u in _users_file_load():
        if u.get("username") == username:
            if check_password_hash(u.get("password_hash", ""), password):
                return u
            return None
    return None


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
    user = find_user(session["username"]) if "username" in session else None
    return render_template("index.html", current_user=user)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = check_password(username, password)
        if user:
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            session["display_name"] = user.get("display_name", username)
            return redirect(url_for("index"))
        error = "ユーザー名またはパスワードが正しくありません"
    return render_template("login.html", mode="login", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username     = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip()
        password     = request.form.get("password", "")
        confirm      = request.form.get("confirm", "")

        if not username or not password:
            error = "ユーザー名とパスワードは必須です"
        elif len(username) < 3:
            error = "ユーザー名は3文字以上にしてください"
        elif password != confirm:
            error = "パスワードが一致しません"
        elif find_user(username):
            error = "そのユーザー名は既に使われています"
        else:
            user = create_user(username, display_name, password)
            session["user_id"]      = user["id"]
            session["username"]     = user["username"]
            session["display_name"] = user.get("display_name", username)
            return redirect(url_for("index"))

    return render_template("login.html", mode="register", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    return jsonify(load_tasks())


@app.route("/api/assignees", methods=["GET"])
def get_assignees():
    tasks = load_tasks()
    assignees = sorted({t.get("assignee") for t in tasks if t.get("assignee")})
    return jsonify(assignees)


@app.route("/api/users", methods=["GET"])
def get_users():
    q = request.args.get("q", "").lower()
    users = load_users()
    result = [
        {"username": u["username"], "display_name": u.get("display_name", u["username"])}
        for u in users
        if not q or q in u["username"].lower() or q in u.get("display_name", "").lower()
    ]
    return jsonify(result)


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
