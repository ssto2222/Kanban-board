import streamlit as st
from datetime import date, datetime
from db.tasks import create_task, update_task, delete_task
from utils.helpers import dt_input, color_picker_with_swatches

@st.dialog("タスク詳細", width="small")
def task_dialog(task: dict | None = None) -> None:
    is_edit = task is not None
    task_id = task["id"] if is_edit else "new"

    # セッションの初期化
    if st.session_state.get("_active_dlg_id") != task_id:
        st.session_state._active_dlg_id = task_id
        st.session_state["dlg_clr_color_val"] = task.get("color", "#FFD166") if is_edit else "#FFD166"

    # 入力項目
    title = st.text_input("タスク名 *", value=task["title"] if is_edit else "", key="dlg_title")
    assignee = st.text_input("担当者", value=task["assignee"] if is_edit else "", key="dlg_asg")
    
    # 期間設定
    started_at = dt_input("開始", value=task.get("started_at", "") if is_edit else "", key_prefix="ds")
    finished_at = dt_input("終了", value=task.get("finished_at", "") if is_edit else "", key_prefix="de")

    st.divider()

    # カラー選択
    # color_picker_with_swatches 内の fragment により、ダイアログを維持したまま色同期が可能
    color_picker_with_swatches("dlg_clr", default_color=st.session_state["dlg_clr_color_val"])

    st.divider()

    # 保存・キャンセル
    c1, c2 = st.columns(2)
    with c1:
        if st.button("キャンセル", use_container_width=True, key="dlg_cancel"):
            st.rerun()

    with c2:
        if st.button("保存する", type="primary", use_container_width=True, key="dlg_save"):
            if not title.strip():
                st.error("タスク名を入力してください")
            else:
                # 最新の色は常にセッションから取得する
                final_color = st.session_state.get("dlg_clr_color_val", "#FFD166")
                
                payload = {
                    "title": title.strip(),
                    "assignee": assignee.strip(),
                    "color": final_color,
                    "started_at": started_at,
                    "finished_at": finished_at
                }
                if is_edit:
                    update_task(task["id"], payload)
                else:
                    create_task({**payload, "column": "todo"})
                
                st.session_state._active_dlg_id = None
                st.rerun()

    if is_edit:
        with st.expander("危険な操作"):
            if st.button("🗑 このタスクを完全に削除", use_container_width=True, key="dlg_del"):
                delete_task(task["id"])
                st.rerun()
