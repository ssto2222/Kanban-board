import streamlit as st
from datetime import datetime, date, time, timedelta, timezone
import html as html_mod

# 日本時間設定
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

def get_priority_color(deadline_str: str, original_color: str, column: str = "todo") -> str:
    """
    タスクの色を決定する。
    1. 完了(done)ステータスなら無条件でグレイ
    2. 未完了なら期限に応じて 赤(切) > 橙(間近) > 元の色
    """
    # 🌟 1. まずステータスをチェック（期限の有無に関わらずグレーにする）
    if column == "done":
        return "#4a4a6a"
    
    # 期限設定がない場合は元の色
    if not deadline_str or deadline_str == "None":
        return original_color

    try:
        dt = datetime.strptime(str(deadline_str), "%Y-%m-%d").date()
        today = datetime.now(JST).date()
        diff = (dt - today).days
    
        if diff < 0:
            return "#FF4B4B"  # 期限切れ：赤
        if diff <= 2:
            return "#FF9F1C"  # 期限間近：橙
        
        return original_color
    except:
        return original_color

def dt_input(label: str, value: str = "", key_prefix: str = "") -> str:
    """日付と時刻の入力。時刻リストを07:00から開始する。"""
    default_dt = parse_dt(value) or datetime.now(JST)
    
    # 7:00 から 翌6:30 までの選択肢を作成
    time_options = []
    for i in range(24):
        h = (7 + i) % 24
        time_options.append(time(h, 0))
        time_options.append(time(h, 30))

    col1, col2 = st.columns(2)
    with col1:
        d = st.date_input(f"{label}日", value=default_dt.date(), key=f"{key_prefix}_d")
    with col2:
        curr_t = default_dt.time().replace(second=0, microsecond=0)
        if curr_t not in time_options:
            time_options.append(curr_t)
            time_options.sort(key=lambda x: (x.hour - 7) % 24)
        
        t = st.selectbox(
            f"{label}時刻", 
            options=time_options,
            index=time_options.index(curr_t),
            format_func=lambda x: x.strftime("%H:%M"),
            key=f"{key_prefix}_t"
        )
    return f"{d} {t.strftime('%H:%M')}" if d and t else ""

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

# カラーピッカー (省略なし)
@st.fragment
def color_picker_with_swatches(key_prefix: str, default_color: str = "#FFD166"):
    val_key = f"{key_prefix}_color_val"

    if val_key not in st.session_state:
        st.session_state[val_key] = default_color

    st.caption("プリセットから選択")
    swatches = [
        "#FFD166",  # 黄（標準/待機）
        "#FF4B4B",  # 赤（緊急/停止）
        "#FF9F1C",  # 橙（警告/注意）
        "#00D2D3",  # ターコイズ（進行中）
        "#1DD1A1",  # 緑（完了/正常）
        "#FF54EB",  # 青（担当者A）
        "#5f27cd",  # 紫（重要/担当者B）
    ]

    cols = st.columns(len(swatches))
    for i, sw in enumerate(swatches):
        with cols[i]:
            if st.button(" ", key=f"{key_prefix}_sw_{i}", help=sw, use_container_width=True):
                st.session_state[val_key] = sw
                st.rerun(scope="fragment")
            st.markdown(f'<div style="background:{sw}; height:5px; margin-top:-10px;"></div>', unsafe_allow_html=True)
    chosen = st.color_picker("カスタム調整", value=st.session_state[val_key], key=f"{key_prefix}_cp_{st.session_state[val_key]}")
    if chosen != st.session_state[val_key]:
        st.session_state[val_key] = chosen
        st.rerun(scope="fragment")
    return st.session_state[val_key]
