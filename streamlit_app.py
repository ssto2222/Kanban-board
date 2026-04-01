import streamlit as st
from supabase import create_client
import uuid
from datetime import date, datetime, time

# ── Constants ─────────────────────────────────────────────────────────────────

STICKY_COLORS = [
    "#FFD166", "#EF476F", "#06D6A0", "#118AB2", "#FFB347",
    "#C77DFF", "#F72585", "#4CC9F0", "#80ED99",
]

COLUMNS = [
    {"key": "todo", "label": "📋 待機中", "bg": "#0f3460"},
    {"key": "wip",  "label": "⚡ 進行中", "bg": "#533483"},
    {"key": "done", "label": "✅ 完了",   "bg": "#1a6b3c"},
]
COL_KEYS = [c["key"] for c in COLUMNS]

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="StickyKanban",
    page_icon="🗒",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #1a1a2e; }
[data-testid="stHeader"]           { background: transparent; }
.col-hdr {
    border-radius: 8px; padding: 10px 14px;
    color: #fff; font-weight: 700; font-size: 14px;
    margin-bottom: 8px;
    display: flex; justify-content: space-between; align-items: center;
}
.badge {
    background: rgba(255,255,255,.2);
    border-radius: 12px; padding: 2px 9px; font-size: 12px;
}
.kcard {
    border-radius: 10px;
    box-shadow: 2px 3px 8px rgba(0,0,0,.45);
    margin-bottom: 4px; overflow: hidden;
}
.kcard-top  { padding: 7px 10px; font-weight: 700; font-size: 13px; color: #111; }
.kcard-body { padding: 4px 10px 8px; font-size: 11px; color: #333; line-height: 1.6; }
.dl-ok      { color: #1a7a40; }
.dl-warn    { color: #a05a00; }
.dl-overdue { color: #b02020; }
</style>
""", unsafe_allow_html=True)

# ── Supabase ──────────────────────────────────────────────────────────────────

@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def load_tasks() -> list[dict]:
    res = get_supabase().table("tasks").select("*").order("created_at").execute()
    return res.data or []


def create_task(data: dict):
    get_supabase().table("tasks").insert({
        "id":         str(uuid.uuid4()),
        "created_at": datetime.utcnow().isoformat(),
        **data,
    }).execute()


def update_task(task_id: str, data: dict):
    get_supabase().table("tasks").update(data).eq("id", task_id).execute()


def delete_task(task_id: str):
    get_supabase().table("tasks").delete().eq("id", task_id).execute()

# ── Helpers ───────────────────────────────────────────────────────────────────

def darken(hex_color: str, factor: float = 0.2) -> str:
    h = hex_color.lstrip("#")
    r, g, b = [int(h[i:i+2], 16) for i in (0, 2, 4)]
    return "#{:02x}{:02x}{:02x}".format(
        int(r * (1 - factor)), int(g * (1 - factor)), int(b * (1 - factor))
    )


def deadline_html(dl: str) -> str:
    if not dl:
        return ""
    try:
        days = (datetime.strptime(dl, "%Y-%m-%d").date() - date.today()).days
    except Exception:
        return f"<div>📅 {dl}</div>"
    if days < 0:
        cls, note = "dl-overdue", f"(期限切れ {abs(days)}日)"
    elif days == 0:
        cls, note = "dl-warn", "(本日期限!)"
    elif days <= 3:
        cls, note = "dl-warn", f"(残り{days}日)"
    else:
        cls, note = "dl-ok", f"(残り{days}日)"
    return f'<div class="{cls}">📅 {dl}&nbsp;{note}</div>'


def parse_dt(dt_str: str) -> tuple[date | None, time | None]:
    """'YYYY-MM-DD HH:MM' → (date, time). Returns (None, None) if empty."""
    if not dt_str:
        return None, None
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        return dt.date(), dt.time()
    except Exception:
        return None, None


def dt_input(label: str, existing: str) -> str:
    """Checkbox + date/time inputs. Returns 'YYYY-MM-DD HH:MM' or ''."""
    d, t = parse_dt(existing)
    enabled = st.checkbox(label, value=bool(d))
    if enabled:
        c1, c2 = st.columns(2)
        picked_date = c1.date_input("日付", value=d or date.today(),
                                    format="YYYY-MM-DD", label_visibility="collapsed")
        picked_time = c2.time_input("時刻", value=t or time(9, 0),
                                    label_visibility="collapsed")
        return f"{picked_date} {picked_time.strftime('%H:%M')}"
    return ""

# ── Dialog ────────────────────────────────────────────────────────────────────

@st.dialog("タスク", width="small")
def task_dialog(task: dict | None = None):
    is_edit = task is not None

    title    = st.text_input("タスク名 *", value=task["title"]    if is_edit else "")
    assignee = st.text_input("担当者",     value=task["assignee"] if is_edit else "")

    dl_val: date | None = None
    if is_edit and task.get("deadline"):
        try:
            dl_val = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
        except Exception:
            pass
    deadline = st.date_input("期限", value=dl_val, format="YYYY-MM-DD")

    note  = st.text_input("メモ",       value=task["note"]  if is_edit else "")

    st.divider()
    started_at  = dt_input("開始日時を設定",  task.get("started_at",  "") if is_edit else "")
    finished_at = dt_input("終了日時を設定",  task.get("finished_at", "") if is_edit else "")
    st.divider()

    color = st.color_picker("付箋の色", value=task["color"] if is_edit else "#FFD166")

    st.caption("プリセットカラー")
    sw_cols = st.columns(len(STICKY_COLORS))
    for i, c in enumerate(STICKY_COLORS):
        sw_cols[i].markdown(
            f'<div title="{c}" style="background:{c};width:20px;height:20px;'
            f'border-radius:4px;margin:auto"></div>',
            unsafe_allow_html=True,
        )

    st.write("")
    c_cancel, c_save = st.columns(2)

    with c_cancel:
        if st.button("キャンセル", use_container_width=True):
            st.rerun()

    with c_save:
        if st.button("保存", type="primary", use_container_width=True):
            if not title.strip():
                st.error("タスク名を入力してください")
                st.stop()
            payload = {
                "title":       title.strip(),
                "assignee":    assignee.strip(),
                "deadline":    deadline.strftime("%Y-%m-%d") if deadline else "",
                "color":       color,
                "note":        note.strip(),
                "started_at":  started_at,
                "finished_at": finished_at,
            }
            if is_edit:
                update_task(task["id"], payload)
            else:
                create_task({**payload, "column": "todo"})
            st.rerun()

    if is_edit:
        st.divider()
        if st.button("🗑 このタスクを削除", use_container_width=True):
            delete_task(task["id"])
            st.rerun()

# ── Card ──────────────────────────────────────────────────────────────────────

def render_card(task: dict, col_idx: int):
    c = task["color"]
    st.markdown(f"""
    <div class="kcard">
      <div class="kcard-top" style="background:{darken(c)}">{task["title"]}</div>
      <div class="kcard-body" style="background:{c}">
        {"<div>👤 " + task['assignee'] + "</div>" if task.get("assignee") else ""}
        {deadline_html(task.get("deadline", ""))}
        {"<div>🕐 開始: " + task['started_at']  + "</div>" if task.get("started_at")  else ""}
        {"<div>🕑 終了: " + task['finished_at'] + "</div>" if task.get("finished_at") else ""}
        {"<div style='color:#555'>" + task['note'] + "</div>" if task.get("note") else ""}
      </div>
    </div>
    """, unsafe_allow_html=True)

    b_l, b_e, b_r = st.columns(3)

    with b_l:
        if col_idx > 0 and st.button("◀", key=f"l_{task['id']}", use_container_width=True):
            update_task(task["id"], {"column": COL_KEYS[col_idx - 1]})
            st.rerun()

    with b_e:
        if st.button("✏️", key=f"e_{task['id']}", use_container_width=True):
            task_dialog(task)

    with b_r:
        if col_idx < 2 and st.button("▶", key=f"r_{task['id']}", use_container_width=True):
            update_task(task["id"], {"column": COL_KEYS[col_idx + 1]})
            st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────

h_col, btn_col = st.columns([5, 1])
with h_col:
    st.markdown("# 🗒 StickyKanban")
with btn_col:
    st.write("")
    if st.button("＋ 新規タスク", type="primary", use_container_width=True):
        task_dialog()

search = st.text_input(
    "search", placeholder="🔍  タスク・担当者を検索...",
    label_visibility="collapsed",
)

try:
    tasks = load_tasks()
except Exception as e:
    st.error("Supabase への接続に失敗しました。")
    st.code(str(e))
    st.info("`.streamlit/secrets.toml` に `SUPABASE_URL` と `SUPABASE_KEY` を設定してください。")
    st.stop()

if search:
    q = search.lower()
    tasks = [t for t in tasks if q in t["title"].lower() or q in t.get("assignee", "").lower()]

board_cols = st.columns(3, gap="medium")
for i, col_def in enumerate(COLUMNS):
    with board_cols[i]:
        col_tasks = [t for t in tasks if t["column"] == col_def["key"]]
        st.markdown(
            f'<div class="col-hdr" style="background:{col_def["bg"]}">'
            f'<span>{col_def["label"]}</span>'
            f'<span class="badge">{len(col_tasks)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        for task in col_tasks:
            render_card(task, i)
