from __future__ import annotations
import html as html_mod
from datetime import datetime, timedelta
import streamlit as st
from config import COL_META, JST
from utils.helpers import get_priority_color, parse_dt
from components.dialog import task_dialog

# ── CSS (レイアウト維持と透明ボタン用) ────────────────────────────────
_CSS = """
<style>
.tl-container { width: 100%; background: #1a1a2e; border-radius: 8px; overflow: hidden; border: 1px solid #333; }
.tl-header { display: flex; background: #16213e; border-bottom: 2px solid #444; height: 40px; position: sticky; top: 0; z-index: 10; }
.tl-side { width: 120px; min-width: 120px; border-right: 1px solid #444; flex-shrink: 0; z-index: 5; background: #16213e; }
.tl-main { flex-grow: 1; position: relative; overflow-x: auto; }
.tl-row { display: flex; border-bottom: 1px solid #2a2a4a; min-height: 70px; position: relative; }
.tl-row-label { width: 120px; min-width: 120px; padding: 10px; font-size: 12px; font-weight: bold; border-right: 1px solid #444; background: #1a1a2e; }
.tl-canvas { flex-grow: 1; position: relative; background-image: linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px); background-size: 50px 100%; }
/* バーの見た目 */
.tl-bar { position: absolute; height: 28px; border-radius: 4px; display: flex; align-items: center; padding: 0 8px; font-size: 11px; color: white; font-weight: bold; pointer-events: none; border: 1px solid rgba(255,255,255,0.2); box-shadow: 1px 1px 3px rgba(0,0,0,0.3); white-space: nowrap; overflow: hidden; }
/* Streamlitボタンを透明化して重ねるためのハック */
div[data-testid="stButton"] > button {
    background: transparent !important;
    border: none !important;
    color: transparent !important;
    width: 100% !important;
    height: 100% !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    z-index: 100 !important;
}
.button-container { position: absolute; z-index: 100; }
</style>
"""

def render_timeline(tasks: list[dict]) -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown("### 📅 タイムライン")

    # 1. 設定
    today = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)
    col1, col2 = st.columns(2)
    with col1:
        group_by = st.radio("表示単位", ["担当者", "ステータス"], horizontal=True)
    
    # 固定スパン（計算を安定させるため14日間に固定推奨）
    chart_min = today - timedelta(days=3)
    chart_max = today + timedelta(days=11)
    total_days = (chart_max - chart_min).days + 1
    
    # 2. データ加工
    group_map = {}
    for t in tasks:
        if t.get("column") == "done": continue
        s = parse_dt(t.get("started_at"))
        if not s: continue
        e = parse_dt(t.get("finished_at")) or (s + timedelta(hours=23))
        if e < chart_min or s > chart_max: continue

        g_label = (t.get("assignee") or "未設定") if group_by == "担当者" else COL_META.get(t.get("column", "todo"), {}).get("label", "不明")
        group_map.setdefault(g_label, []).append({
            "id": t["id"], "title": t["title"], "start": max(s, chart_min), "end": min(e, chart_max),
            "color": get_priority_color(t.get("deadline", ""), t.get("color", "#555"), t.get("column", "todo")), "raw": t
        })

    # 3. HTML & Button 描画
    st.write("---")
    
    # 日付ヘッダー
    cols = st.columns([1.5] + [1] * total_days)
    cols[0].write("対象")
    for i in range(total_days):
        d = chart_min + timedelta(days=i)
        cols[i+1].caption(d.strftime("%m/%d"))

    for gn in sorted(group_map.keys()):
        row_container = st.container()
        with row_container:
            # 1行を2カラムに分ける（ラベル | チャートエリア）
            l_col, r_col = st.columns([1.5, total_days])
            l_col.info(f"**{gn}**")
            
            with r_col:
                # この相対ポジション用コンテナの中でバーを描画
                st.markdown('<div style="position: relative; height: 80px; width: 100%;">', unsafe_allow_html=True)
                
                grp_tasks = sorted(group_map[gn], key=lambda x: x["start"])
                lanes = []
                for t in grp_tasks:
                    # 重なり管理（レーン分け）
                    lane_idx = next((i for i, end in enumerate(lanes) if t["start"] >= end), -1)
                    if lane_idx == -1: lanes.append(t["end"]); lane_idx = len(lanes)-1
                    else: lanes[lane_idx] = t["end"]

                    # 位置計算 (0.0 ~ 100.0%)
                    left = ((t["start"] - chart_min).days / total_days) * 100
                    width = (((t["end"] - t["start"]).days + 1) / total_days) * 100
                    top = 5 + lane_idx * 35

                    # 背景バー（見た目）
                    st.markdown(
                        f'<div class="tl-bar" style="left:{left}%; width:{width}%; top:{top}px; background:{t["color"]};">'
                        f'{html_mod.escape(t["title"])}</div>', 
                        unsafe_allow_html=True
                    )
                    
                    # 透明ボタン（実際のクリック判定）
                    # ボタンの配置をバーに重ねる
                    with st.container():
                        st.markdown(f'<div class="button-container" style="left:{left}%; width:{width}%; top:{top}px; height:28px;">', unsafe_allow_html=True)
                        if st.button(" ", key=f"btn_{t['id']}"):
                            task_dialog(t["raw"])
                        st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
