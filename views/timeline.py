from __future__ import annotations
import html as html_mod
from datetime import datetime, timedelta
import streamlit as st
from streamlit_javascript import st_javascript
from config import COL_META, JST
from utils.helpers import get_priority_color, parse_dt
from components.dialog import task_dialog

# ── CSS (初期の美しいデザインを完全復元) ────────────────────────────────
_CSS = """
<style>
.tl-wrap { background: #1a1a2e; border-radius: 8px; padding: 8px 0; overflow-x: auto; box-shadow: inset 0 0 10px rgba(0,0,0,0.5); position: relative; }
.tl-axis-row { display: flex; align-items: flex-end; height: 45px; border-bottom: 2px solid #444; position: sticky; top: 0; background: #1a1a2e; z-index: 20; }
.tl-group-col { width: 140px; min-width: 140px; flex-shrink: 0; border-right: 1px solid #444; }
.tl-chart-col { flex: 1; position: relative; height: 45px; }
.tl-tick { position: absolute; font-size: 10px; color: #9a9ab0; text-align: center; transform: translateX(-50%); line-height: 1.2; padding-bottom: 5px; white-space: nowrap; }
.tl-tick.sat { color: #4ecca3; font-weight: bold; }
.tl-tick.sun { color: #ff4b2b; font-weight: bold; }
.tl-row { display: flex; align-items: stretch; border-bottom: 1px solid #2a2a4a; position: relative; }
.tl-group-name { width: 140px; min-width: 140px; padding: 10px; font-size: 12px; font-weight: bold; color: #eaeaea; border-right: 1px solid #2a2a4a; display: flex; align-items: flex-start; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; box-sizing: border-box; background: #1a1a2e; position: sticky; left: 0; z-index: 15; }
.tl-chart-area { flex: 1; position: relative; min-height: 60px; }
.tl-gridline { position: absolute; top: 0; bottom: 0; width: 1px; background: #2a2a4a; z-index: 0; }
.tl-today-line { position: absolute; top: 0; bottom: 0; width: 2px; background: #e94560; z-index: 10; box-shadow: 0 0 4px #e94560; pointer-events: none; }
.tl-bar-outer { position: absolute; height: 24px; z-index: 20; cursor: pointer; transition: transform 0.2s; border: none; background: none; padding: 0; }
.tl-bar-outer:hover { transform: scaleY(1.1); z-index: 25; }
.tl-bar-fill { width: 100%; height: 100%; border-radius: 12px; box-shadow: 1px 2px 5px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.2); box-sizing: border-box; overflow: hidden; display: flex; align-items: center; padding: 0 10px; }
.tl-bar-ms { border: 2px solid #ffffff !important; box-shadow: 0 0 8px rgba(255,255,255,0.5); }
.tl-bar-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 11px; font-weight: bold; color: #fff; text-shadow: 1px 1px 2px #000; pointer-events: none; width: 100%; text-align: left; }
</style>
"""

def _get_wd(dt: datetime) -> str:
    return ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]

def _get_group_label(task: dict, mode: str) -> str:
    if mode == "担当者": return task.get("assignee") or "（未設定）"
    return COL_META.get(task.get("column", "todo"), {}).get("label", "不明")

def render_timeline(tasks: list[dict]) -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    # 1. セッション初期化
    if 'tl_ver' not in st.session_state: st.session_state['tl_ver'] = 0
    if 'editing_task_id' not in st.session_state: st.session_state['editing_task_id'] = None

    today = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)

    # ── 2. コントロールパネル ─────────────────────
    col_l, col_r = st.columns([1, 2])
    with col_l:
        group_by = st.radio("グループ分け", ["担当者", "ステータス"], horizontal=True, key="tl_grp_v3")
    with col_r:
        view_mode = st.select_slider("表示スパン", 
            options=["日次 (2週間)", "週次 (2ヶ月)", "月次 (6ヶ月)"], 
            value="日次 (2週間)", key="tl_scale_v3")

    # 表示範囲決定
    if "日次" in view_mode:
        days_back, days_fwd, interval = 3, 11, timedelta(days=1)
        chart_min_width = 1000
    elif "週次" in view_mode:
        days_back, days_fwd, interval = 14, 46, timedelta(days=1)
        chart_min_width = 1200
    else:
        days_back, days_fwd, interval = 30, 150, timedelta(days=3)
        chart_min_width = 1800

    chart_min = today - timedelta(days=days_back)
    chart_max = today + timedelta(days=days_fwd)
    total_secs = (chart_max - chart_min).total_seconds()
    def get_pct(dt: datetime) -> float: return (dt - chart_min).total_seconds() / total_secs * 100

    # ── 3. データ加工 ──────────────────────────
    processed_rows, task_lookup = [], {}
    for t in tasks:
        if t.get("column") == "done": continue
        tid = t.get("id")
        if not tid: continue
        s, e = parse_dt(t.get("started_at")), parse_dt(t.get("finished_at"))
        if not s and t.get("deadline"):
            try:
                d = datetime.strptime(t["deadline"], "%Y-%m-%d").replace(tzinfo=JST)
                s, e = d - timedelta(days=1), d
            except: continue
        if not s: continue
        if not e: e = s + timedelta(hours=23)
        if e < chart_min or s > chart_max: continue

        processed_rows.append({
            "id": tid, "title": t.get("title", "無題"), "start": max(s, chart_min), "end": min(e, chart_max),
            "group": _get_group_label(t, group_by), "color": get_priority_color(t.get("deadline", ""), t.get("color", "#FFD166"), t.get("column", "todo")),
            "is_ms": "🔷" in t.get("title", ""), "raw": t
        })
        task_lookup[tid] = t

    # ── 4. HTML 構築 ─────────────────────────────
    h = [f'<div class="tl-wrap">']
    
    # 目盛り(Ticks)生成
    h.append(f'<div class="tl-axis-row"><div class="tl-group-col"></div><div class="tl-chart-col" style="min-width:{chart_min_width}px;">')
    curr_t = chart_min.replace(hour=0, minute=0, second=0, microsecond=0)
    ticks_p = []
    while curr_t <= chart_max:
        p = get_pct(curr_t)
        if 0 <= p <= 100:
            wd = _get_wd(curr_t)
            label = f"{curr_t.strftime('%m/%d')}<br>({wd})" if "日次" in view_mode else curr_t.strftime('%m/%d')
            cls = "sat" if curr_t.weekday() == 5 else "sun" if curr_t.weekday() == 6 else ""
            h.append(f'<div class="tl-tick {cls}" style="left:{p:.2f}%">{label}</div>')
            ticks_p.append(p)
        curr_t += interval
    h.append('</div></div>')

    # コンテンツ描画
    group_map = {}
    for r in processed_rows: group_map.setdefault(r["group"], []).append(r)
    BAR_HEIGHT, BAR_MARGIN, ROW_PADDING = 24, 8, 15

    for grp in sorted(group_map.keys()):
        grp_tasks = sorted(group_map[grp], key=lambda x: x["start"])
        lanes, task_layout = [], []
        for t in grp_tasks:
            l_idx = next((i for i, end in enumerate(lanes) if t["start"] >= end), -1)
            if l_idx == -1: lanes.append(t["end"]); l_idx = len(lanes)-1
            else: lanes[l_idx] = t["end"]
            task_layout.append((t, l_idx))

        row_h = max(ROW_PADDING * 2 + len(lanes) * (BAR_HEIGHT + BAR_MARGIN), 60)
        h.append(f'<div class="tl-row" style="height:{row_h}px;">')
        h.append(f'<div class="tl-group-name">{html_mod.escape(grp)}</div>')
        h.append(f'<div class="tl-chart-area" style="min-width:{chart_min_width}px;">')
        for p in ticks_p: h.append(f'<div class="tl-gridline" style="left:{p:.2f}%"></div>')
        
        tp = get_pct(datetime.now(JST))
        if 0 <= tp <= 100: h.append(f'<div class="tl-today-line" style="left:{tp:.2f}%"></div>')

        for t, l_idx in task_layout:
            left, width = get_pct(t["start"]), max(get_pct(t["end"]) - get_pct(t["start"]), 1.0)
            top = ROW_PADDING + l_idx * (BAR_HEIGHT + BAR_MARGIN)
            # 確実なクリックイベント
            c_js = f"sessionStorage.setItem('tl_tid', '{t['id']}'); window.dispatchEvent(new CustomEvent('tl_evt'));"
            h.append(
                f'<div class="tl-bar-outer" style="left:{left:.2f}%; width:{width:.2f}%; top:{top}px;" onclick="{c_js}">'
                f'<div class="tl-bar-fill{" tl-bar-ms" if t["is_ms"] else ""}" style="background:{t["color"]};">'
                f'<div class="tl-bar-name">{html_mod.escape(t["title"])}</div></div></div>'
            )
        h.append('</div></div>')
    h.append('</div>')
    st.markdown("".join(h), unsafe_allow_html=True)

    # ── 5. JS通信 & ダイアログ ──────────────────────────
    res = st_javascript("""
        (async () => {
            return await new Promise(resolve => {
                const h = () => {
                    const id = sessionStorage.getItem('tl_tid');
                    if(id) { sessionStorage.removeItem('tl_tid'); resolve(id); }
                };
                window.addEventListener('tl_evt', h);
                setTimeout(() => resolve(null), 2000);
            });
        })()
    """, key=f"tl_v3_js_{st.session_state['tl_ver']}")

    if res and res in task_lookup:
        st.session_state['editing_task_id'] = res
        st.session_state['tl_ver'] += 1
        st.rerun()

    if st.session_state.get('editing_task_id'):
        tid = st.session_state['editing_task_id']
        if tid in task_lookup:
            task_dialog(task_lookup[tid])
            st.session_state['editing_task_id'] = None
