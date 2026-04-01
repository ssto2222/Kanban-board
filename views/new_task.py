import streamlit as st
from datetime import date

from config import COLUMNS, COL_KEYS
from db.tasks import create_task
from utils.helpers import dt_input, color_picker_with_swatches


def render_new_task() -> None:
    """新規タスク作成ページ（フルページフォーム）。"""
    st.markdown("## ➕ 新規タスク")

    fv = st.session_state.get("nt_form_ver", 0)  # フォームリセット用バージョン

    # ── 基本情報 ────────────────────────────────────────────────────────
    title    = st.text_input("タスク名 *", key=f"nt_title_{fv}")
    assignee = st.text_input("担当者",     key=f"nt_assignee_{fv}")

    col_left, col_right = st.columns(2)
    with col_left:
        deadline = st.date_input(
            "期限", value=None, format="YYYY-MM-DD", key=f"nt_deadline_{fv}",
        )
    with col_right:
        col_label_map = {c["key"]: c["label"] for c in COLUMNS}
        status = st.selectbox(
            "初期ステータス",
            options=COL_KEYS,
            format_func=lambda k: col_label_map[k],
            key=f"nt_status_{fv}",
        )

    note = st.text_input("メモ", key=f"nt_note_{fv}")

    # ── 日時 ────────────────────────────────────────────────────────────
    st.divider()
    started_at  = dt_input("開始日時を設定", "", key_prefix=f"nt_{fv}")
    finished_at = dt_input("終了日時を設定", "", key_prefix=f"nt_{fv}")
    st.divider()

    # ── カラー ──────────────────────────────────────────────────────────
    color = color_picker_with_swatches(f"nt_{fv}")

    # ── 送信 ────────────────────────────────────────────────────────────
    st.write("")
    if st.button("タスクを追加", type="primary", use_container_width=True,
                 key=f"nt_submit_{fv}"):
        if not title.strip():
            st.error("タスク名を入力してください")
            return

        create_task({
            "title":       title.strip(),
            "assignee":    assignee.strip(),
            "deadline":    deadline.strftime("%Y-%m-%d") if deadline else "",
            "column":      status,
            "note":        note.strip(),
            "color":       color,
            "started_at":  started_at,
            "finished_at": finished_at,
        })

        # フォームをリセットしてカンバンへ遷移
        _reset_form_state(fv)
        st.session_state["_toast"] = f"「{title.strip()}」を追加しました"
        st.session_state.page = "kanban"
        st.rerun()


def _reset_form_state(current_ver: int) -> None:
    """nt_ プレフィックスのセッションステートをすべて削除してフォームをリセット。"""
    st.session_state["nt_form_ver"] = current_ver + 1
    for k in list(st.session_state.keys()):
        if k.startswith(f"nt_{current_ver}") or k.startswith("nt_form"):
            st.session_state.pop(k, None)
