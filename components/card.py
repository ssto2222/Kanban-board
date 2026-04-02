import streamlit as st
import html as html_mod
from config import COLUMNS, COL_META
from utils.helpers import darken, deadline_html, get_priority_color


def render_card(task: dict, col_idx: int, show_status: bool = False) -> None:
    """
    タスクカードを描画する。
    タイトルを常時表示、Expanderのラベルに期限を表示。
    """
    # 循環インポート回避
    from components.dialog import task_dialog

    # ── 1. 色と基本情報の確定 ──
    original_color = task.get("color", "#FFD166")
    current_status = task.get("column", "todo")
    deadline_val = task.get("deadline", "")
    # 期限による自動色上書き（期限切れは赤など）
    c = get_priority_color(deadline_val, original_color, column=current_status)
    
    # カラム情報
    col_def = COL_META.get(current_status, COLUMNS[0])
    title = task.get("title", "無題")
    assignee = task.get("assignee") or "未設定"
    task_id = task.get("id")

    # ── 2. カード外枠コンテナ ──
    with st.container(border=True):
        
        # ── 3. ヘッダー行（タイトル + メニュー） ──
        h_left, h_right = st.columns([0.85, 0.15])
        
        with h_left:
            st.markdown(f"**{title}**")
            # 優先度/期限状態を示すカラーバー
            st.markdown(
                f'<div style="height:3px; background:{c}; width:40px; border-radius:2px; margin-top:-5px;"></div>',
                unsafe_allow_html=True
            )

        with h_right:
            with st.popover("⋮", help="メニュー"):
                if st.button("📝 編集", key=f"btn_edit_{task_id}_{col_idx}", use_container_width=True):
                    task_dialog(task)
                
                if st.button("🗑️ 削除", key=f"btn_del_{task_id}_{col_idx}", use_container_width=True):
                    from db.tasks import delete_task
                    delete_task(task_id)
                    st.rerun()

        # ── 4. 折りたたみ詳細部分（Expander） ──
        # ラベルに期限を表示（プレーンテキストで表示）
        exp_label = f"⏳ 期限: {deadline_val if deadline_val else '未設定'}"
        with st.expander(exp_label, expanded=False):
            
            # 開いた時に最初に見える情報（担当者とカラー期限バッジ）
            st.markdown(f"**👤 担当者:** {html_mod.escape(assignee)}")
            

            # ステータス表示（担当者別ビューなどの場合）
            if show_status:
                st.markdown(
                    f'<div style="margin-top:8px;"><span class="status-pill" style="background:{col_def["bg"]}; color:white; padding:2px 8px; border-radius:10px; font-size:0.8em;">'
                    f'{col_def["label"]}</span></div>', 
                    unsafe_allow_html=True
                )
            
            # 期間表示
            if task.get("started_at") or task.get("finished_at"):
                st.markdown(
                    f'<div style="font-size:0.85em; color:#666; margin-top:8px;">'
                    f'🕑 {task.get("started_at", "-")} ～ {task.get("finished_at", "-")}</div>',
                    unsafe_allow_html=True
                )

            # メモ
            if task.get("note"):
                st.markdown(
                    f'<div style="background:rgba(0,0,0,0.05); padding:8px; border-radius:5px; font-size:0.9em; margin-top:8px; border-left:3px solid {c};">'
                    f'{html_mod.escape(task["note"])}</div>',
                    unsafe_allow_html=True
                )
