import streamlit as st
from datetime import date, datetime
from db.tasks import create_task, update_task, delete_task
from utils.helpers import dt_input, color_picker_with_swatches

@st.dialog("タスク詳細", width="small")
def task_dialog(task: dict | None = None) -> None:
    is_edit = task is not None
    task_id = task["id"] if is_edit else "new"

    # ── ダイアログ内でのID固定 ──
    if "_active_task_id" not in st.session_state or st.session_state._active_task_id != task_id:
        st.session_state._active_task_id = task_id
        # 編集開始時の初期色をセッションに強制セット
        st.session_state["dlg_clr_color_val"] = task.get("color", "#FFD166") if is_edit else "#FFD166"

    # 入力フィールド (keyを固定することでrerunに耐える)
    title = st.text_input("タスク名 *", value=task["title"] if is_edit else "", key="dlg_title")
    assignee = st.text_input("担当者", value=task["assignee"] if is_edit else "", key="dlg_asg")
    
    st.divider()

    # 期間設定
    started_at = dt_input("開始日時", value=task.get("started_at", "") if is_edit else "", key_prefix="dlg_s")
    finished_at = dt_input("終了日時", value=task.get("finished_at", "") if is_edit else "", key_prefix="dlg_e")

    st.divider()

    # ── カラー選択部 ──
    # ここで色を変えると st.rerun() が走るが、このダイアログ関数が再実行されるだけなので閉じない
    color = color_picker_with_swatches("dlg_clr", default_color=st.session_state["dlg_color_val"] if "dlg_color_val" in st.session_state else task.get("color", "#FFD166"))

    st.divider()

    # ── 保存・削除ボタン ──
    c1, c2 = st.columns(2)
    with c1:
        if st.button("キャンセル", use_container_width=True):
            st.session_state._active_task_id = None
            st.rerun()

    with c2:
        if st.button("保存する", type="primary", use_container_width=True):
            if not title.strip():
                st.error("タスク名を入力してください")
            else:
                payload = {
                    "title": title.strip(),
                    "assignee": assignee.strip(),
                    "color": color,
                    "started_at": started_at,
                    "finished_at": finished_at
                }
                if is_edit:
                    update_task(task["id"], payload)
                else:
                    create_task({**payload, "column": "todo"})
                
                st.session_state._active_task_id = None
                st.rerun()
