import streamlit as st
import html
from config import COLUMNS
from components.card import render_card

def html_escape(s: str) -> str:
    """HTMLエスケープ処理"""
    import html
    return html.escape(str(s))

def render_assignee(tasks: list[dict]) -> None:
    UNASSIGNED = "👤 未設定 / 全体共通"
    MAX_DISPLAY = 3

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

    order = sorted(groups.keys(), key=lambda x: "" if x == UNASSIGNED else x)

    # 2. 描画ループ
    for name in order:
        member_tasks = groups[name]
        
        # ヘッダー (省略)
        st.markdown(f"### {html_escape(name)}")
        # --- ここから追加: カラムヘッダーの表示 ---
        header_cols = st.columns(len(COLUMNS), gap="medium")
        for i, col_def in enumerate(COLUMNS):
          with header_cols[i]:
            col_key = col_def["key"]
            # 現在のカラムに属するタスクをフィルタリング
            col_tasks = [t for t in tasks if t.get("column") == col_key]
            with header_cols[i]:
                # 太字や背景色などでヘッダーっぽく装飾
                st.markdown(
                f'''<div class="col-hdr" style="background:{col_def["bg"]}">
                <span>{col_def["label"]}</span>
                <span class="badge">{len(col_tasks)}</span>
                </div>''',
                unsafe_allow_html=True,
            )
        # ---------------------------------------
        sub_cols = st.columns(len(COLUMNS), gap="medium")
        for i, col_def in enumerate(COLUMNS):
            with sub_cols[i]:
                col_key = col_def["key"]
                col_tasks = [t for t in member_tasks if t.get("column") == col_key]
                
                # --- 表示制御ロジック ---
                # 各列ごとに一意のキーを作成
                state_key = f"expand_{name}_{col_key}"
                
                # 初期状態は「未展開(False)」
                if state_key not in st.session_state:
                    st.session_state[state_key] = False

                # 表示するタスクの切り出し
                if len(col_tasks) > MAX_DISPLAY and not st.session_state[state_key]:
                    display_tasks = col_tasks[:MAX_DISPLAY]
                    has_more = True
                else:
                    display_tasks = col_tasks
                    has_more = False

                # カード描画
                for task in display_tasks:
                    render_card(task, f"{name}-{col_key}")

                # 「もっと見る」ボタンの制御
                if has_more:
                    if st.button(f"他 {len(col_tasks) - MAX_DISPLAY} 件を表示", key=f"btn_{state_key}"):
                        st.session_state[state_key] = True
                        st.rerun() # 状態を反映させるために再実行
                
                # 展開されている場合に「閉じる」ボタンを出す（任意）
                elif len(col_tasks) > MAX_DISPLAY and st.session_state[state_key]:
                    if st.button("閉じる", key=f"close_{state_key}"):
                        st.session_state[state_key] = False
                        st.rerun()
        st.divider()
