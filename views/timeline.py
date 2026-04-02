from __future__ import annotations
import os
import html as html_mod
from datetime import datetime, timedelta
import streamlit as st
from config import COL_META

# ── ヘルパー ──────────────────────────────────────────────────────────────────
def _get_wd(dt: datetime) -> str:
    return ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]

def _parse_dt(s: str) -> datetime | None:
    if not s or s == "None": return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            clean_s = s.replace("T", " ")[:16] if "T" in s else s.strip()
            return datetime.strptime(clean_s, "%Y-%m-%d %H:%M" if len(clean_s) > 10 else "%Y-%m-%d")
        except:
            continue
    return None

def _get_group_label(task: dict, group_by: str) -> str:
    if group_by == "担当者":
        return task.get("assignee") or "未割り当て"
    col_key = task.get("column", "todo")
    return COL_META.get(col_key, {}).get("label", col_key)

# ── メイン描画関数 ────────────────────────────────────────────────────────────
def render_timeline(tasks: list[dict]) -> None:
    st.markdown("## 📅 タイムライン")

    if not tasks:
        st.warning("タスクデータが空です。")
        return

    # ── 表示設定コントロール ──
    ctrl_l, ctrl_r = st.columns([1, 2])
    with ctrl_l:
        group_by = st.radio("グループ分け", ["担当者", "ステータス"], horizontal=True, key="tl_grp")
    
    with ctrl_r:
        # スケールの選択
        view_mode = st.select_slider(
            "表示スパン",
            options=["日次 (2週間)", "週次 (2ヶ月)", "月次 (6ヶ月)"],
            value="日次 (2週間)",
            key="tl_scale"
        )

    # 1. 期間計算の動的設定
    base_today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if view_mode == "日次 (2週間)":
        min_date = base_today - timedelta(days=2)
        max_date = base_today + timedelta(days=12)
        grid_count = (max_date - min_date).days
        date_format = "%d" # 日付のみ
    elif view_mode == "週次 (2ヶ月)":
        min_date = base_today - timedelta(weeks=1)
        max_date = base_today + timedelta(weeks=8)
        grid_count = (max_date - min_date).days // 7
        date_format = "%m/%d~" # 週の開始日
    else: # 月次
        min_date = base_today - timedelta(days=30)
        max_date = base_today + timedelta(days=150)
        grid_count = 6
        date_format = "%m月"

    total_sec = (max_date - min_date).total_seconds()

    # 2. データのフィルタリングと加工
    valid_tasks = []
    for t in tasks:
        start = _parse_dt(str(t.get("started_at") or t.get("deadline")))
        end = _parse_dt(str(t.get("finished_at") or t.get("deadline")))
        
        if start:
            if not end or end <= start:
                end = start + timedelta(hours=4)
            
            # 表示範囲内にあるタスクのみ抽出
            if start < max_date and end > min_date:
                valid_tasks.append({
                    "title": t.get("title", "無題"),
                    "start": max(start, min_date), # はみ出し防止
                    "end": min(end, max_date),
                    "group": _get_group_label(t, group_by),
                    "color": t.get("color", "#FFD166")
                })

    # 3. CSS定義
    grid_width = 100 / (grid_count if grid_count > 0 else 1)
    style = f"""
    <style>
        .tl-wrapper {{ background-color: #1a1a2e; padding: 15px; border-radius: 12px; overflow-x: auto; color: #eee; font-family: sans-serif; }}
        .tl-header-row {{ display: flex; height: 50px; border-bottom: 2px solid #444; position: sticky; top: 0; z-index: 10; background: #1a1a2e; }}
        .tl-row {{ display: flex; position: relative; border-bottom: 1px solid #2a2a4a; min-height: 60px; }}
        .tl-label {{ width: 120px; min-width: 120px; font-size: 12px; font-weight: bold; padding: 15px 5px; color: #aaa; border-right: 1px solid #2a2a4a; overflow: hidden; }}
        .tl-track {{ position: relative; flex-grow: 1; min-width: 800px; background-image: linear-gradient(90deg, #2a2a4a 1px, transparent 1px); background-size: {grid_width}%; }}
        .date-cell {{ position: absolute; height: 100%; border-right: 1px solid #2a2a4a; text-align: center; font-size: 11px; padding-top: 5px; line-height: 1.4; }}
        .sat {{ color: #4ecca3; background: rgba(78, 204, 163, 0.05); }}
        .sun {{ color: #ff4b2b; background: rgba(255, 75, 43, 0.05); }}
        .tl-bar {{
            position: absolute; height: 26px; border-radius: 4px; font-size: 11px; padding: 0 8px;
            display: flex; align-items: center; color: #000; font-weight: bold;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3); z-index: 2;
        }}
        .now-line {{ position: absolute; top: 0; bottom: 0; width: 2px; background: #e94560; z-index: 5; box-shadow: 0 0 8px #e94560; }}
    </style>
    """

    # 4. ヘッダー生成 (日・週・月で切り替え)
    header_html = f'<div class="tl-header-row"><div class="tl-label">項目</div><div class="tl-track">'
    for i in range(grid_count + 1):
        if view_mode == "日次 (2週間)":
            d = min_date + timedelta(days=i)
        elif view_mode == "週次 (2ヶ月)":
            d = min_date + timedelta(weeks=i)
        else: # 月次
            # 簡易的に30日計算
            d = min_date + timedelta(days=i*30)
            
        left = (i / grid_count) * 100 if grid_count > 0 else 0
        w_idx = d.weekday()
        cls = "sat" if w_idx == 5 else "sun" if w_idx == 6 else ""
        
        label = d.strftime(date_format)
        if view_mode == "日次 (2週間)":
            label += f"<br>{_get_wd(d)}"
            
        header_html += f'<div class="date-cell {cls}" style="left:{left}%; width:{grid_width}%;">{label}</div>'
    header_html += '</div></div>'

    # 5. タスク行の生成
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
            
            task_inner += f'''
                <div class="tl-bar" style="left:{left}%; width:{max(width, 1.0)}%; top:{10 + (level*32)}px; background-color:{t["color"]};" 
                     title="{html_mod.escape(t["title"])} ({t["start"].strftime('%m/%d')}～)">
                    {html_mod.escape(t["title"])}
                </div>'''

        row_h = 60 + (max_level * 32)
        body_html += f'<div class="tl-row" style="height:{row_h}px;">'
        body_html += f'<div class="tl-label">{grp}</div><div class="tl-track">'
        if 0 <= now_pos <= 100:
            body_html += f'<div class="now-line" style="left: {now_pos}%"></div>'
        body_html += task_inner
        body_html += '</div></div>'

    st.markdown(style + '<div class="tl-wrapper">' + header_html + body_html + '</div>', unsafe_allow_html=True)
