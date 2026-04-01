import streamlit as st

from config import COLUMNS
from components.card import render_card


def render_kanban(tasks: list[dict]) -> None:
    """カンバンボードビュー（3列）。"""

    # 保存後の成功メッセージ
    if st.session_state.get("_toast"):
        st.success(st.session_state.pop("_toast"))

    cols = st.columns(3, gap="medium")
    for i, col_def in enumerate(COLUMNS):
        with cols[i]:
            col_tasks = [t for t in tasks if t["column"] == col_def["key"]]
            st.markdown(
                f'<div class="col-hdr" style="background:{col_def["bg"]}">'
                f'<span>{col_def["label"]}</span>'
                f'<span class="badge">{len(col_tasks)}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            for task in col_tasks:
                render_card(task, i)
