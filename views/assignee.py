import streamlit as st

from config import COLUMNS
from components.card import render_card

# --- 担当者リストを取得する部分 ---
# 全タスクから担当者名のユニークなセットを作成
all_assignees = list(set(t.get("assignee") for t in tasks))

# 🌟 優先順位を決めてソートする 🌟
def assignee_sort_key(name):
    # 未設定(None, 空文字) または "共通" "全体" などのキーワードを最優先(-1)にする
    priority_names = [None, "", "未設定", "共通", "全体"]
    if name in priority_names:
        return (-1, "") # 数値が小さいほど上にくる
    return (0, str(name)) # それ以外は辞書順(あいうえお順)

# カスタムソートを適用
sorted_assignees = sorted(all_assignees, key=assignee_sort_key)

# --- 描画ループ ---
for assignee in sorted_assignees:
    display_name = assignee if assignee else "👤 未設定 / 共通"
    st.subheader(display_name)
    
    # その担当者のタスクだけをフィルタリング
    person_tasks = [t for t in tasks if t.get("assignee") == assignee]
    
    # 完了したものをグレーにするロジックを含めた render_card を呼び出す
    # ... (レンダリング処理)

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
