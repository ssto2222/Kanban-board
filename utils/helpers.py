import streamlit as st
import html as html_mod
from datetime import datetime, date, timedelta, timezone

# 日本時間 (JST) の定義
JST = timezone(timedelta(hours=9))

# ── 日付パース (JST対応) ────────────────────

def parse_dt(s: str) -> datetime | None:
    """文字列を日本時間として datetime オブジェクトに変換する"""
    if not s or s == "None" or s == "":
        return None
    
    # ISO形式などの不要な文字を落として先頭16文字(分まで)を取得
    clean_s = str(s).replace("T", " ").replace("Z", "")[:16]
    
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(clean_s, fmt)
            # 日本時間として扱う
            return dt.replace(tzinfo=JST)
        except ValueError:
            continue
    return None

# ── カラー操作 ──────────────────────────────────

def darken(hex_color: str, amount: float = 0.2) -> str:
    """枠線用に色を少し暗くする"""
    hex_color = str(hex_color).lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    
    try:
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        new_rgb = tuple(max(0, int(c * (1 - amount))) for c in rgb)
        return '#{:02x}{:02x}{:02x}'.format(*new_rgb)
    except:
        return "#444444"

# ── 期限のHTML表示 ─────────────────────────────

def deadline_html(deadline_str: str) -> str:
    """期限までの残り日数で色を変えたHTMLを返す"""
    if not deadline_str or deadline_str == "None":
        return ""
    
    try:
        dt = datetime.strptime(str(deadline_str), "%Y-%m-%d").date()
        # 今日も日本時間ベースで取得
        today = datetime.now(JST).date()
        diff = (dt - today).days

        if diff < 0:
            cls = "dl-overdue" # 期限切れ
        elif diff <= 2:
            cls = "dl-warn"    # 直前
        else:
            cls = "dl-ok"      # 余裕あり

        return f'<span class="{cls}">⌛ {deadline_str}</span>'
    except:
        return f'<span>{deadline_str}</span>'

# ── 日時入力 (編集モードの初期値対応) ──────────────────

def dt_input(label: str, value: str = "", key_prefix: str = "") -> str:
    """既存データの初期値(value)を反映し、日本時間で入力する"""
    # 既存の値があればパース、なければ現在の日本時間をデフォルトに
    default_dt = parse_dt(value) or datetime.now(JST)
    
    col1, col2 = st.columns(2)
    with col1:
        d = st.date_input(
            f"{label}日", 
            value=default_dt.date(), 
            key=f"{key_prefix}_d"
        )
    with col2:
        t = st.time_input(
            f"{label}時", 
            value=default_dt.time(), 
            key=f"{key_prefix}_t"
        )
    
    # DB保存形式の文字列で返す
    if d and t:
        return f"{d} {t.strftime('%H:%M')}"
    return ""

# ── カラーピッカー (状態同期・編集対応版) ──────────────────

def color_picker_with_swatches(key_prefix: str, default_color: str = "#FFD166"):
    """
    丸ボタンとピッカーを同期。
    編集時は引数の default_color (既存の色) を優先する。
    """
    val_key = f"{key_prefix}_color_val"
    
    # 編集モードなどで外部から渡された色が、現在のセッションと異なる場合は更新
    if val_key not in st.session_state or (default_color and st.session_state.get("_last_def_clr") != default_color):
        st.session_state[val_key] = default_color
        st.session_state["_last_def_clr"] = default_color

    st.caption("カラー選択")
    swatches = ["#FFD166", "#06D6A0", "#118AB2", "#EF476F", "#E94560", "#4ECCA3", "#8E44AD"]
    
    cols = st.columns(len(swatches))
    for i, sw in enumerate(swatches):
        with cols[i]:
            # 見本の色丸
            st.markdown(
                f'<div style="background:{sw};width:18px;height:18px;border-radius:50%;border:1px solid #fff;margin:auto;"></div>',
                unsafe_allow_html=True
            )
            # 透明なボタンで色を選択可能にする
            if st.button("選", key=f"{key_prefix}_sw_{i}"):
                st.session_state[val_key] = sw
                st.rerun()

    # カラーピッカー本体
    # st.session_state[val_key] を value に指定することで、スウォッチボタンと完全同期
    chosen = st.color_picker(
        "カスタム色調整", 
        value=st.session_state[val_key], 
        key=f"{key_prefix}_cp_raw"
    )
    
    # ピッカーで直接変更された場合
    if chosen != st.session_state[val_key]:
        st.session_state[val_key] = chosen

    return st.session_state[val_key]
