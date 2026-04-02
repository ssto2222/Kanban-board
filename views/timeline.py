from __future__ import annotations
import os
import html as html_mod
from datetime import datetime, timedelta
import streamlit as st
from supabase import create_client
from config import COL_META

# ── データベース接続 (Heroku/Local 両対応) ──────────────────────────────────

@st.cache_resource
def get_supabase():
    # HerokuのConfig Vars (os.environ) を優先し、なければ st.secrets を見る
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

    if not url or not key:
        st.error("Supabaseの認証情報が見つかりません。環境変数を確認してください。")
        st.stop()
    
    # URLの余計な引用符を掃除
    url = url.strip().replace('"', '').replace("'", "")
    key = key.strip().replace('"', '').replace("'", "")
    
    return create_client(url, key)

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

    # 1. 表示設定
    ctrl_l, ctrl_r = st.columns(2)
    with ctrl_l:
        group_by = st.radio("グループ分け", ["担当者", "ステータス"], horizontal=True, key="tl_grp")
    
    # 2. データ整形
    valid_tasks = []
    # デフォルトの表示範囲（今日を中心に前後）
    min_date = datetime.now() - timedelta(days=2)
    max_date = datetime.now() + timedelta(days=14)

    for t in tasks:
        # 開始・終了の決定（なければ期限を使用）
        start = _parse_dt(t.get("started_at")) or _parse_dt(t.get("deadline"))
        end = _parse_dt(t.get("finished_at")) or _parse_dt(t.get("deadline"))
        
        if not start: continue
        if not end or end <= start: 
            end = start + timedelta(hours=2) # 期間がない場合は2時間分確保
        
        valid_tasks.append({
            "title": t.get("title", "無題"),
            "start": start,
            "end": end,
            "group": _get_group_label(t, group_by),
            "color": t.get("color", "#FFD166"),
            "assignee": t.get("assignee") or "―"
        })
        # 範囲をタスクに合わせて広げる
        min_date = min(min_date, start)
        max_date = max(max_date, end)

    if not valid_tasks:
        st.info("表示可能なタスクがありません（開始日または期限を設定してください）。")
        return

    # 全期間の日数計算
    min_date = min_date.replace(hour=0, minute=0, second=0)
    total_seconds = (max_date - min_date).total_seconds()
    if total_seconds <= 0: total_seconds = 86400
    
    total_days = int(total_seconds / 86400) + 1

    # 3. CSS定義 (unsafe_allow_html=True で流し込む)
    style = f"""
    <style>
        .timeline-wrapper {{
            background-color: #1a1a2e;
            padding: 30px 15px;
            border-radius: 15px;
            color: #eaeaea;
            font-family: sans-serif;
            overflow-x: auto;
        }}
        .timeline-row {{
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            height: 45px;
            position: relative;
            border-bottom: 1px solid #2a2a4a;
        }}
        .group-name {{
            width: 120px;
            min-width: 120px;
            font-size: 12px;
            font-weight: bold;
            color: #888;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .time-track {{
            position: relative;
            flex-grow: 1;
            height: 100%;
            background-image: linear-gradient(90deg, #2a2a4a 1px, transparent 1px);
            background-size: {100/total_days if total_days > 0 else 10}%;
        }}
        .task-bar {{
            position: absolute;
            height: 28px;
            top: 8px;
            border-radius: 6px;
            font-size: 11px;
            padding: 0 10px;
            display: flex;
            align-items: center;
            color: #000;
            font-weight: bold;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            z-index: 2;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .task-bar:hover {{
            z-index: 100;
            overflow: visible;
            min-width: max-content;
            transform: scale(1.05);
            box-shadow: 0 0 15px rgba(255,255,255,0.2);
        }}
        .now-line {{
            position: absolute;
            top: 0; bottom: 0;
            width: 2px;
            background-color: #e94560;
            z-index: 5;
            box-shadow: 0 0 5px #e94560;
        }}
    </style>
    """

    # 4. HTML構築
    groups = sorted(list(set(t["group"] for t in valid_tasks)))
    now_pos = ((datetime.now() - min_date).total_seconds() / total_seconds) * 100

    html = '<div class="timeline-wrapper">'
    
    for grp in groups:
        grp_tasks = [t for t in valid_tasks if t["group"] == grp]
        html += f'<div class="timeline-row"><div class="group-name">{grp}</div><div class="time-track">'
        
        # 今日の線
        if 0 <= now_pos <= 100:
            html += f'<div class="now-line" style="left: {now_pos}%"></div>'
            
        for t in grp_tasks:
            # 位置と幅の計算
            left = ((t["start"] - min_date).total_seconds() / total_seconds) * 100
            width = ((t["end"] - t["start"]).total_seconds() / total_seconds) * 100
            # 短すぎるタスクでも最低限の幅(3%)を確保
            width = max(width, 3.0) 
            
            # 安全なエスケープ
            safe_title = html_mod.escape(t["title"])
            safe_assignee = html_mod.escape(t["assignee"])
            
            html += f'''
                <div class="task-bar" 
                     style="left: {left}%; width: {width}%; background-color: {t["color"]};" 
                     title="{safe_title} (担当: {safe_assignee})">
                    {safe_title}
                </div>
            '''
        html += '</div></div>'
    
    html += '</div>'

    # 5. レンダリング実行
    st.markdown(style + html, unsafe_allow_html=True)
