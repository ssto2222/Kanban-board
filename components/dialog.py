import streamlit as st
from datetime import date, datetime
from db.tasks import create_task, update_task, delete_task
from utils.helpers import dt_input, color_picker_with_swatches

@st.dialog("タスク詳細", width="small")
def task_dialog(task: dict | None = None) -> None:
    is_edit = task is not None
    task_id = task["id"] if is_edit else "new"

    # ── 状態の固定化 ──
    # ダイアログ内で入力中の値を保持するため、初期化は最小限に
    if "_current_dlg_id" not in st.session_state or st.session_state._current_dlg_id != task_id:
        st.session_state._current_dlg_id = task_id
        st.session_state["dlg_color_val"] = task.get("color", "#FFD166") if is_edit else "#FFD166"

    # 1. 基本入力
    title = st.text_input("タスク名 *", value=task["title"] if is_edit else "", key="dlg_inp_title")
    assignee = st.text_input("担当者", value=task["assignee"] if is_edit else "", key="dlg_inp_asg")

    # 2. 期限
    dl_default = date.today()
    if is_edit and task.get("deadline"):
        try:
            dl_default = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
        except: pass
    deadline = st.date_input("期限", value=dl_default, key="dlg_inp_dl")

    # 3. 期間設定
    s_val = task.get("started_at", "") if is_edit else ""
    e_val = task.get("finished_at", "") if is_edit else ""
    
    started_at = dt_input("開始日時", value=s_val, key_prefix="dlg_s_edit")
    finished_at = dt_input("終了日時", value=e_val, key_prefix="dlg_e_edit")

    st.divider()

    # 4. カラー選択
    # ヘルパー内で rerun を抑制したため、ダイアログが閉じにくくなります
    color = color_picker_with_swatches("dlg_clr", default_color=st.session_state["dlg_color_val"])

    st.divider()

    # 5. アクションボタン
    c1, c2 = st.columns(2)
    with c1:
        # キャンセルは単に閉じるだけ（rerunしない）
        if st.button("閉じる", use_container_width=True, key="dlg_btn_close"):
            st.session_state._current_dlg_id = None # IDリセット
            st.rerun() 

    with c2:
        btn_label = "更新する" if is_edit else "作成する"
        if st.button(btn_label, type="primary", use_container_width=True, key="dlg_btn_save"):
            if not title.strip():
                st.error("タイトルを入力してください")
            else:
                payload = {
                    "title": title.strip(),
                    "assignee": assignee.strip(),
                    "deadline": deadline.strftime("%Y-%m-%d"),
                    "color": color,
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "note": st.session_state.get("dlg_inp_note", "")
                }
                
                if is_edit:
                    update_task(task["id"], payload)
                else:
                    create_task({**payload, "column": "todo"})
                
                # 保存完了後、初めて画面全体を更新してダイアログを閉じる
                st.session_state._current_dlg_id = None
                st.rerun()

    if is_edit:
        with st.expander("危険な操作"):
            if st.button("🗑 タスクを削除", color="red", use_container_width=True, key="dlg_btn_del"):
                delete_task(task["id"])
                st.session_state._current_dlg_id = None
                st.rerun()
