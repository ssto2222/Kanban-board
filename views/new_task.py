import streamlit as st
from datetime import date, datetime

from config import COLUMNS, COL_KEYS
from db.tasks import create_task, load_tasks
from utils.helpers import dt_input, color_picker_with_swatches


def render_new_task() -> None:
    st.markdown("## ➕ 新規タスク / 🔷 マイルストーン")

    fv = st.session_state.get("nt_form_ver", 0)

    # 既存の担当者リストを取得
    try:
        all_tasks = load_tasks()
        existing_assignees = sorted(list(set(
            t.get("assignee") for t in all_tasks if t.get("assignee")
        )))
    except Exception:
        existing_assignees = []

    # ── 入力フォーム ────────────────────────────────────────────────────
    title = st.text_input("項目名 (タスク名) *", key=f"nt_title_{fv}")

    is_milestone = st.checkbox(
        "マイルストーンとして登録 (重要な節目・期日)", key=f"nt_is_ms_{fv}"
    )
    if is_milestone:
        st.info("🔷 マイルストーンとして登録されます。期限（実施日）を必ず入力してください。")

    # 担当者選択
    c1, c2 = st.columns([0.4, 0.6])
    with c1:
        selected_assignee = st.selectbox(
            "既存から選択", options=["(新規入力)"] + existing_assignees, key=f"nt_as_sel_{fv}"
        )
    with c2:
        default_val = "" if selected_assignee == "(新規入力)" else selected_assignee
        assignee = st.text_input("担当者名", value=default_val, key=f"nt_as_txt_{fv}")

    col_left, col_right = st.columns(2)
    with col_left:
        deadline = st.date_input("期限 / 実施日 *", value=date.today(), key=f"nt_deadline_{fv}")
    with col_right:
        col_label_map = {c["key"]: c["label"] for c in COLUMNS}
        status = st.selectbox(
            "ステータス", options=COL_KEYS,
            format_func=lambda k: col_label_map[k], key=f"nt_status_{fv}",
        )

    note = st.text_input("メモ・詳細", key=f"nt_note_{fv}")

    # ── 作業期間 ────────────────────────────────────────────────────
    st.divider()
    if is_milestone:
        st.caption("ℹ️ マイルストーンのため作業期間は設定できません（期限日が実施日となります）")
    else:
        st.caption("作業期間を設定する場合（タイムラインにバーで表示されます）")

    st.divider()
    
    if is_milestone:
        # マイルストーン時は入力欄を出さず、説明テキストのみ表示
        st.warning("🔷 マイルストーン設定：作業期間は設定できません。")
        # 変数の中身を空にして保存処理に備える
        started_at = ""
        finished_at = ""
    else:
        # 通常タスク時のみ入力欄を表示
        st.caption("作業期間を設定する場合（タイムラインに表示されます）")
        started_at  = dt_input("開始日時", "", key_prefix=f"nt_{fv}_s")
        finished_at = dt_input("終了日時", "", key_prefix=f"nt_{fv}_f")

    st.divider()
    
    # is_milestone が True なら disabled=True になるように設定
    #started_at  = dt_input("開始日時", "", key_prefix=f"nt_{fv}_s", disabled=is_milestone)
    #finished_at = dt_input("終了日時", "", key_prefix=f"nt_{fv}_f", disabled=is_milestone)

    # 🌟 マイルストーン時は強制的に空文字にする（バリデーション用）
    if is_milestone:
        started_at = ""
        finished_at = ""

    st.divider()
    
    # 🌟 フラグメントの挙動を安定させるためにコンテナを使用
    footer_container = st.container()
    
    with footer_container:
        default_ms_color = "#E94560" if is_milestone else "#FFD166"
        color_picker_with_swatches(f"nt_{fv}", default_color=default_ms_color)

        st.write("") 
        
        # ── 登録処理 ────────────────────────────────────────────────────
        if st.button("登録する", type="primary", use_container_width=True, key=f"nt_submit_btn_{fv}"):
            # (以下、登録ロジック)
            if not title.strip():
                st.error("項目名を入力してください")
                return

            # バリデーション：マイルストーン時はスルー、通常時のみチェック
            if not is_milestone and finished_at:
                try:
                    f_dt = datetime.strptime(finished_at, "%Y-%m-%d %H:%M")
                    if deadline and f_dt.date() > deadline:
                        st.error(f"❌ 終了日時は期限（{deadline}）以前に設定してください")
                        return
                    if started_at:
                        s_dt = datetime.strptime(started_at, "%Y-%m-%d %H:%M")
                        if s_dt > f_dt:
                            st.error("❌ 開始日時は終了日時より前に設定してください")
                            return
                except ValueError:
                    pass

            # データの構築
            final_title = f"🔷 {title.strip()}" if is_milestone else title.strip()
            final_note  = f"[MS] {note.strip()}" if is_milestone else note.strip()
            color = st.session_state.get(f"nt_{fv}_color_val", default_ms_color)

            try:
                create_task({
                    "title":       final_title,
                    "assignee":    assignee.strip(),
                    "deadline":    deadline.strftime("%Y-%m-%d") if deadline else "",
                    "column":      status,
                    "note":        final_note,
                    "color":       color,
                    "started_at":  started_at,
                    "finished_at": finished_at,
                })
            except RuntimeError as e:
                st.error(str(e))
                return

            _reset_form_state(fv)
            st.session_state["_toast"] = f"「{final_title}」を追加しました"
            st.session_state.page = "kanban"
            st.rerun()


def _reset_form_state(current_ver: int) -> None:
    st.session_state["nt_form_ver"] = current_ver + 1
    for k in list(st.session_state.keys()):
        if k.startswith("nt_"):
            st.session_state.pop(k, None)
