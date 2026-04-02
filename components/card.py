import streamlit as st
import html as html_mod
from config import COLUMNS, COL_META
from utils.helpers import darken, deadline_html, get_priority_color

def render_card(task: dict, col_idx: int, show_status: bool = False) -> None:
    """
    タスクカードを描画。
    カード全体をコンテナで囲み、そのコンテナの枠線をCSSで太く上書きします。
    """
    # 循環インポート回避
    from components.dialog import task_dialog

    # ── 1. 色と基本情報の確定 ──
    original_color = task.get("color", "#FFD166")
    current_status = task.get("column", "todo")
    deadline_val = task.get("deadline", "")
    c = get_priority_color(deadline_val, original_color, column=current_status)
    
    col_def = COL_META.get(current_status, COLUMNS[0])
    title = task.get("title", "無題")
    assignee = task.get("assignee") or "未設定"
    task_id = task.get("id")

    # ── 2. CSSインジェクション ──
    # st.container(border=True) が生成する div (stVerticalBlockBordered) を狙い撃ちして太くします
    st.markdown("""
        <style>
        /* すべてのボーダー付きコンテナの枠線を 2px にし、少し明るくする */
        [data-testid="stVerticalBlockBordered"] {
            border: 2px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 12px !important;
            padding: 15px !important;
            background-color: rgba(255, 255, 255, 0.02);
            margin-bottom: 10px;
        }
        /* カード内の余計な余白をカット */
        [data-testid="stVerticalBlockBordered"] > div {
            gap: 0.5rem !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # ── 3. カード本体 ──
    with st.container(border=True):
        # ヘッダー：タイトルとメニュー
        h_left, h_right = st.columns([0.82, 0.18])
        
        with h_left:
            st.markdown(f"**{title}**")
            st.markdown(
                f'<div style="height:4px; background:{c}; width:45px; border-radius:2px; margin-top:-5px; margin-bottom:10px;"></div>',
                unsafe_allow_html=True
            )

        with h_right:
            with st.popover("⋮"):
                if st.button("📝 編集", key=f"btn_edit_{task_id}_{col_idx}", use_container_width=True):
                    task_dialog(task)
                if st.button("🗑️ 削除", key=f"btn_del_{task_id}_{col_idx}", use_container_width=True):
                    from db.tasks import delete_task
                    delete_task(task_id)
                    st.rerun()

        # アコーディオン（トップに期限）
        exp_label = f"⏳ 期限: {deadline_val if deadline_val else '未設定'}"
        with st.expander(exp_label, expanded=False):
            
            # 担当者
            st.markdown(f"**👤 担当者:** {html_mod.escape(assignee)}")
            
            # ステータス表示
            if show_status:
                st.markdown(
                    f'<div style="margin: 8px 0;"><span style="background:{col_def["bg"]}; color:white; padding:2px 8px; border-radius:10px; font-size:0.8em;">'
                    f'{col_def["label"]}</span></div>', 
                    unsafe_allow_html=True
                )
            
            # 期間
            if task.get("started_at") or task.get("finished_at"):
                st.markdown(
                    f'<div style="font-size:0.85em; color:gray; margin-top:5px;">'
                    f'🕑 {task.get("started_at", "-")} ～ {task.get("finished_at", "-")}</div>',
                    unsafe_allow_html=True
                )

            # メモ
            if task.get("note"):
                st.markdown(
                    f'<div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:5px; font-size:0.9em; margin-top:10px; border-left:3px solid {c};">'
                    f'{html_mod.escape(task["note"])}</div>',
                    unsafe_allow_html=True
                )
