import streamlit as st

from config import COLUMNS, COL_META
from utils.helpers import darken, deadline_html, html_mod


def render_card(task: dict, col_idx: int, show_status: bool = False) -> None:
    """
    付箋カードを描画する。
    show_status=True のとき担当者名を隠してステータスバッジを表示
    （担当者別ビュー用）。
    """
    # 循環インポート回避のため dialog は関数内でインポート
    from components.dialog import task_dialog

    c       = task.get("color", "#FFD166")
    col_def = COL_META.get(task.get("column", "todo"), COLUMNS[0])

    # ── カードHTML ──────────────────────────────────────────────────────
    body: list[str] = []

    if show_status:
        body.append(
            f'<span class="status-pill" style="background:{col_def["bg"]}">'
            f'{col_def["label"]}</span>'
        )
    if task.get("assignee") and not show_status:
        body.append(f'<div>👤 {html_mod.escape(task["assignee"])}</div>')

    dl = deadline_html(task.get("deadline", ""))
    if dl:
        body.append(dl)

    if task.get("started_at"):
        body.append(f'<div>🕐 開始: {html_mod.escape(task["started_at"])}</div>')
    if task.get("finished_at"):
        body.append(f'<div>🕑 終了: {html_mod.escape(task["finished_at"])}</div>')
    if task.get("note"):
        body.append(f'<div style="color:#555">{html_mod.escape(task["note"])}</div>')

    st.markdown(
        f'<div class="kcard">'
        f'<div class="kcard-top" style="background:{darken(c)}">'
        f'{html_mod.escape(task.get("title", ""))}</div>'
        f'<div class="kcard-body" style="background:{c}">{"".join(body)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # カード底部に融合した編集ボタン（クリックでダイアログを開く）
    if st.button("✏ 編集", key=f"e_{task['id']}", use_container_width=True):
        task_dialog(task)
