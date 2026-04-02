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
        st.error("SupabaseのURLまたはKEYが見つかりません。HerokuのConfig Varsを確認してください。")
        st.stop()
    return create_client(url.strip().replace('"', ''), key.strip().replace('"', ''))

# ── ヘルパー ──────────────────────────────────────────────────────────────────
def _get_wd(dt: datetime) -> str:
    return ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]

def _parse_dt(s: str) -> datetime | None:
    if not s or s == "None": return None
    # ISO形式 (2023-10-01T10:00:00...) や標準形式に対応
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            # Tが含まれるISO形式などは先頭19文字程度で合わせる
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

    # 表示設定
    ctrl_l, ctrl_r = st.columns(2)
    with ctrl_l:
        group_by = st.radio("グループ分け", ["担当者", "ステータス"], horizontal=True, key="tl_grp")
    
    # 1. データの有効化と期間計算
    valid_tasks = []
    # 基準日を「今日」に設定
    base_today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    min_date = base_today - timedelta(days=2)
    max_date = base_today + timedelta(days=14)

    for t in tasks:
        # 開始日、終了日、期限のいずれかがあるか確認
        s_raw = t.get("started_at") or t.get("deadline")
        e_raw = t.get("finished_at") or t.get("deadline")
        
        start = _parse_dt(str(s_raw))
        end = _parse_dt(str(e_raw))
        
        if start:
            if not end or end <= start:
                end = start + timedelta(hours=4) # 期間がない場合は4時間分
            
            valid_tasks.append({
                "title": t.get("title", "無題"),
                "start": start,
                "end": end,
                "group": _get_group_label(t, group_by),
                "color": t.get("color", "#FFD166")
            })
            # 表示範囲を広げる
            min_date = min(min_date, start.replace(hour=0, minute=0))
            max_date = max(max_date, end.replace(hour=0, minute=0) + timedelta(days=1))

    if not valid_tasks:
        st.info("表示可能なスケジュール（開始日または期限があるタスク）がありません。")
        # デバッグ用：生データの内容を1件だけ出す
        with st.expander("データ構造の確認（デバッグ用）"):
            st.write(tasks[0] if tasks else "No Data")
        return

    total_days = (max_date - min_date).days
    if total_days <= 0: total_days = 1
    total_sec = total_days * 86400

    # 2. CSS定義
    style = f"""
    <style>
        .tl-wrapper {{ background-color: #1a1a2e; padding: 15px; border-radius: 12px; overflow-x: auto; color: #eee; font-family: sans-serif; }}
        .tl-header-row {{ display: flex; height: 50px; border-bottom: 2px solid #444; position: sticky; top: 0; z-index: 10; background: #1a1a2e; }}
        .tl-row {{ display: flex; position: relative; border-bottom: 1px solid #2a2a4a; min-height: 70px; }}
        .tl-label {{ width: 120px; min-width: 120px; font-size: 12px; font-weight: bold; padding: 15px 5px; color: #aaa; border-right: 1px solid #2a2a4a; overflow: hidden; }}
        .tl-track {{ position: relative; flex-grow: 1; min-width: {total_days * 60}px; background-image: linear-gradient(90deg, #2a2a4a 1px, transparent 1px); background-size: {100/total_days}%; }}
        .date-cell {{ position: absolute; height: 100%; border-right: 1px solid #2a2a4a; text-align: center; font-size: 11px; padding-top: 5px; line-height: 1.4; }}
        .sat {{ color: #4ecca3; background: rgba(78, 204, 163, 0.05); }}
        .sun {{ color: #ff4b2b; background: rgba(255, 75, 43, 0.05); }}
        .tl-bar {{
            position: absolute; height: 28px; border-radius: 5px; font-size: 11px; padding: 0 10px;
            display: flex; align-items: center; color: #000; font-weight: bold;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            box-shadow: 0 4px 8px rgba(0,0,0,0.5); z-index: 2; transition: transform 0.2s;
        }}
        .now-line {{ position: absolute; top: 0; bottom: 0; width: 3px; background: #e94560; z-index: 5; box-shadow: 0 0 10px #e94560; }}
    </style>
    """

    # 3. 日付ヘッダーの生成
    header_html = f'<div class="tl-header-row"><div class="tl-label">グループ</div><div class="tl-track">'
    for i in range(total_days):
        d = min_date + timedelta(days=i)
        w = d.weekday() # 5=土, 6=日
        cls = "sat" if w == 5 else "sun" if w == 6 else ""
        left = (i / total_days) * 100
        width = (1 / total_days) * 100
        header_html += f'<div class="date-cell {cls}" style="left:{left}%; width:{width}%;">{d.month}/{d.day}<br>{_get_wd(d)}</div>'
    header_html += '</div></div>'

    # 4. タスク行の生成
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
                <div class="tl-bar" style="left:{left}%; width:{max(width, 1.5)}%; top:{15 + (level*35)}px; background-color:{t["color"]};" 
                     title="{html_mod.escape(t["title"])}">
                    {html_mod.escape(t["title"])}
                </div>'''

        row_h = 70 + (max_level * 35)
        body_html += f'<div class="tl-row" style="height:{row_h}px;">'
        body_html += f'<div class="tl-label">{grp}</div><div class="tl-track">'
        if 0 <= now_pos <= 100:
            body_html += f'<div class="now-line" style="left: {now_pos}%"></div>'
        body_html += task_inner
        body_html += '</div></div>'

    # 5. 出力
    st.markdown(style + '<div class="tl-wrapper">' + header_html + body_html + '</div>', unsafe_allow_html=True)
