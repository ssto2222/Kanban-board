import streamlit as st

from config import COLUMNS
from components.card import render_card


def render_assignee(tasks: list[dict]) -> None:
    """担当者別ビュー。担当者ごとにセクションを作り 3列で表示。"""
    UNASSIGNED = "（未割り当て）"

    # 担当者でグループ化
    groups: dict[str, list[dict]] = {}
    for t in tasks:
        key = t.get("assignee") or UNASSIGNED
        groups.setdefault(key, []).append(t)

    # 五十音順、未割り当ては末尾
    order = sorted(groups.keys(), key=lambda x: "\xff" if x == UNASSIGNED else x)

    for name in order:
        member_tasks = groups[name]
        counts = {k: sum(1 for t in member_tasks if t["column"] == k)
                  for k in ("todo", "wip", "done")}

        st.markdown(
            f'<div class="assignee-hdr">'
            f'{"👤" if name != UNASSIGNED else "❓"}&nbsp;{html_escape(name)}'
            f'<span class="sub">'
            f'計&nbsp;{len(member_tasks)}&nbsp;件&nbsp;｜&nbsp;'
            f'待機&nbsp;{counts["todo"]}&nbsp;'
            f'進行&nbsp;{counts["wip"]}&nbsp;'
            f'完了&nbsp;{counts["done"]}'
            f'</span></div>',
            unsafe_allow_html=True,
        )

        sub_cols = st.columns(3, gap="medium")
        for i, col_def in enumerate(COLUMNS):
            with sub_cols[i]:
                col_tasks = [t for t in member_tasks if t["column"] == col_def["key"]]
                st.markdown(
                    f'<div class="status-label">{col_def["label"]} ({len(col_tasks)})</div>',
                    unsafe_allow_html=True,
                )
                for task in col_tasks:
                    render_card(task, i)

        st.divider()


def html_escape(s: str) -> str:
    import html
    return html.escape(s)
