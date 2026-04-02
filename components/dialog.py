import streamlit as st
from datetime import date, datetime

from config import COL_KEYS, COL_META
from db.tasks import create_task, update_task, delete_task
from utils.helpers import dt_input, color_picker_with_swatches

@st.dialog("タスク詳細", width="small")
def task_dialog(task: dict | None = None) -> None:
    is_edit = task is not None
    task_id = task["id"] if is_edit else "new"

    # タスクが切り替わったときだけ状態をリセット
    if st.session_state.get("_dlg_task_id") != task_id:
        for k in list(st.session_state.keys()):
            if k.startswith("dlg_"):
                st.session_state.pop(k, None)
        initial_color = task["color"] if is_edit else "#FFD166"
        st.session_state["dlg_clr_color_val"] = initial_color
        st.session_state["_dlg_task_id"] = task_id

    # ── ステータス移動（編集時のみ）────────────────────────────────────
    if is_edit:
        col_key = task.get("column", "todo")
        col_idx = COL_KEYS.index(col_key) if col_key in COL_KEYS else 0
        st.caption(f"現在: {COL_META[col_key]['label']}")
        m_l, m_r = st.columns(2)
        with m_l:
            if col_idx > 0:
                prev_label = COL_META[COL_KEYS[col_idx - 1]]["label"]
                if st.button(f"← {prev_label}", key="dlg_mv_l", use_container_width=True):
                    update_task(task["id"], {"column": COL_KEYS[col_idx - 1]})
                    st.rerun()
        with m_r:
            if col_idx < len(COL_KEYS) - 1:
                next_label = COL_META[COL_KEYS[col_idx + 1]]["label"]
                if st.button(f"{next_label} →", key="dlg_mv_r", use_container_width=True):
                    update_task(task["id"], {"column": COL_KEYS[col_idx + 1]})
                    st.rerun()
        st.divider()

    # ── フォームフィールド ──────────────────────────────────────────────
    # マイルストーン判定（タイトルの先頭に🔷があるか）
    raw_title = task["title"] if is_edit else ""
    init_is_ms = raw_title.startswith("🔷")
    # 表示用タイトルからは🔷を一旦消す
    display_title = raw_title.replace("🔷 ", "").replace("🔷", "")

    title = st.text_input("タスク名 *", value=display_title, key="dlg_title")
    
    is_milestone = st.checkbox(
        "マイルストーンとして登録", 
        value=init_is_ms, 
        key="dlg_is_ms",
        help="チェックすると期間入力が無効になります。"
    )

    assignee = st.text_input("担当者", value=task["assignee"] if is_edit else "", key="dlg_asg")

    # 期限設定
    dl_val: date | None = None
    if is_edit and task.get("deadline"):
        try:
            dl_val = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
        except: pass
    deadline = st.date_input("期限", value=dl_val if dl_val else datetime.now().date(), format="YYYY-MM-DD")

    note = st.text_input("メモ", value=task.get("note", "") if is_edit else "", key="dlg_note")

    st.divider()
    
    # ── 期間入力の制御 ──────────────────────────────────────────────────
    if is_milestone:
        st.warning("🔷 マイルストーン設定中のため、作業期間は設定できません。")
        started_at = ""
        finished_at = ""
    else:
        started_at  = dt_input("開始", task.get("started_at",  "") if is_edit else "", key_prefix="ds")
        finished_at = dt_input("終了", task.get("finished_at", "") if is_edit else "", key_prefix="de")
    
    st.divider()

    color_picker_with_swatches(
        "dlg_clr",
        default_color=st.session_state.get("dlg_clr_color_val", "#FFD166"),
    )

    # ── ボタン行 ────────────────────────────────────────────────────────
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("キャンセル", use_container_width=True, key="dlg_cancel"):
            st.rerun()

    with c2:
        if st.button("保存する", type="primary", use_container_width=True, key="dlg_save"):
            if not title.strip():
                st.error("タスク名を入力してください")
                st.stop()
            
            # バリデーション（通常タスクのみ）
            if not is_milestone and finished_at:
                try:
                    f_dt = datetime.strptime(finished_at, "%Y-%m-%d %H:%M")
                    if deadline and f_dt.date() > deadline:
                        st.error(f"❌ 終了日時は期限（{deadline}）以前に設定してください")
                        st.stop()
                    if started_at:
                        s_dt = datetime.strptime(started_at, "%Y-%m-%d %H:%M")
                        if s_dt > f_dt:
                            st.error("❌ 開始日時は終了日時より前に設定してください")
                            st.stop()
                except ValueError:
                    pass

            # タイトルの最終整形
            final_title = f"🔷 {title.strip()}" if is_milestone else title.strip()
            
            payload = {
                "title":       final_title,
                "assignee":    assignee.strip(),
                "deadline":    deadline.strftime("%Y-%m-%d") if deadline else "",
                "color":       st.session_state.get("dlg_clr_color_val", "#FFD166"),
                "note":        note.strip(),
                "started_at":  started_at,
                "finished_at": finished_at,
            }
            try:
                if is_edit:
                    update_task(task["id"], payload)
                else:
                    create_task({**payload, "column": "todo"})
            except RuntimeError as e:
                st.error(str(e))
                st.stop()
            st.rerun()

    if is_edit:
        with st.expander("危険な操作"):
            if st.button("🗑 このタスクを完全に削除", use_container_width=True, key="dlg_del"):
                delete_task(task["id"])
                st.rerun()
