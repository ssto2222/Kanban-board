from __future__ import annotations
import html as html_mod
from datetime import datetime, timedelta
import streamlit as st
from config import COL_META, JST
from utils.helpers import get_priority_color, parse_dt
from components.dialog import task_dialog

# ── CSS (クリック領域を最前面に出し、体裁を整える) ──────────────────────
_CSS = """
<style>
.tl-wrap { background: #1a1a2e; border-radius: 8px; padding: 8px 0; overflow-x: auto; position: relative; }
.tl-axis-row { display: flex; align-items: flex-end; height: 50px; border-bottom: 2px solid #444; position: sticky; top: 0; background: #1a1a2e; z-index: 100; }
.tl-group-col { width: 140px; min-width: 140px; flex-shrink: 0; border-right: 1px solid #444; }
.tl-chart-col { flex: 1; position: relative; height: 50px; }
.tl-tick { position: absolute; font-size: 10px; color: #9a9ab0; text-align: center; transform: translateX(-50%); line-height: 1.2; padding-bottom: 5px; white-space: nowrap; }
.tl-row { display: flex; align-items: stretch; border-bottom: 1px solid #2a2a4a; position: relative; }
.tl-group-name { width: 140px; min-width: 140px; padding: 10px; font-size: 12px; font-weight: bold; color: #eaeaea; border-right: 1px solid #2a2a4a; background: #1a1a2e; position: sticky; left: 0; z-index: 50; }
.tl-chart-area { flex: 1; position: relative; min-height: 60px; z-index: 10; }
.tl-gridline { position: absolute; top: 0; bottom: 0; width: 1px; background: #2a2a4a; z-index: 0; pointer-events: none; }
.tl-today-line { position: absolute; top: 0; bottom: 0; width: 2px; background: #e94560; z-index: 5; pointer-events: none; }
/* バーの設定: z-indexを高くし、pointer-eventsを有効にする */
.tl-bar-outer { position: absolute; height: 26px; z-index: 200; cursor: pointer; transition: transform 0.1s; }
.tl-bar-outer:hover { transform: scale(1.02); filter: brightness(1.2); }
.tl-bar-fill { width: 100%; height: 100%; border-radius: 4px; border: 1px solid rgba(255,255,255,0.2); display: flex; align-items: center; padding: 0 8px; box-sizing: border-box; }
.tl-bar-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 11px; font-weight: bold; color: #fff; pointer-events: none; }
</style>
"""

def _get_group_label(task: dict, mode: str) -> str:
    if mode == "担当者": return task.get("assignee") or "（未設定）"
    return COL_META.get(task.get("column", "todo"), {}).get("label", "不明")

def render_timeline(tasks: list[dict]) -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    # 1. クエリパラメータからIDを取得（クリック検知）
    query_params = st.query_params
    clicked_id = query_params.get("edit_tid")

    # ── 2. 表示スパン設定 ─────────────────────
    today = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)
    ctrl_l, ctrl_r = st.columns([1, 2])
    with ctrl_l:
        group_by = st.radio("グループ分け", ["担当者", "ステータス"], horizontal=True, key="tl_grp")
    with ctrl_r:
        view_mode = st.select_slider("表示スパン", options=["日次 (2週間)", "週次 (2ヶ月)"], value="日次 (2週間)", key="tl_scale")

    if "日次" in view_mode:
        days_back, days_fwd, interval = 3, 11, timedelta(days=1)
        chart_min_width = 1000
    else:
        days_back, days_fwd, interval = 14, 46, timedelta(days=1)
        chart_min_width = 1200

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
        if not s: continue
        if not e: e = s + timedelta(hours=23)
        if e < chart_min or s > chart_max: continue
        
        processed_rows.append({
            "id": tid, "title": t.get("title", "無題"), "start": max(s, chart_min), "end": min(e, chart_max),
            "group": _get_group_label(t, group_by), 
            "color": get_priority_color(t.get("deadline", ""), t.get("color", "#FFD166"), t.get("column", "todo")),
            "raw": t
        })
        task_lookup[tid] = t

    # ── 4. HTML構築 ─────────────────────────────
    h = ['<div class="tl-wrap">']
    
    # 目盛り(Ticks)
    h.append(f'<div class="tl-axis-row"><div class="tl-group-col"></div><div class="tl-chart-col" style="min-width:{chart_min_width}px;">')
    curr = chart_min.replace(hour=0, minute=0, second=0, microsecond=0)
    while curr <= chart_max:
        p = get_pct(curr)
        if 0 <= p <= 100:
            h.append(f'<div class="tl-tick" style="left:{p:.2f}%">{curr.strftime("%m/%d")}</div>')
        curr += interval
    h.append('</div></div>')

    # タスク描画
    group_map = {}
    for r in processed_rows: group_map.setdefault(r["group"], []).append(r)

    for grp in sorted(group_map.keys()):
        grp_tasks = sorted(group_map[grp], key=lambda x: x["start"])
        lanes = []
        h.append(f'<div class="tl-row">')
        h.append(f'<div class="tl-group-name">{html_mod.escape(grp)}</div>')
        h.append(f'<div class="tl-chart-area" style="min-width:{chart_min_width}px;">')

        for t in grp_tasks:
            lane_idx = next((i for i, end in enumerate(lanes) if t["start"] >= end), -1)
            if lane_idx == -1: lanes.append(t["end"]); lane_idx = len(lanes) - 1
            else: lanes[lane_idx] = t["end"]

            l_pct, w_pct = get_pct(t["start"]), max(get_pct(t["end"]) - get_pct(t["start"]), 1.0)
            top = 15 + lane_idx * 34
            
            # 修正ポイント: window.location.search を更新してリロードさせる
            click_js = f"const url = new URL(window.location); url.searchParams.set('edit_tid', '{t['id']}'); window.location.href = url.href;"
            
            h.append(
                f'<div class="tl-bar-outer" style="left:{l_pct:.2f}%; width:{w_pct:.2f}%; top:{top}px;" onclick="{click_js}">'
                f'<div class="tl-bar-fill" style="background:{t["color"]};">'
                f'<div class="tl-bar-name">{html_mod.escape(t["title"])}</div></div></div>'
            )
        h.append('</div></div>')
    h.append('</div>')
    st.markdown("".join(h), unsafe_allow_html=True)

    # ── 5. ダイアログ起動ロジック ──────────────────────
    if clicked_id and clicked_id in task_lookup:
        # IDがURLに含まれていればダイアログを表示
        task_dialog(task_lookup[clicked_id])
        
        # ダイアログを閉じた後にURLを綺麗にする（これをしないと無限に開き直す）
        if st.button("タイムラインに戻る"):
            st.query_params.clear()
            st.rerun()
