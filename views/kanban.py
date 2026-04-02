import streamlit as st
from config import COLUMNS
from components.card import render_card

def render_kanban(tasks: list[dict]) -> None:
    """
    カンバンボードビュー（Todo / Doing / Done の 3列表示）。
    - 各列5件まで表示し、それ以上はボタンで展開。
    """
    MAX_DISPLAY = 5

    # 保存・更新後のトーストメッセージ表示
    if st.session_state.get("_toast"):
        st.toast(st.session_state.pop("_toast"))

    # カンバンの列レイアウトを作成
    cols = st.columns(len(COLUMNS), gap="medium")

    for i, col_def in enumerate(COLUMNS):
        with cols[i]:
            col_key = col_def["key"]
            # 現在のカラムに属するタスクをフィルタリング
            col_tasks = [t for t in tasks if t.get("column") == col_key]
            
            # カラムヘッダー
            st.markdown(
                f'''<div class="col-hdr" style="background:{col_def["bg"]}">
                <span>{col_def["label"]}</span>
                <span class="badge">{len(col_tasks)}</span>
                </div>''',
                unsafe_allow_html=True,
            )

            # タスクなしの表示
            if not col_tasks:
                st.markdown(
                    '<div style="text-align:center; color:#999; padding:20px; '
                    'border:1px dashed #ccc; border-radius:10px; margin-top:10px; font-size:0.9em;">'
                    'タスクなし</div>', 
                    unsafe_allow_html=True
                )
                continue

            # --- 表示制御ロジック ---
            state_key = f"expand_kanban_{col_key}"
            if state_key not in st.session_state:
                st.session_state[state_key] = False

            # 表示するタスクの決定
            if len(col_tasks) > MAX_DISPLAY and not st.session_state[state_key]:
                display_tasks = col_tasks[:MAX_DISPLAY]
                show_more_button = True
            else:
                display_tasks = col_tasks
                show_more_button = False

            # タスクカードの描画
            for task in display_tasks:
                render_card(task, f"kanban-{col_key}")

            # 「もっと見る」ボタン
            if show_more_button:
                if st.button(f"他 {len(col_tasks) - MAX_DISPLAY} 件を表示", key=f"btn_{state_key}", use_container_width=True):
                    st.session_state[state_key] = True
                    st.rerun()
            
            # 展開中に「閉じる」ボタンを表示したい場合（任意）
            elif len(col_tasks) > MAX_DISPLAY and st.session_state[state_key]:
                if st.button("閉じる", key=f"close_{state_key}", use_container_width=True):
                    st.session_state[state_key] = False
                    st.rerun()
