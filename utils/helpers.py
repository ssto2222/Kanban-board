import streamlit as st
import html as html_mod
from datetime import datetime, date, timedelta, timezone

# ── 日本時間 (JST) ──
JST = timezone(timedelta(hours=9))

def parse_dt(s: str) -> datetime | None:
    if not s or s == "None" or s == "": return None
    clean_s = str(s).replace("T", " ").replace("Z", "")[:16]
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(clean_s, fmt)
            return dt.replace(tzinfo=JST)
        except: continue
    return None

def darken(hex_color: str, amount: float = 0.2) -> str:
    hex_color = str(hex_color).lstrip('#')
    if len(hex_color) == 3: hex_color = ''.join([c*2 for c in hex_color])
    try:
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        new_rgb = tuple(max(0, int(c * (1 - amount))) for c in rgb)
        return '#{:02x}{:02x}{:02x}'.format(*new_rgb)
    except: return "#444444"

def deadline_html(deadline_str: str) -> str:
    if not deadline_str or deadline_str == "None": return ""
    try:
        dt = datetime.strptime(str(deadline_str), "%Y-%m-%d").date()
        today = datetime.now(JST).date()
        diff = (dt - today).days
        cls = "dl-overdue" if diff < 0 else "dl-warn" if diff <= 2 else "dl-ok"
        return f'<span class="{cls}">⌛ {deadline_str}</span>'
    except: return f'<span>{deadline_str}</span>'

def dt_input(label: str, value: str = "", key_prefix: str = "") -> str:
    default_dt = parse_dt(value) or datetime.now(JST)
    col1, col2 = st.columns(2)
    with col1:
        d = st.date_input(f"{label}日", value=default_dt.date(), key=f"{key_prefix}_d")
    with col2:
        t = st.time_input(f"{label}時", value=default_dt.time(), key=f"{key_prefix}_t")
    return f"{d} {t.strftime('%H:%M')}" if d and t else ""

# ── 色設定 (fragment & 強制同期版) ──
@st.fragment
def color_picker_with_swatches(key_prefix: str, default_color: str = "#FFD166"):
    val_key = f"{key_prefix}_color_val"
    
    if val_key not in st.session_state:
        st.session_state[val_key] = default_color

    st.caption("プリセットから選択")
    swatches = ["#FFD166", # 黄 (標準/待機)
        "#FF4B4B", # 赤 (緊急/停止)
        "#FF9F1C", # 橙 (警告/注意)
        "#00D2D3", # ターコイズ (進行中)
        "#1DD1A1", # 緑 (完了/正常)
        "#54a0ff", # 青 (担当者A)
        "#5f27cd"  # 紫 (重要/担当者B)]
    
    cols = st.columns(len(swatches))
    for i, sw in enumerate(swatches):
        with cols[i]:
            is_selected = st.session_state[val_key].upper() == sw.upper()
            border = "2px solid white" if is_selected else "1px solid #555"
            st.markdown(
                f'<div style="background:{sw}; width:18px; height:18px; border-radius:50%; border:{border}; margin:auto;"></div>',
                unsafe_allow_html=True
            )
            # ボタンクリックで色を更新し、このエリアだけ再描画
            if st.button(" ", key=f"{key_prefix}_sw_{i}", use_container_width=True):
                st.session_state[val_key] = sw
                st.rerun(scope="fragment")

    # 🌟 重要：keyに現在の色を含めることで、ピッカーの色を強制的に更新させる
    current_color = st.session_state[val_key]
    chosen = st.color_picker(
        f"カスタム色調整: {current_color}", 
        value=current_color, 
        key=f"{key_prefix}_cp_{current_color}" 
    )
    
    if chosen != st.session_state[val_key]:
        st.session_state[val_key] = chosen
        # ピッカーを直接いじった時も、他のウィジェットを壊さない程度に更新
        st.rerun(scope="fragment")

    return st.session_state[val_key]
