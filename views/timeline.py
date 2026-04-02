from __future__ import annotations
import html as html_mod
from datetime import datetime, date, timedelta
import streamlit as st
from config import COL_META
from utils.helpers import get_priority_color, parse_dt

# ── 定数 & CSS ─────────────────────────────────────────────────────────────

_CSS = """
<style>
.tl-wrap { background: #1a1a2e; border-radius: 8px; padding: 8px 0; overflow-x: auto; }
.tl-axis-row { display: flex; align-items: flex-end; height: 35px; border-bottom: 2px solid #444; }
.tl-group-col { width: 140px; min-width: 140px; flex-shrink: 0; }
.tl-chart-col { flex: 1; position: relative; height: 35px; min-width: 800px; }
.tl-tick { position: absolute; font-size: 10px; color: #9a9ab0; text-align: center; transform: translateX(-50%); line-height: 1.2; }
.tl-tick.sat { color: #4ecca3; }
.tl-tick.sun { color: #ff4b2b; }

.tl-row { display: flex; align-items: stretch; height: 60px; border-bottom: 1px solid #2a2a4a; }
.tl-group-name { width: 140px; min-width: 140px; padding: 10px; font-size: 12px; color: #ccc; border-right: 1px solid #2a2a4a; display: flex; align-items: center; overflow: hidden; }
.tl-chart-area { flex: 1; position: relative; min-width: 800px; }

.tl-gridline { position: absolute; top: 0; bottom: 0; width: 1px; background: #2a2a4a; }
.tl-today-line { position: absolute; top: 0; bottom: 0; width: 2px; background: #e94560; z-index: 10; }

.tl-bar-outer { position: absolute; top: 25px; height: 22px; z-index: 2; cursor: pointer; }
.tl-bar-fill { width: 100%; height: 100%; border-radius: 4px; box-shadow: 1px 1px 4px rgba(0,0,0,0.5); }
.tl-bar-name { position: absolute; top: -14px; left: 0; white-space: nowrap; font-size: 10px; font-weight: bold; color: #eee; text-shadow: 1px 1px 2px #000; }
</style>
"""

def _get_wd(dt: datetime) -> str:
    return ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]

def render_timeline(tasks: list[dict]) -> None:
    st.markdown("## 📅 タイムライン")
    st.markdown(_CSS, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1: group_by = st.radio("グループ", ["担当者", "ステータス"], horizontal=True)
    with c2: view_mode = st.select_slider("スパン", options=["日次 (2週間)", "週次 (2ヶ月)", "月次 (6ヶ月)"])

    # 1. データ加工
    rows = []
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    for t in tasks:
        s = parse_dt(t.get("started_at"))
        e = parse_dt(t.get("finished_at"))
        deadline_str = t.get("deadline", "")
        
        if not s and not deadline_str: continue
        
        if not s: # 開始がない場合は期限の前日に設定
            d_dt = datetime.strptime(deadline_str, "%Y-%m-%d")
            s = d_dt - timedelta(days=1)
        if not e:
            e = s + timedelta(hours=23)

        # 🌟 色の自動判定を適用
        display_color = get_priority_color(deadline_str, t.get("color", "#FFD166"))

        rows.append({
            "title": t.get("title", ""),
            "start": s,
            "end": e,
            "group": _get_group_label(t, group_by),
            "color": display_color
        })

    if not rows:
        st.info("表示可能なタスクがありません。")
        return

    # 2. 表示範囲設定
    min_dt = min([r["start"] for r in rows] + [today]) - timedelta(days=2)
    max_dt = max([r["end"] for r in rows] + [today]) + timedelta(days=7)
    total_secs = (max_dt - min_dt).total_seconds()
    def get_pct(dt): return (dt - min_dt).total_seconds() / total_secs * 100

    # 3. 目盛り生成
    ticks = []
    curr = min_dt.replace(hour=0, minute=0)
    while curr <= max_dt:
        p = get_pct(curr)
        if 0 <= p <= 100:
            wd = _get_wd(curr)
            label = f"{curr.strftime('%m/%d')}<br>{wd}" if "日次" in view_mode else curr.strftime("%m/%d")
            ticks.append((p, label, curr.weekday()))
        
        if "日次" in view_mode: curr += timedelta(days=1)
        elif "週次" in view_mode: curr += timedelta(weeks=1)
        else: curr += timedelta(days=30)

    # 4. HTML構築
    h = ['<div class="tl-wrap">']
    # 軸行
    h.append('<div class="tl-axis-row"><div class="tl-group-col"></div><div class="tl-chart-col">')
    for p, label, wd in ticks:
        cls = "sat" if wd == 5 else "sun" if wd == 6 else ""
        h.append(f'<div class="tl-tick {cls}" style="left:{p:.2f}%">{label}</div>')
    h.append('</div></div>')

    # データ行
    group_tasks = {}
    for r in rows: group_tasks.setdefault(r["group"], []).append(r)
    
    for grp in sorted(group_tasks.keys()):
        h.append('<div class="tl-row">')
        h.append(f'<div class="tl-group-name">{grp}</div>')
        h.append('<div class="tl-chart-area">')
        # グリッド
        for p, _, _ in ticks: h.append(f'<div class="tl-gridline" style="left:{p:.2f}%"></div>')
        # 今日線
        tp = get_pct(datetime.now())
        if 0 <= tp <= 100: h.append(f'<div class="tl-today-line" style="left:{tp:.2f}%"></div>')
        
        # バー
        for r in group_tasks[grp]:
            left = get_pct(r["start"])
            width = max(get_pct(r["end"]) - left, 1.0)
            h.append(f'<div class="tl-bar-outer" style="left:{left:.2f}%; width:{width:.2f}%">')
            h.append(f'<div class="tl-bar-name">{html_mod.escape(r["title"])}</div>')
            h.append(f'<div class="tl-bar-fill" style="background:{r["color"]}"></div></div>')
        
        h.append('</div></div>')
    h.append('</div>')
    st.markdown("".join(h), unsafe_allow_html=True)

def _get_group_label(task, mode):
    if mode == "担当者": return task.get("assignee") or "未設定"
    return COL_META.get(task.get("column", "todo"), {}).get("label", "不明")
