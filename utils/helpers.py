import html as html_mod
import streamlit as st
from datetime import date, datetime, time

from config import STICKY_COLORS


# ── 色操作 ────────────────────────────────────────────────────────────────────

def darken(hex_color: str, factor: float = 0.2) -> str:
    h = hex_color.lstrip("#")
    r, g, b = [int(h[i:i+2], 16) for i in (0, 2, 4)]
    return "#{:02x}{:02x}{:02x}".format(
        int(r * (1 - factor)), int(g * (1 - factor)), int(b * (1 - factor))
    )


# ── 期限表示 ──────────────────────────────────────────────────────────────────

def deadline_html(dl: str) -> str:
    if not dl:
        return ""
    try:
        days = (datetime.strptime(dl, "%Y-%m-%d").date() - date.today()).days
    except Exception:
        return f"<div>📅 {html_mod.escape(dl)}</div>"
    if days < 0:
        cls, note = "dl-overdue", f"(期限切れ {abs(days)}日)"
    elif days == 0:
        cls, note = "dl-warn", "(本日期限!)"
    elif days <= 3:
        cls, note = "dl-warn", f"(残り{days}日)"
    else:
        cls, note = "dl-ok", f"(残り{days}日)"
    return f'<div class="{cls}">📅 {html_mod.escape(dl)}&nbsp;{note}</div>'


# ── 日時入力 ──────────────────────────────────────────────────────────────────

def parse_dt(dt_str: str) -> tuple[date | None, time | None]:
    """'YYYY-MM-DD HH:MM' → (date, time)。空文字なら (None, None)。"""
    if not dt_str:
        return None, None
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        return dt.date(), dt.time()
    except Exception:
        return None, None


def dt_input(label: str, existing: str, key_prefix: str = "") -> str:
    """
    チェックボックス + 日付/時刻ピッカー。
    'YYYY-MM-DD HH:MM' または '' を返す。
    key_prefix でウィジェットキーを名前空間化。
    """
    d, t = parse_dt(existing)
    kp = f"{key_prefix}_" if key_prefix else ""
    safe = label.replace(" ", "").replace("/", "")

    enabled = st.checkbox(label, value=bool(d), key=f"{kp}{safe}_chk")
    if enabled:
        c1, c2 = st.columns(2)
        picked_date = c1.date_input(
            "日付", value=d or date.today(), format="YYYY-MM-DD",
            label_visibility="collapsed", key=f"{kp}{safe}_date",
        )
        picked_time = c2.time_input(
            "時刻", value=t or time(9, 0),
            label_visibility="collapsed", key=f"{kp}{safe}_time",
        )
        return f"{picked_date} {picked_time.strftime('%H:%M')}"
    return ""


# ── カラーピッカー + スウォッチ ───────────────────────────────────────────────

def color_picker_with_swatches(key_prefix: str, default_color: str = "#FFD166"):
    """カラーパレット選択。default_color 引数を追加。"""
    st.write("カラー選択")
    
    # プリセットカラー
    swatches = [
        "#FFD166", "#06D6A0", "#118AB2", "#EF476F", 
        "#073B4C", "#E94560", "#4ECCA3"
    ]
    
    # セッションから前回の値を取得、なければ default_color
    current_color = st.session_state.get(f"{key_prefix}_color_val", default_color)
    
    # スウォッチ（色見本）の表示
    cols = st.columns(len(swatches))
    for i, sw in enumerate(swatches):
        with cols[i]:
            if st.button("●", key=f"{key_prefix}_sw_{i}", help=sw):
                st.session_state[f"{key_prefix}_color_val"] = sw
                st.rerun()
                
    # カラーピッカー本体
    chosen = st.color_picker(
        "カスタム色", 
        value=current_color, 
        key=f"{key_prefix}_cp"
    )
    
    # 最終的な色をセッションに保存して返す
    st.session_state[f"{key_prefix}_color_val"] = chosen
    return chosen
