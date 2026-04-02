import streamlit as st
from config import COLUMNS
from components.card import render_card

def render_assignee(tasks: list[dict]) -> None:
    """
    担当者別ビュー。
    - 未設定/共通タスクを最上部に表示。
    - 担当者ごとに「待機・進行・完了」の3列グリッドで表示。
    """
    UNASSIGNED = "👤 未設定 / 全体共通"

    if not tasks:
        st.info("タスクが登録されていません。")
        return

    # 1. 担当者ごとにグループ化
    groups: dict[str, list[dict]] = {}
    for t in tasks:
        # 担当者が空、None、または特定のキーワードの場合は UNASSIGNED にまとめる
        assignee = t.get("assignee")
        if not assignee or assignee in ["", "None", "未設定", "共通", "全体"]:
            key = UNASSIGNED
        else:
            key = assignee
        groups.setdefault(key, []).append(t)

    # 2. 表示順序の決定 (未設定を先頭、他は五十音順)
    # 空文字を最小値（先頭）にするためのカスタムソート
    order = sorted(groups.keys(), key=lambda x: "" if x == UNASSIGNED else x)

    # 3. 描画ループ
    for name in order:
        member_tasks = groups[name]
        
        # 各ステータスの件数集計
        counts = {
            col["key"]: sum(1 for t in member_tasks if t.get("column") == col["key"])
            for col in COLUMNS
        }

        # 担当者ヘッダーの描画
        st.markdown(
            f'''
            <div style="
                background: #262730; 
                padding: 10px 15px; 
                border-radius: 5px; 
                margin: 20px 0 10px 0;
                border-left: 5px solid #4ecca3;
            ">
                <span style="font-size: 1.2em; font-weight: bold;">
                    {"❓" if name == UNASSIGNED else "👤"}&nbsp;{html_escape(name)}
                </span>
                <span style="font-size: 0.85em; color: #9a9ab0; margin-left: 15px;">
                    計 {len(member_tasks)} 件 ｜ 
                    {COLUMNS[0]["label"]} {counts.get(COLUMNS[0]["key"], 0)} ・ 
                    {COLUMNS[1]["label"]} {counts.get(COLUMNS[1]["key"], 0)} ・ 
                    {COLUMNS[2]["label"]} {counts.get(COLUMNS[2]["key"], 0)}
                </span>
            </div>
            ''',
            unsafe_allow_html=True,
        )

        # 4. ステータスごとの3列表示
        sub_cols = st.columns(3, gap="medium")
        for i, col_def in enumerate(COLUMNS):
            with sub_cols[i]:
                col_key = col_def["key"]
                col_tasks = [t for t in member_tasks if t.get("column") == col_key]
                
                # 各列のラベル表示
                st.markdown(
                    f'<div style="text-align:center; font-size:0.8em; color:#666; margin-bottom:8px; font-weight:bold;">'
                    f'{col_def["label"]} ({len(col_tasks)})</div>',
                    unsafe_allow_html=True,
                )
                
                # カードの描画
                for task in col_tasks:
                    # 以前の修正により render_card 内でステータスを見て 
                    # 完了(done)なら自動でグレーになります
                    render_card(task, i)

        st.divider()


def html_escape(s: str) -> str:
    """HTMLエスケープ処理"""
    import html
    return html.escape(str(s))
