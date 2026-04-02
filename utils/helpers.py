import streamlit as st
import html as html_mod
from datetime import datetime, date, timedelta

# ── 日付パース (タイムラインやカード表示に必須) ────────────────────

def parse_dt(s: str) -> datetime | None:
    """様々な形式の日時文字列を datetime オブジェクトに変換する"""
    if not s or s == "None" or s == "":
        return None
    
    # ISO形式 (Tが含まれる) や標準形式に対応するためのクリーニング
    clean_s = str(s).replace("T", " ").replace("Z", "")[:16]
    
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(clean_s, fmt)
        except ValueError:
            continue
    return None

# ── カラー操作 (カードの枠線用) ──────────────────────────────────

def darken(hex_color: str, amount: float = 0.2) -> str:
    """色を指定した割合だけ暗くする"""
    hex_color = str(hex_color).lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    
    try:
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        new_rgb = tuple(max(0, int(c * (1 - amount))) for c in rgb)
        return '#{:02x}{:02x}{:02x}'.format(*new_rgb)
    except:
        return "#444444"

# ── 期限のHTML表示 ─────────────────────────────────────────────

def deadline_html(deadline_str: str) -> str:
    """期限に応じた色のバッジを返す"""
    if not deadline_str or deadline_str == "None":
        return ""
    
    try:
        dt = datetime.strptime(str(deadline_str), "%Y-%m-%d").date()
        today = date.today()
        diff = (dt - today).days

        if diff < 0:
            cls = "dl-overdue" # 赤
        elif diff <= 2:
            cls = "dl-warn"    # オレンジ
        else:
            cls = "dl-ok"      # 緑

        return f'<span class="{cls}">⌛ {deadline_str}</span>'
    except:
        return f'<span>{deadline_str}</span>'

# ── 日時入力 (新規タスク用) ────────────────────────────────────

def dt_input(label: str, value: str = "", key_prefix: str = "") -> str:
    """日付と時刻の入力を組み合わせて文字列で返す"""
    col1, col2 = st.columns(2)
    with col1:
        d = st.date_input(f"{label}日", key=f"{key_prefix}_d")
    with col2:
        t = st.time_input(f"{label}時", value=datetime.now().time(), key=f"{key_prefix}_t")
    
    if d and t:
        return f"{d} {t.strftime('%H:%M')}"
    return ""

# ── カラーピッカー (スウォッチ付き) ─────────────────────────────

def color_picker_with_swatches(key_prefix: str, default_color: str = "#FFD166"):
    """丸型ボタン付きカラーセレクター"""
    val_key = f"{key_prefix}_color_val"
    if val_key not in st.session_state:
        st.session_state[val_key] = default_color

    swatches = ["#FFD166", "#06D6A0", "#118AB2", "#EF476F", "#E94560", "#4ECCA3", "#8E44AD"]
    
    cols = st.columns(len(swatches))
    for i, sw in enumerate(swatches):
        with cols[i]:
            st.markdown(
                f'<div style="background:{sw};width:18px;height:18px;border-radius:50%;border:1px solid #fff;margin:auto;"></div>',
                unsafe_allow_html=True
            )
            if st.button("選", key=f"{key_prefix}_sw_{i}"):
                st.session_state[val_key] = sw
                st.rerun()

    chosen = st.color_picker("色調整", value=st.session_state[val_key], key=f"{key_prefix}_cp")
    st.session_state[val_key] = chosen
    return chosen
