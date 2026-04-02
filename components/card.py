import streamlit as st
import html as html_mod
from config import COLUMNS, COL_META
from utils.helpers import darken, deadline_html, get_priority_color


def render_card(task: dict, col_idx: int, show_status: bool = False) -> None:
    """
    タスクカードを描画する。
    タイトルを常時表示、Expanderのラベルに期限を表示。
    外枠線をカスタムCSSで太く設定。
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

    # ── 2. カスタムCSSの定義（枠線を太く） ──
    # border: 2px で標準より強調。border-left でアクセントカラーを付与。
    _CARD_STYLE = f"""
    <style>
    .custom-card {{
        border: 2px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 12px;
        background-color: rgba(255, 255, 255, 0.02);
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }}
    </style>
    """
    
    # ── 3. カード外枠（HTML開始） ──
    st.markdown(_CARD_STYLE + f'<div class="custom-card">', unsafe_allow_html=True)
    
    # ── 4. ヘッダー行（タイトル + メニュー） ──
    h_left, h_right = st.columns([0.82, 0.18])
    
    with h_left:
        st.markdown(f"**{title}**")
        # 優先度/期限状態を示すカラーバー
        st.markdown(
            f'<div style="height:4px; background:{c}; width:45px; border-radius:2px; margin-top:-5px; margin-bottom:8px;"></div>',
            unsafe_allow_html=True
        )

    with h_right:
        with st.popover("⋮", help="操作"):
            if st.button("📝 編集", key=f"btn_edit_{task_id}_{col_idx}", use_container_width=True):
                task_dialog(task)
            
            if st.button("🗑️ 削除", key=f"btn_del_{task_id}_{col_idx}", use_container_width=True):
                from db.tasks import delete_task
                delete_task(task_id)
                st.rerun()

    # ── 5. 折りたたみ詳細部分（Expander） ──
    # ラベルに期限を表示
    exp_label = f"⏳ 期限: {deadline_val if deadline_val else '未設定'}"
    with st.expander(exp_label, expanded=False):
        
        # 1. 担当者を最上部に配置
        st.markdown(f"**👤 担当者:** {html_mod.escape(assignee)}")
        
        # 2. 期限の状態バッジを表示
        dl_html = deadline_html(deadline_val)
        if dl_html:
            st.markdown(f"**📊 状況:** {dl_html}", unsafe_allow_html=True)

        # 3. ステータス表示（必要時）
        if show_status:
            st.markdown(
                f'<div style="margin-top:8px;"><span class="status-pill" style="background:{col_def["bg"]}; color:white; padding:2px 8px; border-radius:10px; font-size:0.8em;">'
                f'{col_def["label"]}</span></div>', 
                unsafe_allow_html=True
            )
        
        # 4. 期間表示
        if task.get("started_at") or task.get("finished_at"):
            st.markdown(
                f'<div style="font-size:0.85em; color:gray; margin-top:10px; padding-left:4px; border-left:2px solid #444;">'
                f'期間: {task.get("started_at", "-")} ～ {task.get("finished_at", "-")}</div>',
                unsafe_allow_html=True
            )

        # 5. メモ
        if task.get("note"):
            st.markdown(
                f'<div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:5px; font-size:0.9em; margin-top:12px; border-left:3px solid {c};">'
                f'{html_mod.escape(task["note"])}</div>',
                unsafe_allow_html=True
            )

    # ── 6. カード外枠（HTML終了） ──
    st.markdown('</div>', unsafe_allow_html=True)
