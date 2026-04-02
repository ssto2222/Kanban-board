import streamlit as st
import html as html_mod
from datetime import datetime, date, timedelta, timezone

# ── 1. 基本設定 (日本時間 JST) ────────────────────────────────
JST = timezone(timedelta(hours=9))

# ── 2. 日付パース関数 ─────────────────────────────────────────
def parse_dt(s: str) -> datetime | None:
    """様々な形式の文字列を日本時間の datetime オブジェクトに変換"""
    if not s or s == "None" or s == "":
        return None
    
    # ISO形式などのクリーニング (先頭16文字: 分まで)
    clean_s = str(s).replace("T", " ").replace("Z", "")[:16]
    
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(clean_s, fmt)
            return dt.replace(tzinfo=JST)
        except ValueError:
            continue
    return None

# ── 3. カラー操作 (ImportError: darken の解決) ──────────────────
def darken(hex_color: str, amount: float = 0.2) -> str:
    """指定した色を一定割合暗くする (カードの枠線用)"""
    hex_color = str(hex_color).lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    
    try:
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        new_rgb = tuple(max(0, int(c * (1 - amount))) for c in rgb)
        return '#{:02x}{:02x}{:02x}'.format(*new_rgb)
    except:
        return "#444444"

# ── 4. UI用ヘルパー (HTMLバッジ) ──────────────────────────────
def deadline_html(deadline_str: str) -> str:
    """期限に応じたカラーバッジのHTMLを生成"""
    if not deadline_str or deadline_str == "None":
        return ""
    
    try:
        dt = datetime.strptime(str(deadline_str), "%Y-%m-%d").date()
        today = datetime.now(JST).date()
        diff = (dt - today).days

        if diff < 0:
            cls = "dl-overdue" # 期限切れ(赤)
        elif diff <= 2:
            cls = "dl-warn"    # 直前(オレンジ)
        else:
            cls = "dl-ok"      # 余裕(緑)

        return f'<span class="{cls}">⌛ {deadline_str}</span>'
    except:
        return f'<span>{deadline_str}</span>'

# ── 5. 日時入力コンポーネント ─────────────────────────────────
def dt_input(label: str, value: str = "", key_prefix: str = "") -> str:
    """日付と時刻を並べて入力し、結合した文字列を返す"""
    # 既存値があればパース、なければ現在の日本時間
    default_dt = parse_dt(value) or datetime.now(JST)
    
    col1, col2 = st.columns(2)
    with col1:
        d = st.date_input(f"{label}日", value=default_dt.date(), key=f"{key_prefix}_d")
    with col2:
        t = st.time_input(f"{label}時", value=default_dt.time(), key=f"{key_prefix}_t")
    
    return f"{d} {t.strftime('%H:%M')}" if d and t else ""

# ── 6. カラーピッカー (即時反映・同期型) ────────────────────────
def color_picker_with_swatches(key_prefix: str, default_color: str = "#FFD166"):
    """丸ボタンをクリックすると下のピッカー色も即座に変わるUI"""
    val_key = f"{key_prefix}_color_val"
    
    if val_key not in st.session_state:
        st.session_state[val_key] = default_color

    st.caption("プリセットから選択")
    swatches = ["#FFD166", "#06D6A0", "#118AB2", "#EF476F", "#E94560", "#4ECCA3", "#8E44AD"]
    
    cols = st.columns(len(swatches))
    for i, sw in enumerate(swatches):
        with cols[i]:
            # 選択中の色を強調
            is_selected = st.session_state[val_key].upper() == sw.upper()
            border = "3px solid white" if is_selected else "1px solid #555"
            
            st.markdown(
                f'<div style="background:{sw}; width:18px; height:18px; '
                f'border-radius:50%; border:{border}; margin:auto;"></div>',
                unsafe_allow_html=True
            )
            
            # ボタンクリックで状態を更新して再描画
            if st.button("選", key=f"{key_prefix}_sw_{i}", use_container_width=True):
                st.session_state[val_key] = sw
                st.rerun()

    # 下のピッカーと連動
    chosen = st.color_picker(
        "カスタム色調整 (選択中)", 
        value=st.session_state[val_key], 
        key=f"{key_prefix}_cp_widget"
    )
    
    # ピッカーを直接操作した際も状態を同期
    if chosen != st.session_state[val_key]:
        st.session_state[val_key] = chosen

    return st.session_state[val_key]
