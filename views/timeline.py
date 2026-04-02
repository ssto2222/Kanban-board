from __future__ import annotations
import os
import html as html_mod
from datetime import datetime, timedelta
import streamlit as st
from supabase import create_client
from config import COL_META

# ── データベース接続 ──────────────────────────────────
@st.cache_resource
def get_supabase():
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")
    if not url or not key:
        st.error("Supabaseの認証情報が見つかりません。")
        st.stop()
    return create_client(url.strip().replace('"', ''), key.strip().replace('"', ''))

# ── ヘルパー ──────────────────────────────────────────────────────────────────
def _get_wd(dt: datetime) -> str:
    return ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]

def _parse_dt(s: str) -> datetime | None:
    if not s: return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try: return datetime.strptime(s.strip(), fmt)
        except ValueError: continue
    return None

def _get_group_label(task: dict, group_by: str) -> str:
    if group_by == "担当者":
        return task.get("assignee") or "未割り当て"
    col_key = task.get("column", "todo")
    return COL_META.get(col_key, {}).get("label", col_key)

# ── メイン描画関数 ────────────────────────────────────────────────────────────
def render_timeline(tasks: list[dict]) -> None:
    st.markdown("## 📅 タイムライン")

    ctrl_l, ctrl_r = st.columns(2)
    with ctrl_l:
        group_by = st.radio("グループ分け", ["担当者", "ステータス"], horizontal=True, key="tl_grp")
    
    # 1. データ整形
    valid_tasks = []
    min_date = datetime.now().replace(hour=0, minute=0, second=0)
    max_date = min_date + timedelta(days=14) # デフォルト2週間

    for t in tasks:
        start = _parse_dt(t.get("started_at")) or _parse_dt(t.get("deadline"))
        end = _parse_dt(t.get("finished_at")) or _parse_dt(t.get("deadline"))
        if not start: continue
        if not end or end <= start: end = start + timedelta(hours=4)
        
        valid_tasks.append({"title": t.get("title", "無題"), "start": start, "end": end, "group": _get_group_label(t, group_by), "color": t.get("color", "#FFD166")})
        min_date = min(min_date, start.replace(hour=0, minute=0))
        max_date = max(max_date, end.replace(hour=0, minute=0) + timedelta(days=1))

    total_days = (max_date - min_date).days
    total_sec = total_days * 86400

    # 2. CSS定義
    style = f"""
    <style>
        .tl-wrapper {{ background-color: #1a1a2e; padding: 10px; border-radius: 12px; overflow-x: auto; color: #eee; font-family: sans-serif; }}
        .tl-header-row {{ display: flex; height: 40px; border-bottom: 2px solid #444; position: sticky; top: 0; z-index: 10; background: #1a1a2e; }}
        .tl-row {{ display: flex; position: relative; border-bottom: 1px solid #2a2a4a; min-height: 60px; }}
        .tl-label {{ width: 100px; min-width: 100px; font-size: 11px; font-weight: bold; padding: 10px 5px; color: #aaa; border-right: 1px solid #2a2a4a; overflow: hidden; }}
        .tl-track {{ position: relative; flex-grow: 1; min-width: {total_days * 50}px; /* 1日あたり50px確保 */
            background-image: linear-gradient(90deg, #2a2a4a 1px, transparent 1px); background-size: {100/total_days}%; }}
        .date-cell {{ position: absolute; height: 100%; border-right: 1px solid #2a2a4a; text-align: center; font-size: 10px; }}
        .date-cell.sat {{ color: #4ecca3; background: rgba(78, 204, 163, 0.05); }}
        .date-cell.sun {{ color: #ff4b2b; background: rgba(255, 75, 43, 0.05); }}
        .tl-bar {{
            position: absolute; height: 26px; border-radius: 4px; font-size: 11px; padding: 0 8px;
            display: flex; align-items: center; color: #000; font-weight: bold;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            box-shadow: 0 3px 6px rgba(0,0,0,0.4); z-index: 2; transition: transform 0.1s;
        }}
        .now-line {{ position: absolute; top: 0; bottom: 0; width: 2px; background: #e94560; z-index: 5; box-shadow: 0 0 8px #e94560; }}
    </style>
    """

    # 3. 日付ヘッダーの生成
    header_html = f'<div class="tl-header-row"><div class="tl-label">グループ</div><div class="tl-track" style="min-width: {total_days*50}px;">'
    for i in range(total_days):
        d = min_date + timedelta(days=i)
        w = d.weekday()
        cls = "sat" if w == 6 else "sun" if w == 0 else "" # 日曜が0, 土曜が6(weekday()準拠なら土5, 日6)
        cls = "sun" if w == 6 else "sat" if w == 5 else ""
        left = (i / total_days) * 100
        width = (1 / total_days) * 100
        header_html += f'<div class="date-cell {cls}" style="left:{left}%; width:{width}%;">{d.month}/{d.day}<br>({_get_wd(d)})</div>'
    header_html += '</div></div>'

    # 4. タスク行の生成 (重なり回避付)
    body_html = ""
    groups = sorted(list(set(t["group"] for t in valid_tasks)))
    now_pos = ((datetime.now() - min_date).total_seconds() / total_sec) * 100
    
    for grp in groups:
        grp_tasks = [t for t in valid_tasks if t["group"] == grp]
        levels: list[datetime] = []
        task_inner = ""
        max_level = 0
        
        for t in sorted(grp_tasks, key=lambda x: x["start"]):
            level = next((i for i, last_end in enumerate(levels) if t["start"] >= last_end), len(levels))
            if level >= len(levels): levels.append(t["end"])
            else: levels[level] = t["end"]
            
            max_level = max(max_level, level)
            left = ((t["start"] - min_date).total_seconds() / total_sec) * 100
            width = ((t["end"] - t["start"]).total_seconds() / total_sec) * 100
            task_inner += f'<div class="tl-bar" style="left:{left}%; width:{max(width, 1)}%; top:{10 + (level*32)}px; background-color:{t["color"]};" title="{html_mod.escape(t["title"])}">{html_mod.escape(t["title"])}</div>'

        body_html += f'<div class="tl-row" style="height:{60 + (max_level*32)}px;">'
        body_html += f'<div class="tl-label">{grp}</div><div class="tl-track" style="min-width: {total_days*50}px;">'
        if 0 <= now_pos <= 100: body_html += f'<div class="now-line" style="left: {now_pos}%"></div>'
        body_html += task_inner
        body_html += '</div></div>'

    # 5. 出力 (unsafe
