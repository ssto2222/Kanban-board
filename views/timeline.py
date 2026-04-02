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
    
    # 1. データ整形と期間決定
    valid_tasks = []
    min_date = datetime.now() - timedelta(days=1)
    max_date = datetime.now() + timedelta(days=14)

    for t in tasks:
        start = _parse_dt(t.get("started_at")) or _parse_dt(t.get("deadline"))
        end = _parse_dt(t.get("finished_at")) or _parse_dt(t.get("deadline"))
        if not start: continue
        if not end or end <= start: end = start + timedelta(hours=4)
        
        valid_tasks.append({
            "title": t.get("title", "無題"),
            "start": start,
            "end": end,
            "group": _get_group_label(t, group_by),
            "color": t.get("color", "#FFD166"),
            "assignee": t.get("assignee") or "―"
        })
        min_date = min(min_date, start)
        max_date = max(max_date, end)

    if not valid_tasks:
        st.info("表示可能なタスクがありません。")
        return

    min_date = min_date.replace(hour=0, minute=0, second=0)
    total_sec = (max_date - min_date).total_seconds()
    total_days = int(total_sec / 86400) + 1

    # 2. CSS定義
    style = f"""
    <style>
        .tl-wrapper {{ background-color: #1a1a2e; padding: 20px; border-radius: 12px; overflow-x: auto; color: #eee; font-family: sans-serif; }}
        .tl-row {{ display: flex; margin-bottom: 2px; position: relative; border-bottom: 1px solid #2a2a4a; min-height: 50px; }}
        .tl-label {{ width: 100px; min-width: 100px; font-size: 11px; padding-top: 10px; color: #888; sticky: left; }}
        .tl-track {{ position: relative; flex-grow: 1; background-image: linear-gradient(90deg, #2a2a4a 1px, transparent 1px); background-size: {100/total_days}%; min-height: 50px; }}
        .tl-bar {{
            position: absolute; height: 24px; border-radius: 4px; font-size: 10px; padding: 0 8px;
            display: flex; align-items: center; color: #000; font-weight: bold;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3); z-index: 2; transition: all 0.2s;
        }}
        .tl-bar:hover {{ z-index: 100; overflow: visible; min-width: max-content; transform: scale(1.05); }}
        .now-line {{ position: absolute; top: 0; bottom: 0; width: 2px; background: #e94560; z-index: 5; box-shadow: 0 0 5px #e94560; }}
    </style>
    """

    # 3. HTML構築 (重なり回避ロジック)
    groups = sorted(list(set(t["group"] for t in valid_tasks)))
    now_pos = ((datetime.now() - min_date).total_seconds() / total_sec) * 100
    
    html = '<div class="tl-wrapper">'
    for grp in groups:
        grp_tasks = [t for t in valid_tasks if t["group"] == grp]
        # 重なり判定用の「段」リスト
        levels: list[datetime] = [] 
        
        task_html = ""
        max_level = 0
        
        # 開始順にソートして配置
        for t in sorted(grp_tasks, key=lambda x: x["start"]):
            level = 0
            # 空いている段を探す
            for i, last_end in enumerate(levels):
                if t["start"] >= last_end:
                    level = i
                    levels[i] = t["end"]
                    break
                level = i + 1
            
            if level >= len(levels):
                levels.append(t["end"])
            
            max_level = max(max_level, level)
            
            left = ((t["start"] - min_date).total_seconds() / total_sec) * 100
            width = ((t["end"] - t["start"]).total_seconds() / total_sec) * 100
            top = 10 + (level * 30) # 1段につき30pxずらす
            
            task_html += f'''
                <div class="tl-bar" style="left:{left}%; width:{max(width, 2)}%; top:{top}px; background-color:{t["color"]};" 
                     title="{html_mod.escape(t["title"])}">
                    {html_mod.escape(t["title"])}
                </div>'''

        # 行の高さを段数に合わせて調整
        row_height = 50 + (max_level * 30)
        html += f'<div class="tl-row" style="height:{row_height}px;">'
        html += f'<div class="tl-label">{grp}</div><div class="tl-track">'
        if 0 <= now_pos <= 100:
            html += f'<div class="now-line" style="left: {now_pos}%"></div>'
        html += task_html
        html += '</div></div>'
    
    html += '</div>'
    st.markdown(style + html, unsafe_allow_html=True)
