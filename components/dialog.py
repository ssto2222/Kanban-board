import streamlit as st
from datetime import date, datetime
from db.tasks import create_task, update_task, delete_task
from utils.helpers import dt_input, color_picker_with_swatches

@st.dialog("タスク詳細", width="small")
def task_dialog(task: dict | None = None) -> None:
    """タスク作成・編集・削除ダイアログ。"""
    is_edit = task is not None
    task_id = task["id"] if is_edit else "new"

    # ── セッション状態の初期化（タスク切り替え時のみ） ──
    if st.session_state.get("_current_dlg_id") != task_id:
        st.session_state._current_dlg_id = task_id
        # 色の初期値をセット
        st.session_state["dlg_clr_color_val"] = task.get("color", "#FFD166") if is_edit else "#FFD166"

    # ── 入力フィールド ──
    title = st.text_input("タスク名 *", value=task["title"] if is_edit else "", key="dlg_title")
    assignee = st.text_input("担当者", value=task["assignee"] if is_edit else "", key="dlg_asg")

    dl_default = date.today()
    if is_edit and task.get("deadline"):
        try:
            dl_default = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
        except: pass
    deadline = st.date_input("期限", value=dl_default, key="dlg_deadline")

    st.divider()

    # 期間設定（JST・キー重複回避）
    started_at = dt_input(
        "開始日時", 
        value=task.get("started_at", "") if is_edit else "", 
        key_prefix="dlg_s_input"
    )
    finished_at = dt_input(
        "終了日時", 
        value=task.get("finished_at", "") if is_edit else "", 
        key_prefix="dlg_e_input"
    )

    st.divider()

    # カラー選択（default_colorにセッションの値を渡す）
    color = color_picker_with_swatches(
        "dlg_clr", 
        default_color=st.session_state["dlg_clr_color_val"]
    )

    # ── アクション ──
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("キャンセル", use_container_width=True, key="dlg_cancel"):
            st.rerun()

    with c2:
        label = "更新する" if is_edit else "作成する"
        if st.button(label, type="primary", use_container_width=True, key="dlg_save"):
            if not title.strip():
                st.error("タスク名が必要です")
            else:
                payload = {
                    "title": title.strip(),
                    "assignee": assignee.strip(),
                    "deadline": deadline.strftime("%Y-%m-%d"),
                    "color": color,
                    "started_at": started_at,
                    "finished_at": finished_at
                }
                if is_edit:
                    update_task(task["id"], payload)
                else:
                    create_task({**payload, "column": "todo"})
                st.rerun()

    if is_edit:
        st.write("")
        with st.expander("詳細設定"):
            # color="red" エラーを修正：標準ボタンとして配置
            if st.button("🗑 このタスクを完全に削除", use_container_width=True, key="dlg_delete"):
                delete_task(task["id"])
                st.rerun()
