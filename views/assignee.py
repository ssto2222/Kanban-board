import streamlit as st
import html
from config import COLUMNS
from components.card import render_card

def html_escape(s: str) -> str:
    """HTMLエスケープ処理"""
    return html.escape(str(s))

def render_assignee(tasks: list[dict]) -> None:
    """
    担当者別ビュー。
    - 1ステータス内のタスクが6行以上の場合は5行までに制限。
    """
    UNASSIGNED = "👤 未設定 / 全体共通"
    MAX_DISPLAY = 5  # 表示上限設定

    if not tasks:
        st.info("タスクが登録されていません。")
        return

    # 1. 担当者ごとにグループ化
    groups: dict[str, list[dict]] = {}
    for t in tasks:
        assignee = t.get("assignee")
        if not assignee or str(assignee).strip().lower() in ["none", "未設定", "共通", "全体"]:
            key = UNASSIGNED
        else:
            key = assignee
        groups.setdefault(key, []).append(t)

    # 2. 表示順序（未設定を先頭）
    order = sorted(groups.keys(), key=lambda x: "" if x == UNASSIGNED else x)

    # 3. 描画ループ
    for name in order:
        member_tasks = groups[name]
        
        # ヘッダー描画（集計ロジックは簡略化のため省略可、前回のものを流用可能）
        st.markdown(
            f'''
            <div style="background:#262730; padding:10px; border-radius:5px; margin:20px 0 10px 0; border-left:5px solid #4ecca3;">
                <span style="font-weight:bold;">{"❓" if name == UNASSIGNED else "👤"} {html_escape(name)}</span>
                <span style="font-size:0.8em; color:#9a9ab0; margin-left:10px;">全 {len(member_tasks)} 件</span>
            </div>
            ''',
            unsafe_allow_html=True
        )

        # 4. ステータスごとの表示
        sub_cols = st.columns(len(COLUMNS), gap="small")
        for i, col_def in enumerate(COLUMNS):
            with sub_cols[i]:
                col_key = col_def["key"]
                col_tasks = [t for t in member_tasks if t.get("column") == col_key]
                
                # ラベル表示
                st.markdown(f'<div style="text-align:center; font-size:0.8em; color:#888;">{col_def["label"]} ({len(col_tasks)})</div>', unsafe_allow_html=True)
                
                # --- 5行制限のロジック ---
                display_tasks = col_tasks[:MAX_DISPLAY]
                remaining_count = len(col_tasks) - MAX_DISPLAY

                for task in display_tasks:
                    render_card(task, f"{name}-{col_key}")

                if remaining_count > 0:
                    st.button(
                        f"他 {remaining_count} 件を表示...", 
                        key=f"more-{name}-{col_key}",
                        help="詳細画面または担当者別ページで確認してください",
                        use_container_width=True
                    )
        st.divider()
