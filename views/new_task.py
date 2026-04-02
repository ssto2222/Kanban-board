import streamlit as st
from datetime import date

from config import COLUMNS, COL_KEYS
from db.tasks import create_task, load_tasks  # load_tasksを追加
from utils.helpers import dt_input, color_picker_with_swatches


def render_new_task() -> None:
    """新規タスク作成ページ（フルページフォーム）。"""
    st.markdown("## ➕ 新規タスク")

    fv = st.session_state.get("nt_form_ver", 0)  # フォームリセット用バージョン

    # ── 担当者リストの取得 ──────────────────────────────────────────────
    # 既存のタスクからユニークな担当者名を取得
    try:
        all_tasks = load_tasks()
        # Noneを除外し、重複を消してソート
        existing_assignees = sorted(list(set(
            t.get("assignee") for t in all_tasks if t.get("assignee")
        )))
    except:
        existing_assignees = []

    # ── 基本情報 ────────────────────────────────────────────────────────
    title = st.text_input("タスク名 *", key=f"nt_title_{fv}")

    # 担当者入力の改善: 既存リストから選択 or 新規入力
    st.write("担当者")
    c1, c2 = st.columns([0.4, 0.6])
    with c1:
        selected_assignee = st.selectbox(
            "既存から選択",
            options=["(新規入力)"] + existing_assignees,
            key=f"nt_assignee_sel_{fv}"
        )
    with c2:
        # 選択肢が「新規入力」の時だけ入力可能にする、または上書き入力用
        default_val = "" if selected_assignee == "(新規入力)" else selected_assignee
        assignee = st.text_input(
            "担当者名を入力", 
            value=default_val,
            key=f"nt_assignee_text_{fv}",
            placeholder="新しい名前を入力..."
        )

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
    started_at  = dt_input("開始日時を設定", "", key_prefix=f"nt_{fv}_s")
    finished_at = dt_input("終了日時を設定", "", key_prefix=f"nt_{fv}_f")
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
            "assignee":    assignee.strip(), # c2のテキスト入力値を優先使用
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
        # 遷移先を「担当者別」にする場合はここを "assignee" に変更
        st.session_state.page = "assignee" 
        st.rerun()


def _reset_form_state(current_ver: int) -> None:
    """nt_ プレフィックスのセッションステートをすべて削除してフォームをリセット。"""
    st.session_state["nt_form_ver"] = current_ver + 1
    # 関連するすべてのキーを削除
    for k in list(st.session_state.keys()):
        if k.startswith("nt_"):
            st.session_state.pop(k, None)
