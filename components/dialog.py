import streamlit as st
from db.tasks import create_task, update_task, delete_task
from utils.helpers import dt_input, color_picker_with_swatches

@st.dialog("タスク詳細", width="small")
def task_dialog(task: dict | None = None) -> None:
    is_edit = task is not None
    task_id = task["id"] if is_edit else "new"
    
    # 状態の初期化
    if st.session_state.get("_active_dlg_id") != task_id:
        st.session_state._active_dlg_id = task_id
        st.session_state["dlg_clr_color_val"] = task.get("color", "#FFD166") if is_edit else "#FFD166"

    # 入力項目
    title = st.text_input("タスク名 *", value=task["title"] if is_edit else "", key="dlg_t_in")
    
    # 日時入力 (key_prefixを分ける)
    started_at = dt_input("開始", value=task.get("started_at", "") if is_edit else "", key_prefix="ds")
    finished_at = dt_input("終了", value=task.get("finished_at", "") if is_edit else "", key_prefix="de")

    st.divider()

    # カラー選択 (内部で rerun(scope="fragment") するのでダイアログは閉じない)
    color_picker_with_swatches("dlg_clr", default_color=st.session_state["dlg_clr_color_val"])

    st.divider()

    # 保存ボタン
    if st.button("保存する", type="primary", use_container_width=True):
        # 最終的な色はセッションから取得
        final_color = st.session_state.get("dlg_clr_color_val", "#FFD166")
        
        payload = {
            "title": title.strip(),
            "color": final_color,
            "started_at": started_at,
            "finished_at": finished_at,
            # 他のフィールドも同様に追加
        }

        if is_edit:
            update_task(task["id"], payload)
        else:
            create_task({**payload, "column": "todo"})
        
        # ここで初めてダイアログを閉じるために rerun()
        st.session_state._active_dlg_id = None
        st.rerun()
