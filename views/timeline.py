from __future__ import annotations
import html as html_mod
from datetime import datetime, timedelta
import streamlit as st
from config import COL_META

# ── ヘルパー関数 ──────────────────────────────────────────────────────────────

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
    st.markdown("## 📅 タイムライン (HTML/CSS版)")

    # コントロール UI
    ctrl_l, ctrl_r = st.columns(2)
    with ctrl_l:
        group_by = st.radio("グループ分け", ["担当者", "ステータス"], horizontal=True)
    
    # データの準備
    valid_tasks = []
    min_date = datetime.now()
    max_date = datetime.now() + timedelta(days=7)

    for t in tasks:
        start = _parse_dt(t.get("started_at")) or _parse_dt(t.get("deadline"))
        end = _parse_dt(t.get("finished_at")) or _parse_dt(t.get("deadline"))
        
        if not start: continue
        if end <= start: end = start + timedelta(hours=1)
        
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
        st.info("表示できるタスクがありません。")
        return

    # 期間の計算 (全体の日数)
    min_date = min_date.replace(hour=0, minute=0)
    total_days = max(1, (max_date - min_date).days + 1)
    
   # --- CSS定義（改善版） ---
    st.markdown(f"""
    <style>
        .timeline-container {{
            background-color: #1a1a2e;
            padding: 20px 10px;
            border-radius: 12px;
            overflow-x: auto; /* 横スクロールを許可 */
            color: #eaeaea;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        .timeline-row {{
            display: flex;
            align-items: center;
            margin-bottom: 12px;
            height: 50px; /* 高さを少し広げる */
            position: relative;
            border-bottom: 1px solid #2a2a4a;
        }}
        .group-label {{
            width: 100px;
            min-width: 100px;
            font-size: 0.8rem;
            font-weight: bold;
            color: #aaa;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            padding-right: 10px;
        }}
        .track {{
            position: relative;
            flex-grow: 1;
            height: 100%;
            background-image: linear-gradient(90deg, rgba(42,42,74,0.5) 1px, transparent 1px);
            background-size: {100/total_days if total_days > 0 else 10}%;
        }}
        .bar {{
            position: absolute;
            height: 30px;
            top: 10px;
            border-radius: 6px;
            font-size: 12px;
            padding: 0 10px;
            display: flex;
            align-items: center;
            color: #111;
            font-weight: 600;
            white-space: nowrap;
            overflow: hidden; /* 通常時ははみ出しを隠す */
            text-overflow: ellipsis; /* 文字が長い場合は「...」にする */
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            cursor: pointer;
            z-index: 2;
            transition: all 0.2s ease;
        }}
        /* ホバーした時に内容をすべて表示する */
        .bar:hover {{
            z-index: 100;
            overflow: visible;
            min-width: max-content;
            box-shadow: 0 0 15px rgba(255,255,255,0.2);
            transform: translateY(-2px);
        }}
        .today-line {{
            position: absolute;
            top: 0; bottom: 0;
            width: 2px;
            background-color: #e94560;
            z-index: 1;
            box-shadow: 0 0 8px #e94560;
        }}
        .today-label {{
            position: absolute;
            top: -15px;
            left: -10px;
            font-size: 10px;
            color: #e94560;
            font-weight: bold;
        }}
    </style>
    """, unsafe_allow_html=True)

    # --- HTML描画 ---
    groups = sorted(list(set(t["group"] for t in valid_tasks)))
    
    html = '<div class="timeline-container">'
    
    # 今日の線の位置計算
    today_pos = ((datetime.now() - min_date).total_seconds() / (total_days * 86400)) * 100

    for grp in groups:
        grp_tasks = [t for t in valid_tasks if t["group"] == grp]
        html += f'<div class="timeline-row"><div class="group-label">{grp}</div><div class="track">'
        
        # 今日の線
        if 0 <= today_pos <= 100:
            html += f'<div class="today-line" style="left: {today_pos}%"></div>'
            
        for t in grp_tasks:
            left = ((t["start"] - min_date).total_seconds() / (total_days * 86400)) * 100
            width = ((t["end"] - t["start"]).total_seconds() / (total_days * 86400)) * 100
            width = max(width, 2) # 最低限の幅を確保
            
            html += f'''
                <div class="bar" style="left: {left}%; width: {width}%; background-color: {t["color"]};" 
                     title="{t["title"]} ({t["assignee"]})">
                    {t["title"]}
                </div>
            '''
        html += '</div></div>'
    
    html += '</div>'
    st.write(html, unsafe_allow_html=True)
