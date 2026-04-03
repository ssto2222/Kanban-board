from __future__ import annotations
import html as html_mod
from datetime import datetime, timedelta
import streamlit as st
from streamlit_javascript import st_javascript
from config import COL_META, JST
from utils.helpers import get_priority_color, parse_dt
from components.dialog import task_dialog

# ── CSS ──────────────────────────────────────────────────────────────────
_CSS = """
<style>
.tl-wrap { background: #1a1a2e; border-radius: 8px; padding: 8px 0; overflow-x: auto; box-shadow: inset 0 0 10px rgba(0,0,0,0.5); }
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
.tl-today-line { position: absolute; top: 0; bottom: 0; width: 2px; background: #e94560; z-index: 10; box-shadow: 0 0 4px #e94560; }
.tl-bar-outer { position: absolute; height: 24px; z-index: 2; cursor: pointer; transition: transform 0.2s; }
.tl-bar-outer:hover { transform: scaleY(1.1); z-index: 5; opacity: 0.9; }
.tl-bar-fill { width: 100%; height: 100%; border-radius: 12px; box-shadow: 1px 2px 5px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.2); box-sizing: border-box; overflow: hidden; display: flex; align-items: center; padding: 0 10px; }
.tl-bar-ms { border: 2px solid #ffffff !important; box-shadow: 0 0 8px rgba(255,255,255,0.5); }
.tl-bar-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 11px; font-weight: bold; color: #fff; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000, 0 1px 4px rgba(0,0,0,0.8); pointer-events: none; width: 100%; }
</style>
"""

def _get_wd(dt: datetime) -> str:
    return ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]

def _get_group_label(task: dict, mode: str) -> str:
    if mode == "担当者": return task.get("assignee") or "（未設定）"
    return COL_META.get(task.get("column", "todo"), {}).get("label", "不明")

def render_timeline(tasks: list[dict]) -> None:
    st.markdown("## 📅 タイムライン (未完了のみ)")
    st.markdown(_CSS, unsafe_allow_html=True)

    # 1. セッション初期化
    if 'editing_task_id' not in st.session_state: st.session_state['editing_task_id'] = None
    if 'tl_ver' not in st.session_state: st.session_state['tl_ver'] = 0

    today = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)

    # ── 2. コントロールパネル ─────────────────────
    ctrl_l, ctrl_r = st.columns(2)
    with ctrl_l:
        group_by = st.radio("グループ分け", ["担当者", "ステータス"], horizontal=True, key="tl_grp")
    with ctrl_r:
        view_mode = st.select_slider("表示スパン", 
                                   options=["日次 (2週間)", "週次 (2ヶ月)", "月次 (6ヶ月)", "年次 (12ヶ月)"], 
                                   value="日次 (2週間)", key="tl_scale")

    # 表示範囲決定 (ロジック省略なし)
    if "日次" in view_mode: days_back, days_fwd, interval = 3, 11, timedelta(days=1); chart_min_width = 1000
    elif "週次" in view_mode: days_back, days_fwd, interval = 14, 46, timedelta(days=1); chart_min_width = 1200
    elif "月次" in view_mode: days_back, days_fwd, interval = 30, 150, timedelta(days=3); chart_min_width = 1800
    else: days_back, days_fwd, interval = 30, 335, timedelta(days=7); chart_min_width = 2800

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
            "is_ms": "🔷" in t.get("title", "")
        })
        task_lookup[tid] = t

    # ── 4. HTML 構築 (JSクリック発火を改良) ────────────────────────
    h = [f'<div class="tl-wrap">']
    # 目盛り、グリッドライン等は既存通り
    h.append(f'<div class="tl-axis-row"><div class="tl-group-col"></div><div class="tl-chart-col" style="min-width:{chart_min_width}px;">')
    # ... (ticks生成省略、既存ロジック使用) ...
    # 簡略化のため中略：実際にはここに既存のticks描画コードが入ります

    group_map = {}
    for r in processed_rows: group_map.setdefault(r["group"], []).append(r)
    BAR_HEIGHT, BAR_MARGIN, ROW_PADDING = 24, 8, 15

    for grp in sorted(group_map.keys()):
        grp_tasks = sorted(group_map[grp], key=lambda x: x["start"])
        lanes, task_layout = [], []
        for t in grp_tasks:
            lane_idx = next((i for i, end in enumerate(lanes) if t["start"] >= end), -1)
            if lane_idx == -1: lanes.append(t["end"]); lane_idx = len(lanes) - 1
            else: lanes[lane_idx] = t["end"]
            task_layout.append((t, lane_idx))

        row_h = max(ROW_PADDING * 2 + len(lanes) * (BAR_HEIGHT + BAR_MARGIN), 60)
        h.append(f'<div class="tl-row" style="height:{row_h}px;">')
        h.append(f'<div class="tl-group-name">{html_mod.escape(grp)}</div>')
        h.append(f'<div class="tl-chart-area" style="min-width:{chart_min_width}px;">')

        # バーの描画
        for t, lane_idx in task_layout:
            left, width = get_pct(t["start"]), max(get_pct(t["end"]) - get_pct(t["start"]), 1.0)
            top = ROW_PADDING + lane_idx * (BAR_HEIGHT + BAR_MARGIN)
            # 修正ポイント: BroadcastChannel + SessionStorage の二段構え
            click_js = f"sessionStorage.setItem('clicked_task', '{t['id']}'); new BroadcastChannel('kanban_tl').postMessage('{t['id']}');"
            h.append(
                f'<div class="tl-bar-outer" style="left:{left:.2f}%; width:{width:.2f}%; top:{top}px;" onclick="{click_js}">'
                f'<div class="tl-bar-fill{" tl-bar-ms" if t["is_ms"] else ""}" style="background:{t["color"]};">'
                f'<div class="tl-bar-name">{html_mod.escape(t["title"])}</div></div></div>'
            )
        h.append('</div></div>')
    h.append('</div>')
    st.markdown("".join(h), unsafe_allow_html=True)

    # ── 5. クリック検出ロジック (ここが重要) ──────────────────────────
    # JSで「クリックされたID」を監視し、取得できたら即座に返す
    clicked_id = st_javascript("""
        (async () => {
            // 1. まず現在の SessionStorage を確認
            let tid = sessionStorage.getItem('clicked_task');
            if (tid) {
                sessionStorage.removeItem('clicked_task');
                return tid;
            }
            // 2. なければ BroadcastChannel で待機
            const bc = new BroadcastChannel('kanban_tl');
            return await new Promise(resolve => {
                bc.onmessage = (e) => {
                    bc.close();
                    sessionStorage.removeItem('clicked_task');
                    resolve(e.data);
                };
                setTimeout(() => resolve(null), 2000); // 応答がなければnull
            });
        })()
    """, key=f"tl_poll_{st.session_state['tl_ver']}")

    # ── 6. Python側でのダイアログ起動 ──────────────────────────────
    if clicked_id and isinstance(clicked_id, str) and clicked_id in task_lookup:
        # IDが取れたら即座にセッションを更新して再描画
        st.session_state['editing_task_id'] = clicked_id
        st.session_state['tl_ver'] += 1
        st.rerun()

    # ダイアログの表示 (st.rerun後にここが踏まれる)
    if st.session_state.get('editing_task_id'):
        tid = st.session_state['editing_task_id']
        if tid in task_lookup:
            task_dialog(task_lookup[tid])
            # 重要: ダイアログが閉じられた後にIDを消す
            # ただし st.dialog の中で保存・削除して rerun される場合は
            # そちらの処理に任せるか、ここで None に戻す
            st.session_state['editing_task_id'] = None
