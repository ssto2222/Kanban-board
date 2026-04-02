import streamlit as st
from datetime import date, datetime

from config import COLUMNS, COL_KEYS
from db.tasks import create_task, load_tasks
from utils.helpers import dt_input, color_picker_with_swatches


def render_new_task() -> None:
    st.markdown("## ➕ 新規タスク / 🔷 マイルストーン")

    # フォームのリセット管理用バージョン
    fv = st.session_state.get("nt_form_ver", 0)

    # 既存の担当者リストを取得（重複排除・ソート）
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
        help="チェックすると、期間入力が無効になり、タイムライン上では特定の日の節目として表示されます。"
    )

    if is_milestone:
        st.info("🔷 マイルストーンモード: 期限（実施日）を1日選んでください。")

    # ── 2. 担当者入力 (選択 + 直接編集) ──────────────────────────────────
    st.markdown("##### 👤 担当者設定")
    c1, c2 = st.columns([0.4, 0.6])
    with c1:
        selected_assignee = st.selectbox(
            "既存から選択", 
            options=["(新規入力)"] + existing_assignees, 
            key=f"nt_as_sel_{fv}"
        )
    with c2:
        # selectboxの選択内容を初期値(value)にする。新規入力なら空、選んだらその名前。
        default_name = "" if selected_assignee == "(新規入力)" else selected_assignee
        assignee = st.text_input(
            "担当者名 (直接編集・追記可)", 
            value=default_name, 
            key=f"nt_as_txt_{fv}",
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

    # ── 4. 作業期間 (マイルストーン時は無効化) ──────────────────────────
    st.divider()
    
    # マイルストーンなら disabled=True。
    # さらに、is_milestoneがTrueの間は値を強制的に空文字にする
    if is_milestone:
        st.caption("ℹ️ マイルストーンは期間を持ちません（期限日が実施日となります）")
        started_at = ""
        finished_at = ""
        # 表示だけグレーアウトさせる
        dt_input("開始日時", "", key_prefix=f"nt_{fv}_s_dis", disabled=True)
        dt_input("終了日時", "", key_prefix=f"nt_{fv}_f_dis", disabled=True)
    else:
        st.caption("作業期間を設定する場合（タイムラインにバーで表示されます）")
        started_at  = dt_input("開始日時", "", key_prefix=f"nt_{fv}_s")
        finished_at = dt_input("終了日時", "", key_prefix=f"nt_{fv}_f")

    st.divider()
    
    # ── 5. カラー選択と登録ボタン (コンテナで保護) ───────────────────────
    # カラーピッカーのfragmentによる再描画からボタン消失を守るためのコンテナ
    footer_container = st.container()
    
    with footer_container:
        # デフォルトカラーの切り替え
        default_color = "#E94560" if is_milestone else "#FFD166"
        
        # カラーピッカー呼び出し (fragment)
        color_picker_with_swatches(f"nt_{fv}", default_color=default_color)

        st.write("") # 縦の余白
        
        # 登録ボタン
        if st.button("この内容で登録する", type="primary", use_container_width=True, key=f"nt_submit_btn_{fv}"):
            # --- バリデーション ---
            if not title.strip():
                st.error("項目名を入力してください")
                return

            # 日時の整合性チェック (通常タスクのみ)
            if not is_milestone and finished_at:
                try:
                    f_dt = datetime.strptime(finished_at, "%Y-%m-%d %H:%M")
                    # 終了日時が期限日を超えていないか
                    if deadline and f_dt.date() > deadline:
                        st.error(f"❌ 終了日時は期限（{deadline}）以前に設定してください")
                        return
                    # 開始が終了より前か
                    if started_at:
                        s_dt = datetime.strptime(started_at, "%Y-%m-%d %H:%M")
                        if s_dt > f_dt:
                            st.error("❌ 開始日時は終了日時より前に設定してください")
                            return
                except ValueError:
                    pass

            # --- データの構築 ---
            # マイルストーンならタイトルとメモに識別子を付与（タイムライン側での判定用）
            final_title = f"🔷 {title.strip()}" if is_milestone else title.strip()
            final_note  = f"[MS] {note.strip()}" if is_milestone else note.strip()
            
            # カラーはセッションステートから取得、なければデフォルト
            color = st.session_state.get(f"nt_{fv}_color_val", default_color)

            # DB登録処理
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
                st.error(f"登録エラー: {str(e)}")
                return

            # 状態リセットと画面遷移
            _reset_form_state(fv)
            st.session_state["_toast"] = f"「{final_title}」を追加しました"
            st.session_state.page = "kanban"
            st.rerun()


def _reset_form_state(current_ver: int) -> None:
    """フォームの各ウィジェットをクリアするためにバージョンを上げ、ステートを削除する"""
    st.session_state["nt_form_ver"] = current_ver + 1
    for k in list(st.session_state.keys()):
        if k.startswith("nt_"):
            st.session_state.pop(k, None)
