import streamlit as st
import html as html_mod
from datetime import datetime, date

# ── カラー操作 (Cardの見た目用) ──────────────────────────────────

def darken(hex_color: str, amount: float = 0.2) -> str:
    """色を指定した割合だけ暗くする (16進数)"""
    hex_color = hex_color.lstrip('#')
    # 3桁の短縮形式 (#FFF) を6桁 (#FFFFFF) に変換
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    
    try:
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        # 各チャンネルを暗くし、0-255の範囲に収める
        new_rgb = tuple(max(0, int(c * (1 - amount))) for c in rgb)
        return '#{:02x}{:02x}{:02x}'.format(*new_rgb)
    except:
        return "#666666" # エラー時はグレーを返す

# ── 日時・期限のHTML生成 ──────────────────────────────────────

def deadline_html(deadline_str: str) -> str:
    """期限に応じたカラーのHTMLバッジを返す"""
    if not deadline_str or deadline_str == "None":
        return ""
    
    try:
        # 文字列をdateオブジェクトに変換
        dt = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        today = date.today()
        diff = (dt - today).days

        if diff < 0:
            cls = "dl-overdue" # 期限切れ（赤）
        elif diff <= 2:
            cls = "dl-warn"    # 2日前（オレンジ）
        else:
            cls = "dl-ok"      # 余裕あり（緑）

        return f'<span class="{cls}">⌛ {deadline_str}</span>'
    except:
        return f'<span>{deadline_str}</span>'

# ── 日時入力コンポーネント (render_new_task用) ──────────────────

def dt_input(label: str, value: str, key_prefix: str) -> str:
    """Streamlitの標準入力を使って ISO形式の日時文字列を生成する"""
    col1, col2 = st.columns(2)
    with col1:
        d = st.date_input(f"{label} 日付", key=f"{key_prefix}_d")
    with col2:
        t = st.time_input(f"{label} 時刻", value=datetime.now().time(), key=f"{key_prefix}_t")
    
    if d and t:
        return f"{d} {t.strftime('%H:%M')}"
    return ""

# ── カラーピッカー (丸型ボタン付き) ─────────────────────────────

def color_picker_with_swatches(key_prefix: str, default_color: str = "#FFD166"):
    """丸いカラー見本付きのピッカー"""
    val_key = f"{key_prefix}_color_val"
    if val_key not in st.session_state:
        st.session_state[val_key] = default_color

    swatches = ["#FFD166", "#06D6A0", "#118AB2", "#EF476F", "#E94560", "#4ECCA3"]
    
    cols = st.columns(len(swatches))
    for i, sw in enumerate(swatches):
        with cols[i]:
            # 色丸を表示
            st.markdown(
                f'<div style="background:{sw};width:20px;height:20px;border-radius:50%;border:1px solid #fff;"></div>',
                unsafe_allow_html=True
            )
            if st.button(" ", key=f"{key_prefix}_sw_{i}"):
                st.session_state[val_key] = sw
                st.rerun()

    chosen = st.color_picker("色調整", value=st.session_state[val_key], key=f"{key_prefix}_cp")
    st.session_state[val_key] = chosen
    return chosen
    try:
        return get_supabase().table("tasks").delete().eq("id", task_id).execute()
    except Exception as e:
        st.error(f"削除エラー: {e}")
        raise e
