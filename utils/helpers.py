import streamlit as st
from datetime import datetime, date, timedelta, timezone

# 日本時間 (JST) 定義
JST = timezone(timedelta(hours=9))

def color_picker_with_swatches(key_prefix: str, default_color: str = "#FFD166"):
    """
    丸ボタンを選択すると、下のカラーピッカーの色も即座に変わる同期型。
    """
    val_key = f"{key_prefix}_color_val"
    
    # 1. セッション状態の初期化
    if val_key not in st.session_state:
        st.session_state[val_key] = default_color

    st.caption("プリセットから選択")
    swatches = ["#FFD166", "#06D6A0", "#118AB2", "#EF476F", "#E94560", "#4ECCA3", "#8E44AD"]
    
    # 2. スウォッチボタンの並び
    cols = st.columns(len(swatches))
    for i, sw in enumerate(swatches):
        with cols[i]:
            # 現在選択されている色のボタンに枠線をつけるCSS（オプション）
            is_selected = st.session_state[val_key].upper() == sw.upper()
            border_style = "3px solid white" if is_selected else "1px solid #555"
            
            st.markdown(
                f'<div style="background:{sw}; width:20px; height:20px; '
                f'border-radius:50%; border:{border_style}; margin:auto;"></div>',
                unsafe_allow_html=True
            )
            
            # ボタンクリックでセッションを更新し、即座にrerun
            if st.button(" ", key=f"{key_prefix}_sw_{i}", use_container_width=True):
                st.session_state[val_key] = sw
                st.rerun() # これにより下の color_picker の value が更新される

    # 3. カスタム色調整（ここがボタンと連動する）
    # value にセッションの状態を渡すのがポイント
    chosen = st.color_picker(
        "カスタム色調整 (選択中の色)", 
        value=st.session_state[val_key], 
        key=f"{key_prefix}_cp_widget"
    )
    
    # ピッカーを直接いじった場合もセッションに反映
    if chosen != st.session_state[val_key]:
        st.session_state[val_key] = chosen

    return st.session_state[val_key]

# --- 他のヘルパー関数 (parse_dt, dt_input等) は前回のまま維持してください ---
