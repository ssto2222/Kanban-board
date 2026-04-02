import streamlit as st
from config import COLUMNS
from components.card import render_card

def render_kanban(tasks: list[dict]) -> None:
    """
    カンバンボードビュー（Todo / Doing / Done の 3列表示）。
    各カードの色は components/card.py 内で期限に応じて自動判定されます。
    """

    # 保存・更新後のトーストメッセージ表示
    if st.session_state.get("_toast"):
        st.success(st.session_state.pop("_toast"))

    # カンバンの3列レイアウトを作成
    cols = st.columns(3, gap="medium")

    for i, col_def in enumerate(COLUMNS):
        with cols[i]:
            # 現在のカラムに属するタスクをフィルタリング
            col_tasks = [t for t in tasks if t.get("column") == col_def["key"]]
            
            # カラムヘッダー（色付きバーとタスク数バッジ）
            st.markdown(
                f'<div class="col-hdr" style="background:{col_def["bg"]}">'
                f'<span>{col_def["label"]}</span>'
                f'<span class="badge">{len(col_tasks)}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # タスクカードの描画
            if not col_tasks:
                # タスクが空の場合のプレースホルダー
                st.markdown(
                    '<div style="text-align:center; color:#999; padding:20px; '
                    'border:1px dashed #ccc; border-radius:10px; margin-top:10px; font-size:0.9em;">'
                    'タスクなし</div>', 
                    unsafe_allow_html=True
                )
            else:
                for task in col_tasks:
                    # render_card 内部で get_priority_color が走り、
                    # 期限切れ=赤、間近=橙、その他=元の色 で描画されます
                    render_card(task, i)
