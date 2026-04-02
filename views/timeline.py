from __future__ import annotations
import html as html_mod
from datetime import datetime, date, timedelta
import streamlit as st
from config import COL_META
from utils.helpers import get_priority_color, parse_dt, JST

# ── CSS ──────────────────────────────────────────────────────────────────
_CSS = """
<style>
.tl-wrap { background: #1a1a2e; border-radius: 8px; padding: 8px 0; overflow-x: auto; box-shadow: inset 0 0 10px rgba(0,0,0,0.5); }
.tl-axis-row { display: flex; align-items: flex-end; height: 45px; border-bottom: 2px solid #444; position: sticky; top: 0; background: #1a1a2e; z-index: 20; }
.tl-group-col { width: 140px; min-width: 140px; flex-shrink: 0; border-right: 1px solid #444; }
.tl-chart-col { flex: 1; position: relative; height: 45px; min-width: 1000px; }
.tl-tick { position: absolute; font-size: 10px; color: #9a9ab0; text-align: center; transform: translateX(-50%); line-height: 1.2; padding-bottom: 5px; }
.tl-tick.sat { color: #4ecca3; font-weight: bold; }
.tl-tick.sun { color: #ff4b2b; font-weight: bold; }
.tl-row { display: flex; align-items: stretch; border-bottom: 1px solid #2a2a4a; position: relative; }
.tl-group-name { width: 140px; min-width: 140px; padding: 10px; font-size: 12px; font-weight: bold; color: #eaeaea; border-right: 1px solid #2a2a4a; display: flex; align-items: flex-start; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; box-sizing: border-box; background: #1a1a2e; position: sticky; left: 0; z-index: 15; }
.tl-chart-area { flex: 1; position: relative; min-width: 1000px; min-height: 60px; }
.tl-gridline { position: absolute; top: 0; bottom: 0; width: 1px; background: #2a2a4a; z-index: 0; }
.tl-today-line { position: absolute; top: 0; bottom: 0; width: 2px; background: #e94560; z-index: 10; box-shadow: 0 0 4px #e94560; }
.tl-bar-outer { position: absolute; height: 24px; z-index: 2; cursor: pointer; transition: transform 0.2s; }
.tl-bar-outer:hover { transform: scaleY(1.1); z-index: 5; }
.tl-bar-fill { width: 100%; height: 100%; border-radius: 12px; box-shadow: 1px 2px 5px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.2); box-sizing: border-box; overflow: hidden; display: flex; align-items: center; padding: 0 10px; }
/* マイルストーン用の強調スタイル */
.tl-bar-ms { border: 2px solid #ffffff !important; box-shadow: 0 0 8px rgba(255,255,255,0.5); }
.tl-bar-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 11px; font-weight: bold; color: #fff; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000, 0 1px 4px rgba(0,0,0,0.8); pointer-events: none; width: 100%; }
</style>
"""

def _get_wd(dt: datetime) -> str:
    return ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]

def render_timeline(tasks: list[dict]) -> None:
    st.markdown("## 📅 タイムライン (未完了のみ)")
    st.markdown(_CSS, unsafe_allow_html=True)

    today = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # ── 1. コントロールパネル ─────────────────────
    ctrl_l, ctrl_r = st.columns(2)
    with ctrl_l: 
        group_by = st.radio("グループ分け", ["担当者", "ステータス"], horizontal=True, key="tl_grp")
    with ctrl_r: 
        view_mode = st.select_slider(
            "表示スパン（ピッチ）", 
            options=["日次 (2週間)", "週次 (2ヶ月)", "月次 (6ヶ月)"], 
            value="週次 (2ヶ月)",
            key="tl_scale"
        )

    # ── 2. 表示範囲とインターバルの決定 ──────────────────
    if "日次" in view_mode:
        days_back, days_fwd = 3, 11
        interval = timedelta(days=1)
    elif "週次" in view_mode:
        days_back, days_fwd = 14, 46
        interval = timedelta(days=1)
    else: # 月次
        days_back, days_fwd = 30, 150
        interval = timedelta(days=2)

    chart_min = today - timedelta(days=days_back)
    chart_max = today + timedelta(days=days_fwd)
    total_secs = (chart_max - chart_min).total_seconds()

    def get_pct(dt: datetime) -> float:
        return (dt - chart_min).total_seconds() / total_secs * 100

    # ── 3. データ加工 ──────────────────────────
    processed_rows = []
    for t in tasks:
        if t.get("column") == "done": continue

        title = t.get("title", "無題")
        is_ms = "🔷" in title # タイトルに🔷があればマイルストーンとみなす
        
        s = parse_dt(t.get("started_at"))
        e = parse_dt(t.get("finished_at"))
        deadline_str = t.get("deadline", "")
        status = t.get("column", "todo")
        
        # 開始・終了がないが期限がある場合はマイルストーン表示（期限の前日〜当日）
        if not s and deadline_str:
            try:
                d_dt = datetime.strptime(deadline_str, "%Y-%m-%d").replace(tzinfo=JST)
                s = d_dt - timedelta(days=1)
                e = d_dt
            except: continue

        if not s: continue
        if s and not e: e = s + timedelta(hours=23)

        # 範囲外のタスクは除外
        if e < chart_min or s > chart_max: continue
        
        display_color = get_priority_color(deadline_str, t.get("color", "#FFD166"), column=status)

        if s and e and s <= e:
            processed_rows.append({
                "title": title,
                "start": max(s, chart_min),
                "end": min(e, chart_max),
                "group": _get_group_label(t, group_by),
                "color": display_color,
                "is_ms": is_ms
            })

    # ── 4. 目盛り生成 ──────────────────────────
    ticks = []
    curr = chart_min.replace(hour=0, minute=0, second=0, microsecond=0)
    while curr <= chart_max:
        p = get_pct(curr)
        if 0 <= p <= 100:
            wd = _get_wd(curr)
            label = ""
            if "日次" in view_mode:
                label = f"{curr.strftime('%m/%d')}<br>({wd})"
            elif "週次" in view_mode:
                if curr.weekday() == 0: label = f"{curr.strftime('%m/%d')}"
            else: # 月次
                if curr.day == 1 or curr.day == 15: label = f"{curr.strftime('%m/%d')}"
            
            ticks.append((p, label, curr.weekday()))
        curr += interval

    # ── 5. HTML構築 ────────────────────────────
    h = ['<div class="tl-wrap">']
    h.append('<div class="tl-axis-row"><div class="tl-group-col"></div><div class="tl-chart-col">')
    for p, label, wd in ticks:
        if label:
            cls = "sat" if wd == 5 else "sun" if wd == 6 else ""
            h.append(f'<div class="tl-tick {cls}" style="left:{p:.2f}%">{label}</div>')
    h.append('</div></div>')

    group_map = {}
    for r in processed_rows: group_map.setdefault(r["group"], []).append(r)
    
    BAR_HEIGHT, BAR_MARGIN, ROW_PADDING = 24, 8, 15

    for grp in sorted(group_map.keys()):
        grp_tasks = sorted(group_map[grp], key=lambda x: x["start"])
        lanes: list[datetime] = []
        task_layout = []
        for t in grp_tasks:
            lane_idx = next((i for i, end in enumerate(lanes) if t["start"] >= end), -1)
            if lane_idx == -1:
                lanes.append(t["end"])
                lane_idx = len(lanes) - 1
            else: lanes[lane_idx] = t["end"]
            task_layout.append((t, lane_idx))
        
        row_h = max(ROW_PADDING * 2 + len(lanes) * (BAR_HEIGHT + BAR_MARGIN), 60)
        h.append(f'<div class="tl-row" style="height:{row_h}px;">')
        h.append(f'<div class="tl-group-name" title="{html_mod.escape(grp)}">{html_mod.escape(grp)}</div>')
        h.append('<div class="tl-chart-area">')
        
        for p, _, _ in ticks: 
            h.append(f'<div class="tl-gridline" style="left:{p:.2f}%"></div>')
        
        tp = get_pct(datetime.now(JST))
        if 0 <= tp <= 100: h.append(f'<div class="tl-today-line" style="left:{tp:.2f}%"></div>')
        
        for t, lane_idx in task_layout:
            left, width = get_pct(t["start"]), max(get_pct(t["end"]) - get_pct(t["start"]), 1.0)
            top = ROW_PADDING + lane_idx * (BAR_HEIGHT + BAR_MARGIN)
            title = html_mod.escape(t["title"])
            
            # マイルストーンならクラスを追加
            ms_class = " tl-bar-ms" if t.get("is_ms") else ""
            
            h.append(f'<div class="tl-bar-outer" style="left:{left:.2f}%; width:{width:.2f}%; top:{top}px;">'
                     f'<div class="tl-bar-fill{ms_class}" style="background:{t["color"]};" title="{title}">'
                     f'<div class="tl-bar-name">{title}</div></div></div>')
        h.append('</div></div>')

    h.append('</div>')
    st.markdown("".join(h), unsafe_allow_html=True)

def _get_group_label(task: dict, mode: str) -> str:
    if mode == "担当者": return task.get("assignee") or "（未設定）"
    return COL_META.get(task.get("column", "todo"), {}).get("label", "不明")
