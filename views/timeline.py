from __future__ import annotations
import html as html_mod
from datetime import datetime, date, timedelta
import streamlit as st
from config import COL_META
from utils.helpers import get_priority_color, parse_dt, JST  # JSTをインポート

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
    """曜日ラベルを取得"""
    return ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]

def render_timeline(tasks: list[dict]) -> None:
    st.markdown("## 📅 タイムライン")
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── グローバルな「今日」の設定 (Aware datetime) ──
    # これを JST に合わせることで比較エラーを回避します
    today = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)

    c1, c2 = st.columns(2)
    with c1: 
        group_by = st.radio("グループ分け", ["担当者", "ステータス"], horizontal=True, key="tl_grp")
    with c2: 
        view_mode = st.select_slider("表示スパン", options=["日次 (2週間)", "週次 (2ヶ月)", "月次 (6ヶ月)"], key="tl_scale")

    # 1. データ加工
    rows = []
    for t in tasks:
        # helpers.parse_dt は内部で .replace(tzinfo=JST) している前提
        s = parse_dt(t.get("started_at"))
        e = parse_dt(t.get("finished_at"))
        deadline_str = t.get("deadline", "")
        
        # どちらも設定がない場合は表示スキップ
        if not s and not deadline_str: continue
        
        # 開始がない場合は期限の前日に設定 (JST Awareにする)
        if not s and deadline_str:
            try:
                d_dt = datetime.strptime(deadline_str, "%Y-%m-%d").replace(tzinfo=JST)
                s = d_dt - timedelta(days=1)
            except:
                continue

        # 終了がない場合は開始の23時間後に設定
        if s and not e:
            e = s + timedelta(hours=23)

        # ── 期限による色の自動判定 ──
        display_color = get_priority_color(deadline_str, t.get("color", "#FFD166"))

        if s and e:
            rows.append({
                "title": t.get("title", "無題"),
                "start": s,
                "end": e,
                "group": _get_group_label(t, group_by),
                "color": display_color
            })

    if not rows:
        st.info("表示可能なタスクがありません。開始日時または期限を設定してください。")
        return

    # 2. 表示範囲設定 (すべての要素が Aware なのでエラーになりません)
    all_starts = [r["start"] for r in rows] + [today]
    all_ends = [r["end"] for r in rows] + [today]
    
    min_dt = min(all_starts) - timedelta(days=2)
    max_dt = max(all_ends) + timedelta(days=7)
    total_secs = (max_dt - min_dt).total_seconds()

    def get_pct(dt: datetime) -> float:
        return (dt - min_dt).total_seconds() / total_secs * 100

    # 3. 目盛り (Ticks) の生成
    ticks = []
    curr = min_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    while curr <= max_dt:
        p = get_pct(curr)
        if 0 <= p <= 100:
            wd = _get_wd(curr)
            # 日次モードのときだけ曜日を表示
            if "日次" in view_mode:
                label = f"{curr.strftime('%d')}<br>({wd})"
            else:
                label = curr.strftime("%m/%d")
            ticks.append((p, label, curr.weekday()))
        
        # スパンに応じて加算
        if "日次" in view_mode: curr += timedelta(days=1)
        elif "週次" in view_mode: curr += timedelta(weeks=1)
        else: curr += timedelta(days=30)

    # 4. HTML構築
    h = ['<div class="tl-wrap">']
    
    # ── 軸行 (カレンダーヘッダー) ──
    h.append('<div class="tl-axis-row"><div class="tl-group-col"></div><div class="tl-chart-col">')
    for p, label, wd in ticks:
        cls = "sat" if wd == 5 else "sun" if wd == 6 else ""
        h.append(f'<div class="tl-tick {cls}" style="left:{p:.2f}%">{label}</div>')
    h.append('</div></div>')

    # ── データ行 (グループごと) ──
    group_tasks: dict[str, list] = {}
    for r in rows:
        group_tasks.setdefault(r["group"], []).append(r)
    
    for grp in sorted(group_tasks.keys()):
        h.append('<div class="tl-row">')
        h.append(f'<div class="tl-group-name">{html_mod.escape(grp)}</div>')
        h.append('<div class="tl-chart-area">')
        
        # 背景グリッド線
        for p, _, _ in ticks:
            h.append(f'<div class="tl-gridline" style="left:{p:.2f}%"></div>')
        
        # 今日線 (Red Line)
        tp = get_pct(datetime.now(JST))
        if 0 <= tp <= 100:
            h.append(f'<div class="tl-today-line" style="left:{tp:.2f}%"></div>')
        
        # タスクバー (Gantt Bars)
        for r in group_tasks[grp]:
            left = get_pct(r["start"])
            width = max(get_pct(r["end"]) - left, 0.8) # 最低限の幅を確保
            
            title_esc = html_mod.escape(r["title"])
            h.append(f'<div class="tl-bar-outer" style="left:{left:.2f}%; width:{width:.2f}%">')
            h.append(f'<div class="tl-bar-name" title="{title_esc}">{title_esc}</div>')
            h.append(f'<div class="tl-bar-fill" style="background:{r["color"]}"></div></div>')
        
        h.append('</div></div>')

    h.append('</div>')
    st.markdown("".join(h), unsafe_allow_html=True)

def _get_group_label(task: dict, mode: str) -> str:
    """タスクをどのグループ名で表示するかを決定"""
    if mode == "担当者":
        return task.get("assignee") or "未設定"
    # ステータス（カラム）名
    col_key = task.get("column", "todo")
    return COL_META.get(col_key, {}).get("label", col_key)
