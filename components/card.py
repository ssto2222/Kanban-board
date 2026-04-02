import streamlit as st
import html as html_mod
from config import COLUMNS, COL_META
from utils.helpers import darken, deadline_html, get_priority_color


def render_card(task: dict, col_idx: int, show_status: bool = False) -> None:
    """
    タスクカードを描画する。
    タイトルのみを常時表示し、詳細は折りたたみ（Expander）。
    編集・削除は右肩のメニュー（Popover）から実行。
    """
    # 循環インポート回避
    from components.dialog import task_dialog

    # ── 1. 色と基本情報の確定 ──
    original_color = task.get("color", "#FFD166")
    current_status = task.get("column", "todo")
    # 期限による自動色上書き（期限切れは赤など）
    c = get_priority_color(task.get("deadline", ""), original_color, column=current_status)
    
    # カラム情報
    col_def = COL_META.get(current_status, COLUMNS[0])
    title = task.get("title", "無題")
    assignee = task.get("assignee") or "未設定"
    task_id = task.get("id")

    # ── 2. カード外枠コンテナ ──
    # border=True を使うことでカードらしい外観に
    with st.container(border=True):
        
        # ── 3. ヘッダー行（タイトル + メニュー） ──
        # タイトルを左、メニューを右に配置
        h_left, h_right = st.columns([0.85, 0.15])
        
        with h_left:
            # タイトルを表示（マイルストーンアイコン等があればそのまま表示）
            st.markdown(f"**{title}**")
            # 視認性のための細いカラーバー（カード上部）
            st.markdown(
                f'<div style="height:3px; background:{c}; width:40px; border-radius:2px; margin-top:-5px;"></div>',
                unsafe_allow_html=True
            )

        with h_right:
            # 右肩の「・・・」メニュー
            with st.popover("⋮", help="編集・操作"):
                if st.button("📝 編集", key=f"btn_edit_{task_id}_{col_idx}", use_container_width=True):
                    task_dialog(task)
                
                # 削除が必要な場合はここに追加
            

        # ── 4. 折りたたみ詳細部分（Expander） ──
        # ラベルには担当者を表示
        with st.expander(f"👤 {assignee}", expanded=False):
            # ステータス表示（必要時）
            if show_status:
                st.markdown(
                    f'<span class="status-pill" style="background:{col_def["bg"]}; color:white; padding:2px 8px; border-radius:10px; font-size:0.8em;">'
                    f'{col_def["label"]}</span>', 
                    unsafe_allow_html=True
                )
            
            # 期限表示
            dl = deadline_html(task.get("deadline", ""))
            if dl:
                st.markdown(f'<div style="margin: 8px 0;">{dl}</div>', unsafe_allow_html=True)

            # 期間表示
            if task.get("started_at") or task.get("finished_at"):
                st.caption(f"🕑 {task.get('started_at', '未設定')} ～ {task.get('finished_at', '未設定')}")

            # メモ
            if task.get("note"):
                st.markdown(
                    f'<div style="background:rgba(0,0,0,0.05); padding:8px; border-radius:5px; font-size:0.9em; margin-top:8px;">'
                    f'{html_mod.escape(task["note"])}</div>',
                    unsafe_allow_html=True
                )
