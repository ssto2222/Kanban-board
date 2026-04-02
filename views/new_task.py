import streamlit as st
from datetime import date

from config import COLUMNS, COL_KEYS
from db.tasks import create_task, load_tasks  # load_tasksを追加
from utils.helpers import dt_input, color_picker_with_swatches


def render_new_task() -> None:
    st.markdown("## ➕ 新規タスク / 🔷 マイルストーン")

    fv = st.session_state.get("nt_form_ver", 0)

    # ── 担当者リストの取得 ──
    try:
        all_tasks = load_tasks()
        existing_assignees = sorted(list(set(t.get("assignee") for t in all_tasks if t.get("assignee"))))
    except:
        existing_assignees = []

    # ── 入力フォーム ──
    title = st.text_input("項目名 (タスク名) *", key=f"nt_title_{fv}")

    # マイルストーン設定の追加
    is_milestone = st.checkbox("マイルストーンとして登録 (重要な節目・期日)", key=f"nt_is_ms_{fv}")
    
    if is_milestone:
        st.info("🔷 マイルストーンとして登録されます。期限（実施日）を必ず入力してください。")

    # 担当者選択
    c1, c2 = st.columns([0.4, 0.6])
    with c1:
        selected_assignee = st.selectbox("既存から選択", options=["(新規入力)"] + existing_assignees, key=f"nt_as_sel_{fv}")
    with c2:
        default_val = "" if selected_assignee == "(新規入力)" else selected_assignee
        assignee = st.text_input("担当者名", value=default_val, key=f"nt_as_txt_{fv}")

    col_left, col_right = st.columns(2)
    with col_left:
        deadline = st.date_input("期限 / 実施日 *", value=date.today(), key=f"nt_deadline_{fv}")
    with col_right:
        col_label_map = {c["key"]: c["label"] for c in COLUMNS}
        status = st.selectbox("ステータス", options=COL_KEYS, format_func=lambda k: col_label_map[k], key=f"nt_status_{fv}")

    note = st.text_input("メモ・詳細", key=f"nt_note_{fv}")

    # ── 日時（マイルストーンでない場合のみ重要） ──
    if not is_milestone:
        st.divider()
        st.caption("作業期間を設定する場合（タイムラインにバーで表示されます）")
        started_at  = dt_input("開始日時", "", key_prefix=f"nt_{fv}_s")
        finished_at = dt_input("終了日時", "", key_prefix=f"nt_{fv}_f")
    else:
        # マイルストーンの場合は内部的に空にする
        started_at = None
        finished_at = None

    st.divider()
    # マイルストーン用のデフォルトカラーを設定（例：マゼンタなど目立つ色）
    default_ms_color = "#E94560" if is_milestone else "#FFD166"
    color = color_picker_with_swatches(f"nt_{fv}", default_color=default_ms_color)

    # ── 登録処理 ──
    if st.button("登録する", type="primary", use_container_width=True):
        if not title.strip():
            st.error("項目名を入力してください")
            return

        # マイルストーン用のフラグをnoteやtitleに隠しプロパティとして持たせるか、
        # noteの先頭に [MS] と付与して判別しやすくする（DBのカラム追加なしで対応する場合）
        final_note = f"[MS] {note.strip()}" if is_milestone else note.strip()
        final_title = f"🔷 {title.strip()}" if is_milestone else title.strip()

        create_task({
            "title":       final_title,
            "assignee":    assignee.strip(),
            "deadline":    deadline.strftime("%Y-%m-%d") if deadline else "",
            "column":      status,
            "note":        final_note,
            "color":       color,
            "started_at":  started_at,
            "finished_at": finished_at,
        })

        _reset_form_state(fv)
        st.session_state.page = "assignee"
        st.rerun()

def _reset_form_state(current_ver: int) -> None:
    """nt_ プレフィックスのセッションステートをすべて削除してフォームをリセット。"""
    st.session_state["nt_form_ver"] = current_ver + 1
    # 関連するすべてのキーを削除
    for k in list(st.session_state.keys()):
        if k.startswith("nt_"):
            st.session_state.pop(k, None)
