from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from functools import wraps
import json
import os
import uuid
from datetime import date, datetime, timezone, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-prod")

# セッションをブラウザを閉じても保持する（デフォルト30日、環境変数で変更可）
_session_days = int(os.environ.get("SESSION_DAYS", "30"))
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=_session_days)
app.config["SESSION_COOKIE_HTTPONLY"]    = True   # JS からクッキーを読めないようにする
app.config["SESSION_COOKIE_SAMESITE"]   = "Lax"  # CSRF 軽減
# HTTPS 環境では Secure フラグを有効化（本番用）
if os.environ.get("FLASK_ENV") == "production" or os.environ.get("SESSION_COOKIE_SECURE"):
    app.config["SESSION_COOKIE_SECURE"] = True

SAVE_FILE  = os.path.join(os.path.expanduser("~"), ".sticky_kanban.json")
USERS_FILE = os.path.join(os.path.expanduser("~"), ".sticky_kanban_users.json")
LOG_FILE   = os.path.join(os.path.expanduser("~"), ".sticky_kanban_logs.json")

COL_LABEL = {"todo": "未着手", "wip": "作業中", "done": "完了", "milestone": "マイルストーン"}


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


# ── 操作ログ ─────────────────────────────────────────────────────────────────

def load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def append_log(action, detail, entity_id="", entity_title=""):
    username     = session.get("username", "")
    display_name = session.get("display_name", "") or username or "匿名"
    entry = {
        "id":           str(uuid.uuid4())[:8],
        "ts":           datetime.now(timezone.utc).isoformat(),
        "username":     username,
        "display_name": display_name,
        "action":       action,
        "detail":       detail,
        "entity_id":    entity_id,
        "entity_title": entity_title,
    }
    logs = load_logs()
    logs.append(entry)
    if len(logs) > 500:
        logs = logs[-500:]
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


# ── 起動時シードユーザー ──────────────────────────────────────────────────────
# INIT_USERNAME / INIT_PASSWORD 環境変数が設定されている場合、
# 起動時にそのユーザーを作成する（既存の場合はスキップ）。
# デプロイ後にファイルストレージが消えても必ずログインできるようにするため。

def _ensure_seed_user():
    username     = os.environ.get("INIT_USERNAME", "").strip()
    password     = os.environ.get("INIT_PASSWORD", "").strip()
    display_name = os.environ.get("INIT_DISPLAY_NAME", "").strip()
    if not username or not password:
        return
    if not find_user(username):
        create_user(username, display_name or username, password)

_ensure_seed_user()


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
            session.permanent       = True
            session["user_id"]      = user["id"]
            session["username"]     = user["username"]
            session["display_name"] = user.get("display_name", username)
            append_log("login", f"ログイン: {user.get('display_name', username)}")
            return redirect(url_for("index") + "?view=mytasks")
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
            session.permanent       = True
            session["user_id"]      = user["id"]
            session["username"]     = user["username"]
            session["display_name"] = user.get("display_name", username)
            return redirect(url_for("index") + "?view=mytasks")

    return render_template("login.html", mode="register", error=error)


@app.route("/logout")
def logout():
    append_log("logout", f"ログアウト: {session.get('display_name', session.get('username', ''))}")
    session.clear()
    return redirect(url_for("index"))


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    return jsonify(load_tasks())


@app.route("/api/tasks/reassign", methods=["POST"])
def reassign_tasks():
    data = request.get_json()
    from_val = data.get("from", "")
    to_val   = data.get("to", "")
    if to_val is None:
        return jsonify({"error": "to is required"}), 400

    supabase = _get_supabase()
    if supabase:
        try:
            res = supabase.table("tasks").update({"assignee": to_val}).eq("assignee", from_val).execute()
            count = len(res.data or [])
            append_log("task_reassign", f"担当者「{from_val}」→「{to_val}」に振り替え ({count}件)")
            return jsonify({"updated": count})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    tasks_data = _file_load()
    count = 0
    for t in tasks_data:
        if t.get("assignee", "") == from_val:
            t["assignee"] = to_val
            count += 1
    _file_save(tasks_data)
    append_log("task_reassign", f"担当者「{from_val}」→「{to_val}」に振り替え ({count}件)")
    return jsonify({"updated": count})


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


@app.route("/api/users/<username>", methods=["DELETE"])
def delete_user(username):
    supabase = _get_supabase()
    if supabase:
        try:
            supabase.table("users").delete().eq("username", username).execute()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    users = _users_file_load()
    users = [u for u in users if u.get("username") != username]
    _users_file_save(users)
    return jsonify({"ok": True})

@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json()
    supabase = _get_supabase()
    if supabase:
        try:
            payload = {k: v for k, v in data.items() if v is not None and str(v).strip() != ""}
            payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
            res = supabase.table("tasks").insert(payload).execute()
            result = res.data[0] if res.data else payload
            title = result.get("title", "")
            append_log("task_create", f"タスク「{title}」を作成", result.get("id", ""), title)
            return jsonify(result), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    task = _create_task_file(data)
    title = task.get("title", "")
    append_log("task_create", f"タスク「{title}」を作成", task.get("id", ""), title)
    return jsonify(task), 201


@app.route("/api/tasks/<task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.get_json()
    supabase = _get_supabase()
    if supabase:
        try:
            res = supabase.table("tasks").update(data).eq("id", task_id).execute()
            result = res.data[0] if res.data else data
            title = result.get("title", "")
            if "column" in data:
                col = COL_LABEL.get(data["column"], data["column"])
                append_log("task_move", f"「{title}」を「{col}」に移動", task_id, title)
            else:
                append_log("task_update", f"タスク「{title}」を更新", task_id, title)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    task = _update_task_file(task_id, data)
    if task is None:
        return jsonify({"error": "Not found"}), 404
    title = task.get("title", "")
    if "column" in data:
        col = COL_LABEL.get(data["column"], data["column"])
        append_log("task_move", f"「{title}」を「{col}」に移動", task_id, title)
    else:
        append_log("task_update", f"タスク「{title}」を更新", task_id, title)
    return jsonify(task)


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    # タイトルをログ用に事前取得
    all_tasks = load_tasks()
    task_title = next((t.get("title", "") for t in all_tasks if t.get("id") == task_id), "")

    supabase = _get_supabase()
    if supabase:
        try:
            supabase.table("tasks").delete().eq("id", task_id).execute()
            append_log("task_delete", f"タスク「{task_title}」を削除", task_id, task_title)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    _delete_task_file(task_id)
    append_log("task_delete", f"タスク「{task_title}」を削除", task_id, task_title)
    return jsonify({"ok": True})


# ── Aerial lift ストレージ ────────────────────────────────────────────────────

LIFT_SAVE_FILE = os.path.join(os.path.expanduser("~"), ".aerial_lifts.json")


def load_lifts():
    if not os.path.exists(LIFT_SAVE_FILE):
        return _get_sample_lifts()
    try:
        with open(LIFT_SAVE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _get_sample_lifts()


def save_lifts(lifts):
    with open(LIFT_SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(lifts, f, ensure_ascii=False, indent=2)


def _get_sample_lifts():
    colors = [
        "#FFD166","#EF476F","#06D6A0","#118AB2","#FFB347",
        "#C77DFF","#F72585","#4CC9F0","#80ED99",
    ]
    # 18台: 1F・2Fは3台、3F〜8Fは2台
    assignment = []
    for f in range(1, 9):
        assignment.extend([f] * (3 if f <= 2 else 2))
    lifts = []
    for i, floor in enumerate(assignment, start=1):
        lifts.append({
            "id":       str(uuid.uuid4())[:8],
            "name":     f"高所作業車 {i:02d}",
            "floor":    floor,
            "color":    colors[(i - 1) % len(colors)],
            "operator": "",
            "note":     "",
        })
    save_lifts(lifts)
    return lifts


# ── Aerial lift API ───────────────────────────────────────────────────────────

@app.route("/api/lifts", methods=["GET"])
def get_lifts():
    return jsonify(load_lifts())


@app.route("/api/lifts", methods=["POST"])
def create_lift():
    data = request.get_json()
    lift = {
        "id":       str(uuid.uuid4())[:8],
        "name":     data.get("name", ""),
        "floor":    int(data.get("floor", 1)),
        "color":    data.get("color", "#FFD166"),
        "operator": data.get("operator", ""),
        "note":     data.get("note", ""),
    }
    lifts = load_lifts()
    lifts.append(lift)
    save_lifts(lifts)
    append_log("lift_create", f"高所作業車「{lift['name']}」を{lift['floor']}Fに追加", lift["id"], lift["name"])
    return jsonify(lift), 201


@app.route("/api/lifts/<lift_id>", methods=["PUT"])
def update_lift(lift_id):
    data = request.get_json()
    lifts = load_lifts()
    old_floor = next((l.get("floor") for l in lifts if l["id"] == lift_id), None)
    for lift in lifts:
        if lift["id"] == lift_id:
            for k, v in data.items():
                if k != "id":
                    lift[k] = v
            save_lifts(lifts)
            name = lift.get("name", "")
            if "floor" in data and data["floor"] != old_floor:
                append_log("lift_move", f"高所作業車「{name}」を{old_floor}F→{lift['floor']}Fに移動", lift_id, name)
            else:
                append_log("lift_update", f"高所作業車「{name}」を更新", lift_id, name)
            return jsonify(lift)
    return jsonify({"error": "Not found"}), 404


@app.route("/api/lifts/<lift_id>", methods=["DELETE"])
def delete_lift(lift_id):
    lifts = load_lifts()
    target = next((l for l in lifts if l["id"] == lift_id), None)
    lifts = [l for l in lifts if l["id"] != lift_id]
    save_lifts(lifts)
    if target:
        name = target.get("name", "")
        append_log("lift_delete", f"高所作業車「{name}」を削除", lift_id, name)
    return jsonify({"ok": True})


@app.route("/api/logs", methods=["GET"])
def get_logs():
    if "username" not in session:
        return jsonify({"error": "ログインが必要です"}), 401
    logs = list(reversed(load_logs()))  # 新しい順
    return jsonify(logs)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
