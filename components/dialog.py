import streamlit as st
from datetime import date, datetime
from db.tasks import create_task, update_task, delete_task
from utils.helpers import dt_input, color_picker_with_swatches

@st.dialog("タスク詳細", width="small")
def task_dialog(task: dict | None = None) -> None:
    """タスク作成・編集・削除ダイアログ。"""
    is_edit = task is not None
    task_id = task["id"] if is_edit else "new"

    # ── セッション状態の初期化（タスクが切り替わったとき） ──
    # これにより、編集モードを開いたときに既存のデータが正しくフォームにセットされます
    if st.session_state.get("_dlg_task_id") != task_id:
        # 古いダイアログ用のセッションキーを掃除
        for k in list(st.session_state.keys()):
            if k.startswith("dlg_"):
                st.session_state.pop(k, None)
        
        # 編集なら既存の値、新規ならデフォルト値をセット
        st.session_state["_dlg_task_id"] = task_id
        # カラーピッカー用の初期値を保持
        st.session_state["dlg_color_val"] = task["color"] if is_edit else "#FFD166"

    # ── フォームフィールド ──────────────────────────────────────────────
    
    # 1. 基本情報
    title = st.text_input("タスク名 *", value=task["title"] if is_edit else "")
    assignee = st.text_input("担当者", value=task["assignee"] if is_edit else "")

    # 2. 期限 (date_input)
    dl_val = date.today()
    if is_edit and task.get("deadline"):
        try:
            # 文字列を date オブジェクトに変換
            dl_val = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
        except Exception:
            pass
    deadline = st.date_input("期限", value=dl_val, format="YYYY-MM-DD")

    # 3. メモ
    note = st.text_area("メモ", value=task.get("note", "") if is_edit else "")

    st.divider()

    # 4. 期間設定 (JST対応・キー重複回避)
    # 既存の値を value 引数として dt_input に渡すことで編集時に反映されます
    started_at = dt_input(
        "開始日時", 
        value=task.get("started_at", "") if is_edit else "", 
        key_prefix="dlg_start"
    )
    
    finished_at = dt_input(
        "終了日時", 
        value=task.get("finished_at", "") if is_edit else "", 
        key_prefix="dlg_end"
    )

    st.divider()

    # 5. カラー選択 (編集時の既存色を反映)
    # 前回のヘルパー修正により、第2引数に既存色を渡すことでデフォルトが決まります
    current_color = task.get("color", "#FFD166") if is_edit else "#FFD166"
    color = color_picker_with_swatches("dlg_clr", default_color=current_color)

    # ── ボタン行 ────────────────────────────────────────────────────────
    st.write("")
    c_cancel, c_save = st.columns(2)

    with c_cancel:
        if st.button("キャンセル", use_container_width=True):
            st.rerun()

    with c_save:
        label = "更新" if is_edit else "保存"
        if st.button(label, type="primary", use_container_width=True):
            if not title.strip():
                st.error("タスク名を入力してください")
                st.stop()
            
            payload = {
                "title":       title.strip(),
                "assignee":    assignee.strip(),
                "deadline":    deadline.strftime("%Y-%m-%d") if deadline else None,
                "color":       color,
                "note":        note.strip(),
                "started_at":  started_at,
                "finished_at": finished_at,
            }

            if is_edit:
                update_task(task["id"], payload)
            else:
                # 新規作成時はデフォルトで todo カラムへ
                create_task({**payload, "column": "todo"})
            
            st.rerun()

    # 削除ボタン
    if is_edit:
        st.write("")
        with st.expander("詳細設定"):
            if st.button("🗑 このタスクを削除", use_container_width=True, type="secondary"):
                delete_task(task["id"])
                st.rerun()
