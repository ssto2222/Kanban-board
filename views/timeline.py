from __future__ import annotations
import html as html_mod
from datetime import datetime, timedelta
import streamlit as st
from config import COL_META, JST
from utils.helpers import get_priority_color, parse_dt
from components.dialog import task_dialog

# ── 1. CSS: 崩れを最小限にし、クリックを最優先する ───────────────────
_CSS = """
<style>
/* タイムライン全体のコンテナ */
.tl-container { width: 100%; background: #1a1a2e; color: #eee; border-radius: 10px; overflow-x: auto; font-family: sans-serif; }
/* ヘッダー（日付） */
.tl-header { display: flex; border-bottom: 2px solid #444; position: sticky; top: 0; background: #1a1a2e; z-index: 10; height: 45px; }
.tl-label-col { width: 150px; min-width: 150px; border-right: 1px solid #444; flex-shrink: 0; }
.tl-time-col { flex-grow: 1; position: relative; }
/* 行（ステータス/担当者ごと） */
.tl-row { display: flex; border-bottom: 1px solid #333; position: relative; min-height: 80px; }
.tl-row-label { width: 150px; min-width: 150px; padding: 10px; background: #1a1a2e; border-right: 1px solid #444; font-size: 13px; font-weight: bold; position: sticky; left: 0; z-index: 5; }
.tl-row-content { flex-grow: 1; position: relative; }
/* 目盛り線 */
.tl-grid-line { position: absolute; top: 0; bottom: 0; width: 1px; background: rgba(255,255,255,0.05); pointer-events: none; }
.tl-today-marker { position: absolute; top: 0; bottom: 0; width: 2px; background: #ff4b2b; z-index: 2; pointer-events: none; }
/* タスクバー: aタグにして確実にリンクとして機能させる */
.tl-task-link { position: absolute; height: 28px; text-decoration: none !important; color: white !important; z-index: 100; transition: transform 0.1s; }
.tl-task-link:hover { transform: scale(1.03); filter: brightness(1.2); z-index: 101; }
.tl-task-bar { width: 100%; height: 100%; border-radius: 5px; display: flex; align-items: center; padding: 0 8px; font-size: 11px; font-weight: bold; box-sizing: border-box; box-shadow: 1px 2px 4px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.2); }
.tl-date-tick { position: absolute; font-size: 10px; transform: translateX(-50%); top: 15px; color: #888; }
</style>
"""

def render_timeline(tasks: list[dict]) -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── 2. クリック（URLパラメータ）のチェック ────────────────────────
    # URLに edit_id があれば、それを優先してダイアログ表示対象にする
    q_params = st.query_params
    target_id = q_params.get("edit_id")

    # ── 3. 設定と計算 ───────────────────────────────────────────
    today = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # スパン選択（シンプルに）
    view_mode = st.radio("スパン", ["2週間", "1ヶ月", "3ヶ月"], horizontal=True, key="tl_v2_span")
    group_by = st.radio("グループ", ["担当者", "ステータス"], horizontal=True, key="tl_v2_grp")

    days_back, days_fwd = (3, 11) if view_mode == "2週間" else (7, 23) if view_mode == "1ヶ月" else (14, 76)
    chart_min = today - timedelta(days=days_back)
    chart_max = today + timedelta(days=days_fwd)
    total_days = (chart_max - chart_min).days + 1
    
    # 1日あたりの%幅
    day_w = 100.0 / total_days
    def get_pos(dt: datetime) -> float:
        diff = (dt - chart_min).total_seconds() / 86400.0
        return diff * day_w

    # ── 4. データ整理 ───────────────────────────────────────────
    processed = []
    task_lookup = {}
    for t in tasks:
        if t.get("column") == "done": continue
        tid = t.get("id")
        if not tid: continue
        s, e = parse_dt(t.get("started_at")), parse_dt(t.get("finished_at"))
        if not s: continue
        if not e: e = s + timedelta(hours=23)
        if e < chart_min or s > chart_max: continue

        label = (t.get("assignee") or "未設定") if group_by == "担当者" else COL_META.get(t.get("column", "todo"), {}).get("label", "不明")
        
        processed.append({
            "id": tid, "title": t.get("title", "無題"), "start": max(s, chart_min), "end": min(e, chart_max),
            "group": label, "color": get_priority_color(t.get("deadline", ""), t.get("color", "#666"), t.get("column", "todo"))
        })
        task_lookup[tid] = t

    # ── 5. HTML構築 ─────────────────────────────────────────────
    h = ['<div class="tl-container">']
    
    # ヘッダー (日付目盛り)
    h.append('<div class="tl-header"><div class="tl-label-col"></div><div class="tl-time-col">')
    for i in range(total_days):
        d = chart_min + timedelta(days=i)
        left = i * day_w
        h.append(f'<div class="tl-date-tick" style="left:{left + day_w/2:.2f}%">{d.strftime("%m/%d")}</div>')
        h.append(f'<div class="tl-grid-line" style="left:{left:.2f}%"></div>')
    h.append('</div></div>')

    # グループ分け
    group_names = sorted(list(set(p["group"] for p in processed)))
    for gn in group_names:
        h.append(f'<div class="tl-row"><div class="tl-row-label">{html_mod.escape(gn)}</div><div class="tl-row-content">')
        
        # 今日ライン
        t_pos = get_pos(datetime.now(JST))
        if 0 <= t_pos <= 100: h.append(f'<div class="tl-today-marker" style="left:{t_pos:.2f}%"></div>')

        # タスクバー
        grp_tasks = [p for p in processed if p["group"] == gn]
        lanes = []
        for t in sorted(grp_tasks, key=lambda x: x["start"]):
            l_idx = next((i for i, end in enumerate(lanes) if t["start"] >= end), -1)
            if l_idx == -1: lanes.append(t["end"]); l_idx = len(lanes)-1
            else: lanes[l_idx] = t["end"]

            left, width = get_pos(t["start"]), max(get_pos(t["end"]) - get_pos(t["start"]), day_w * 0.8)
            top = 10 + l_idx * 32
            
            # リンクにクエリパラメータを仕込む（絶対確実な遷移）
            href = f"?edit_id={t['id']}"
            
            h.append(
                f'<a href="{href}" target="_self" class="tl-task-link" style="left:{left:.2f}%; width:{width:.2f}%; top:{top}px;">'
                f'<div class="tl-task-bar" style="background:{t["color"]};" title="{html_mod.escape(t["title"])}">'
                f'{html_mod.escape(t["title"])}</div></a>'
            )
        h.append('</div></div>')
    h.append('</div>')
    
    st.markdown("".join(h), unsafe_allow_html=True)

    # ── 6. ダイアログ起動 ─────────────────────────────────────────
    if target_id and target_id in task_lookup:
        task_dialog(task_lookup[target_id])
        
        # ダイアログを閉じるためのリセットボタン
        if st.button("一覧に戻る (編集完了)"):
            st.query_params.clear()
            st.rerun()
