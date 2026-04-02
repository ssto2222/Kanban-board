import streamlit as st
from datetime import date, datetime

from config import COLUMNS, COL_KEYS
from db.tasks import create_task, load_tasks
from utils.helpers import dt_input, color_picker_with_swatches


def render_new_task() -> None:
    st.markdown("## ➕ 新規タスク / 🔷 マイルストーン")

    # フォームのリセット管理用バージョン
    fv = st.session_state.get("nt_form_ver", 0)

    # 既存の担当者リストを取得
    try:
        all_tasks = load_tasks()
        existing_assignees = sorted(list(set(
            t.get("assignee") for t in all_tasks if t.get("assignee")
        )))
    except Exception:
        existing_assignees = []

    # ── 1. 基本情報入力 ──────────────────────────────────────────────────
    title = st.text_input("項目名 (タスク名) *", key=f"nt_title_{fv}", placeholder="例: デザイン案の作成")

    is_milestone = st.checkbox(
        "マイルストーンとして登録 (重要な節目・期日)", 
        key=f"nt_is_ms_{fv}",
        help="チェックすると期間入力が無効になり、当日のみのイベントとして登録されます。"
    )

    if is_milestone:
        st.info("🔷 マイルストーンモード: 期限（実施日）を1日選んでください。")

    # ── 2. 担当者入力 (連動コールバック) ──────────────────────────────────
    st.markdown("##### 👤 担当者設定")
    
    txt_key = f"nt_as_txt_{fv}"
    sel_key = f"nt_as_sel_{fv}"

    # コールバック関数: セレクトボックスが変わった瞬間にテキスト欄のStateを直接書き換える
    def on_assignee_change():
        chosen = st.session_state[sel_key]
        if chosen != "(新規入力)":
            st.session_state[txt_key] = chosen

    c1, c2 = st.columns([0.4, 0.6])
    with c1:
        selected_assignee = st.selectbox(
            "既存から選択", 
            options=["(新規入力)"] + existing_assignees, 
            key=sel_key,
            on_change=on_assignee_change # ここで連動
        )
    with c2:
        # text_inputの初期値設定はStateに任せ、変数を取得
        assignee = st.text_input(
            "担当者名 (直接編集・追記可)", 
            key=txt_key,
            placeholder="名前を入力"
        )

    # ── 3. 期限とステータス ──────────────────────────────────────────────
    col_left, col_right = st.columns(2)
    with col_left:
        deadline = st.date_input("期限 / 実施日 *", value=date.today(), key=f"nt_deadline_{fv}")
    with col_right:
        col_label_map = {c["key"]: c["label"] for c in COLUMNS}
        status = st.selectbox(
            "ステータス", 
            options=COL_KEYS,
            format_func=lambda k: col_label_map[k], 
            key=f"nt_status_{fv}",
        )

    note = st.text_input("メモ・詳細", key=f"nt_note_{fv}", placeholder="備考など")

    # ── 4. 作業期間 (マイルストーン時は説明のみ) ──────────────────────────
    st.divider()
    
    if is_milestone:
        st.warning("🔷 マイルストーン設定中: 作業期間（開始・終了）は設定できません。")
        started_at = ""
        finished_at = ""
    else:
        st.caption("作業期間を設定する場合（タイムラインにバーで表示されます）")
        started_at  = dt_input("開始日時", "", key_prefix=f"nt_{fv}_s")
        finished_at = dt_input("終了日時", "", key_prefix=f"nt_{fv}_f")

    st.divider()
    
    # ── 5. カラー選択と登録ボタン ───────────────────────────────────────
    footer_container = st.container()
    
    with footer_container:
        default_color = "#E94560" if is_milestone else "#FFD166"
        color_picker_with_swatches(f"nt_{fv}", default_color=default_color)

        st.write("") 
        
        if st.button("この内容で登録する", type="primary", use_container_width=True, key=f"nt_submit_btn_{fv}"):
            if not title.strip():
                st.error("項目名を入力してください")
                return

            # バリデーション
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

            # 登録データの構築
            final_title = f"🔷 {title.strip()}" if is_milestone else title.strip()
            # タイムライン側でマイルストーンとして扱うためのフラグをnote等に含める（必要に応じて）
            final_note  = f"[MS] {note.strip()}" if is_milestone else note.strip()
            
            color = st.session_state.get(f"nt_{fv}_color_val", default_color)

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
                
                # 成功時のリセット
                _reset_form_state(fv)
                st.session_state["_toast"] = f"「{final_title}」を追加しました"
                st.session_state.page = "kanban"
                st.rerun()

            except RuntimeError as e:
                st.error(f"登録エラー: {str(e)}")


def _reset_form_state(current_ver: int) -> None:
    st.session_state["nt_form_ver"] = current_ver + 1
    for k in list(st.session_state.keys()):
        if k.startswith("nt_"):
            st.session_state.pop(k, None)
