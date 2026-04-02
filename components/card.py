import streamlit as st
from config import COLUMNS, COL_KEYS, COL_META
from db.tasks import update_task
from utils.helpers import darken, deadline_html, html_mod, get_priority_color

def render_card(task: dict, col_idx: int, show_status: bool = False) -> None:
    """
    付箋カードを描画する。
    期限切れは赤、間近は橙に自動で色を上書きして表示。
    """
    # 循環インポート回避のため dialog は関数内でインポート
    from components.dialog import task_dialog

    # ── 色の決定 (期限による自動上書きロジックを適用) ──
    # DBに保存されている色をベースに、期限の状態に応じて赤や橙を優先する
    original_color = task.get("color", "#FFD166")
    c = get_priority_color(task.get("deadline", ""), original_color)
    
    # カラムのメタ情報取得
    col_def = COL_META.get(task.get("column", "todo"), COLUMNS[0])

    # ── カードHTMLの構築 ──────────────────────────────────────────────────────
    body: list[str] = []

    # ステータス表示（担当者別ビューなどの場合）
    if show_status:
        body.append(
            f'<span class="status-pill" style="background:{col_def["bg"]}">'
            f'{col_def["label"]}</span>'
        )
    
    # 担当者名表示（ステータス表示がOFFのとき）
    if task.get("assignee") and not show_status:
        body.append(f'<div style="margin-bottom:4px;">👤 {html_mod.escape(task["assignee"])}</div>')

    # 期限バッジ (⌛ アイコンと色付きテキスト)
    dl = deadline_html(task.get("deadline", ""))
    if dl:
        body.append(f'<div style="margin-bottom:4px;">{dl}</div>')

    # 期間（開始・終了）
    if task.get("started_at"):
        body.append(f'<div style="font-size:0.85em;">🕐 開始: {html_mod.escape(task["started_at"])}</div>')
    if task.get("finished_at"):
        body.append(f'<div style="font-size:0.85em;">🕑 終了: {html_mod.escape(task["finished_at"])}</div>')
    
    # メモ
    if task.get("note"):
        body.append(f'<div style="color:#555; font-size:0.9em; margin-top:4px; border-top:1px solid rgba(0,0,0,0.1); padding-top:2px;">'
                    f'{html_mod.escape(task["note"])}</div>')

    # HTMLレンダリング
    # kcard-top (タイトルバー) は背景色を少し暗く(darken)して視認性を確保
    st.markdown(
        f'<div class="kcard">'
        f'<div class="kcard-top" style="background:{darken(c, 0.15)}">'
        f'{html_mod.escape(task.get("title", ""))}</div>'
        f'<div class="kcard-body" style="background:{c}">{"".join(body)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── アクションボタン (◀ ✏️ ▶) ──────────────────────────────────────────────
    b_l, b_e, b_r = st.columns(3)

    with b_l:
        # 左へ移動
        if col_idx > 0:
            if st.button("◀", key=f"l_{task['id']}", use_container_width=True):
                update_task(task["id"], {"column": COL_KEYS[col_idx - 1]})
                st.rerun()
        else:
            st.button(" ", key=f"l_off_{task['id']}", disabled=True, use_container_width=True)

    with b_e:
        # 編集ダイアログを開く
        if st.button("✏️", key=f"e_{task['id']}", use_container_width=True):
            task_dialog(task)

    with b_r:
        # 右へ移動
        if col_idx < 2:
            if st.button("▶", key=f"r_{task['id']}", use_container_width=True):
                update_task(task["id"], {"column": COL_KEYS[col_idx + 1]})
                st.rerun()
        else:
            st.button(" ", key=f"r_off_{task['id']}", disabled=True, use_container_width=True)
