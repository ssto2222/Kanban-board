import streamlit as st
from datetime import date, datetime

from db.tasks import create_task, update_task, delete_task
from utils.helpers import dt_input, color_picker_with_swatches


@st.dialog("タスク", width="small")
def task_dialog(task: dict | None = None) -> None:
    """タスク作成・編集・削除ダイアログ。"""
    is_edit = task is not None
    task_id = task["id"] if is_edit else "new"

    # タスクが切り替わったときだけカラー状態をリセット
    if st.session_state.get("_dlg_task_id") != task_id:
        for k in list(st.session_state.keys()):
            if k.startswith("dlg_"):
                st.session_state.pop(k, None)
        st.session_state["dlg_color"]    = task["color"] if is_edit else "#FFD166"
        st.session_state["_dlg_task_id"] = task_id

    # ── フォームフィールド ──────────────────────────────────────────────
    title    = st.text_input("タスク名 *", value=task["title"]    if is_edit else "")
    assignee = st.text_input("担当者",     value=task["assignee"] if is_edit else "")

    dl_val: date | None = None
    if is_edit and task.get("deadline"):
        try:
            dl_val = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
        except Exception:
            pass
    deadline = st.date_input("期限", value=dl_val, format="YYYY-MM-DD")

    note = st.text_input("メモ", value=task.get("note", "") if is_edit else "")

    st.divider()
    started_at  = dt_input("開始日時を設定", task.get("started_at",  "") if is_edit else "", key_prefix="dlg")
    finished_at = dt_input("終了日時を設定", task.get("finished_at", "") if is_edit else "", key_prefix="dlg")
    st.divider()

    color = color_picker_with_swatches("dlg")

    # ── ボタン行 ────────────────────────────────────────────────────────
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
