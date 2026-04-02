import streamlit as st
import os

from config import NAV_PAGES, COMING_SOON
from db.tasks import load_tasks
from views import render_kanban, render_assignee, render_new_task, render_timeline

# ── ページ設定 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StickyKanban",
    page_icon="🗒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── グローバルCSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 背景・サイドバーの基本デザイン */
[data-testid="stAppViewContainer"] { background: #1a1a2e; }
[data-testid="stHeader"]           { background: transparent; }
[data-testid="stSidebar"] {
    background: #16213e;
    border-right: 1px solid #2a2a4a;
}

/* カンバン・カードのデザイン */
.col-hdr {
    border-radius: 8px; padding: 10px 14px;
    color: #fff; font-weight: 700; font-size: 14px;
    margin-bottom: 8px;
    display: flex; justify-content: space-between; align-items: center;
}
.kcard {
    border-radius: 10px 10px 0 0;
    box-shadow: 2px 2px 6px rgba(0,0,0,.45);
    overflow: hidden;
}
.kcard-top  { padding: 7px 10px; font-weight: 700; font-size: 13px; color: #111; }
.kcard-body { padding: 4px 10px 8px; font-size: 11px; color: #333; line-height: 1.6; }

/* ── 編集ボタンをカード底部に融合 ── */
div[data-testid="stButton"][data-key^="e_"] {
    margin-top: -2px;
    margin-bottom: 8px;
}
div[data-testid="stButton"][data-key^="e_"] > button {
    background: rgba(0,0,0,.18) !important;
    border: none !important;
    border-radius: 0 0 10px 10px !important;
    color: #555 !important;
    font-size: 10px !important;
    padding: 2px 8px 5px !important;
    height: 22px !important;
    min-height: 22px !important;
    box-shadow: 2px 3px 6px rgba(0,0,0,.35) !important;
    transition: background .15s, color .15s;
}
div[data-testid="stButton"][data-key^="e_"] > button:hover {
    background: rgba(0,0,0,.32) !important;
    color: #111 !important;
}

/* ── 期限カラー ── */
.dl-ok      { color: #1a7a40; }
.dl-warn    { color: #a05a00; }
.dl-overdue { color: #b02020; }

/* ── 担当者別ビュー ── */
.assignee-hdr {
    background: #16213e; border-left: 4px solid #e94560;
    border-radius: 0 8px 8px 0; padding: 10px 16px; margin-bottom: 10px;
    font-weight: 700; font-size: 15px; color: #eaeaea;
}
</style>
""", unsafe_allow_html=True)

# ── セッション初期化 ──────────────────────────────────────────────────────────
# 担当者別 (assignee) を初期ページに設定
if "page" not in st.session_state:
    st.session_state.page = "assignee"

# ── サイドバー ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗒 StickyKanban")
    st.divider()

    st.caption("メニュー")
    for label, key in NAV_PAGES:
        is_active = st.session_state.page == key
        if st.button(
            label,
            key=f"nav_{key}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            # ページ遷移時に新規タスクのフォーム状態をリセット
            if st.session_state.page == "new_task" and key != "new_task":
                for k in list(st.session_state.keys()):
                    if k.startswith("nt_"):
                        st.session_state.pop(k, None)
            st.session_state.page = key
            st.rerun()

    st.divider()
    st.caption("今後追加予定")
    for item in COMING_SOON:
        st.markdown(f'<div style="color:#9a9ab0;padding:3px 0;font-size:13px">{item}</div>', unsafe_allow_html=True)

    st.divider()
    st.caption("v1.0.0")

# ── メインコンテンツ ──────────────────────────────────────────────────────────
page = st.session_state.page

if page in ("kanban", "assignee", "timeline"):
    try:
        tasks = load_tasks()
    except Exception as e:
        st.error(str(e))
        st.info("Herokuの環境変数または `.streamlit/secrets.toml` を確認してください。")
        st.stop()

    if page == "timeline":
        render_timeline(tasks)
    else:
        # 検索バー
        search = st.text_input("search", placeholder="🔍 タスク・担当者を検索...", label_visibility="collapsed")
        if search:
            q = search.lower()
            tasks = [t for t in tasks if q in t["title"].lower() or q in (t.get("assignee") or "").lower()]

        if page == "assignee":
            render_assignee(tasks)
        else:
            render_kanban(tasks)

elif page == "new_task":
    render_new_task()
