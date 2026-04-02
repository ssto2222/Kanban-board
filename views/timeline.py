from __future__ import annotations
import os
import html as html_mod
from datetime import datetime, timedelta
import streamlit as st
from config import COL_META
from utils.helpers import get_priority_color  # 期限色判定をインポート


# ── 定数 ─────────────────────────────────────────────────────────────────────

_TODAY_CL = "#e94560"

_CSS = """
<style>
.tl-wrap {
    overflow-x: auto;
    background: #1a1a2e;
    border-radius: 8px;
    padding: 8px 0 12px;
    user-select: none;
}
/* 軸行 */
.tl-axis-row {
    display: flex;
    align-items: flex-end;
    height: 22px;
    margin-bottom: 2px;
}
.tl-group-col {
    width: 150px;
    min-width: 150px;
    flex-shrink: 0;
    box-sizing: border-box;
}
.tl-chart-col {
    flex: 1;
    position: relative;
    height: 22px;
    overflow: visible;
}
.tl-tick {
    position: absolute;
    font-size: 10px;
    color: #9a9ab0;
    white-space: nowrap;
    transform: translateX(-50%);
    bottom: 0;
}
/* データ行 */
.tl-row {
    display: flex;
    align-items: stretch;
    height: 60px;
    border-bottom: 1px solid #2a2a4a;
}
.tl-row:last-child { border-bottom: none; }
.tl-group-name {
    width: 150px;
    min-width: 150px;
    flex-shrink: 0;
    padding: 0 10px 0 4px;
    font-size: 12px;
    font-weight: 600;
    color: #ccc;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    display: flex;
    align-items: center;
    box-sizing: border-box;
    border-right: 1px solid #2a2a4a;
}
.tl-chart-area {
    flex: 1;
    position: relative;
    overflow: visible;
}
/* グリッド・今日線 */
.tl-gridline {
    position: absolute;
    top: 0; bottom: 0;
    width: 1px;
    background: #2a2a4a;
    z-index: 0;
}
.tl-today-line {
    position: absolute;
    top: 0; bottom: 0;
    width: 2px;
    background: #e94560;
    z-index: 10;
}
.tl-today-label {
    position: absolute;
    top: 2px;
    left: 3px;
    font-size: 9px;
    font-weight: 700;
    color: #e94560;
    white-space: nowrap;
    z-index: 11;
}
/* ガントバー */
.tl-bar-outer {
    position: absolute;
    top: 28px;
    height: 22px;
    z-index: 2;
    min-width: 3px;
}
.tl-bar-fill {
    width: 100%;
    height: 100%;
    border-radius: 4px;
    box-shadow: 1px 2px 5px rgba(0,0,0,.5);
}
.tl-bar-name {
    position: absolute;
    top: -14px;
    left: 0;
    white-space: nowrap;
    font-size: 10px;
    font-weight: 700;
    color: #eaeaea;
    z-index: 5;
    pointer-events: none;
    text-shadow: 0 1px 4px rgba(0,0,0,1), 0 0 6px rgba(0,0,0,.8);
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
}
/* マイルストーン */
.tl-ms {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    z-index: 3;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
}
.tl-ms-name {
    font-size: 10px;
    font-weight: 700;
    color: #eaeaea;
    white-space: nowrap;
    text-shadow: 0 1px 4px rgba(0,0,0,1);
    max-width: 90px;
    overflow: hidden;
    text-overflow: ellipsis;
}
.tl-ms-diamond {
    width: 11px;
    height: 11px;
    transform: rotate(45deg);
    border-radius: 2px;
    box-shadow: 0 1px 4px rgba(0,0,0,.6);
}
.tl-ms-diamond-open {
    width: 11px;
    height: 11px;
    transform: rotate(45deg);
    border-radius: 2px;
    border: 2px solid;
    box-sizing: border-box;
    background: transparent;
}
.tl-ms-triangle {
    width: 0; height: 0;
    border-left: 7px solid transparent;
    border-right: 7px solid transparent;
    border-top: 12px solid;
}
/* 凡例 */
.tl-legend {
    display: flex;
    gap: 18px;
    padding: 6px 10px;
    font-size: 11px;
    color: #ccc;
    flex-wrap: wrap;
}
.tl-legend-item {
    display: flex;
    align-items: center;
    gap: 5px;
}
.tl-legend-diamond {
    width: 9px; height: 9px;
    transform: rotate(45deg);
    background: #9a9ab0;
    border-radius: 1px;
}
.tl-legend-diamond-open {
    width: 9px; height: 9px;
    transform: rotate(45deg);
    border: 2px solid #9a9ab0;
    border-radius: 1px;
    box-sizing: border-box;
}
.tl-legend-triangle {
    width: 0; height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 9px solid #9a9ab0;
}
</style>
"""

def _parse_dt(s: str) -> datetime | None:
    if not s or s == "None" or s == "": return None
    # 各種フォーマットに対応
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            clean_s = s.replace("T", " ")[:16]
            if len(clean_s) > 10:
                return datetime.strptime(clean_s, "%Y-%m-%d %H:%M")
            else:
                return datetime.strptime(clean_s, "%Y-%m-%d")
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
    st.markdown(_CSS, unsafe_allow_html=True)

    ctrl_l, ctrl_r = st.columns(2)
    with ctrl_l:
        group_by = st.radio("グループ分け", ["担当者", "ステータス"], horizontal=True, key="tl_grp")
    
    with ctrl_r:
        view_mode = st.select_slider(
            "表示スパン",
            options=["日次 (2週間)", "週次 (2ヶ月)", "月次 (6ヶ月)"],
            value="日次 (2週間)",
            key="tl_scale"
        )

    st.divider()

    html = _gantt_html(tasks, group_by, view_mode)

    if html is None:
        st.info("表示できるタスクがありません。開始日時または期限が設定されたタスクを追加してください。")
        return

    st.markdown(html, unsafe_allow_html=True)


# ── ガントチャート ────────────────────────────────────────────────────────────

_SPAN_DAYS = {
    "日次 (2週間)": 14,
    "週次 (2ヶ月)": 60,
    "月次 (6ヶ月)": 180,
}


def _gantt_html(tasks: list[dict], group_by: str, view_mode: str = "日次 (2週間)") -> str | None:
    rows = []
    for t in tasks:
        s = _parse_dt(t.get("started_at", ""))
        e = _parse_dt(t.get("finished_at", ""))
        d = _parse_date(t.get("deadline", ""))

        if s is None and d is None:
            continue

        if s is None:
            s = datetime.combine(d - timedelta(days=1), datetime.min.time())  # type: ignore[arg-type]
        if e is None:
            e = datetime.combine(d, datetime.min.time()) if d else s + timedelta(days=1)
        if e <= s:
            e = s + timedelta(hours=1)

        rows.append({
            "title": t.get("title", ""),
            "start": s,
            "end":   e,
            "group": _get_group(t, group_by),
            "color": t.get("color", "#FFD166"),
        })

    if not rows:
        return None

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    span = _SPAN_DAYS.get(view_mode, 14)
    # 表示スパンを今日を中心に設定し、タスクがはみ出す場合は拡張
    all_dates = [r["start"] for r in rows] + [r["end"] for r in rows]
    min_dt = min(min(all_dates), today - timedelta(days=span // 4))
    max_dt = max(max(all_dates), today + timedelta(days=span * 3 // 4))
    if (max_dt - min_dt).days < span:
        max_dt = min_dt + timedelta(days=span)

    pct = _make_pct(min_dt, max_dt)
    ticks = _month_ticks(min_dt, max_dt, pct)
    today_pct = pct(today)

    group_tasks: dict[str, list] = {}
    for r in rows:
        group_tasks.setdefault(r["group"], []).append(r)
    groups = sorted(group_tasks.keys())

    h: list[str] = []
    h.append('<div class="tl-wrap">')
    h += _axis_row(ticks)

    for grp in groups:
        h.append('<div class="tl-row">')
        h.append(f'<div class="tl-group-name" title="{html_mod.escape(grp)}">{html_mod.escape(grp)}</div>')
        h.append('<div class="tl-chart-area">')
        h += _bg_lines(ticks, today_pct)

        for r in group_tasks[grp]:
            left  = pct(r["start"])
            width = max(pct(r["end"]) - left, 0.4)
            label = html_mod.escape(r["title"])
            color = r["color"]
            h.append(
                f'<div class="tl-bar-outer" style="left:{left:.3f}%;width:{width:.3f}%">'
                f'<div class="tl-bar-name">{label}</div>'
                f'<div class="tl-bar-fill" style="background:{color}" title="{label}"></div>'
                f'</div>'
            )

        h.append('</div></div>')

    h.append('</div>')
    return "".join(h)


# ── マイルストーン ────────────────────────────────────────────────────────────

def _milestone_html(tasks: list[dict], group_by: str) -> str | None:
    items: list[dict] = []
    for t in tasks:
        grp   = _get_group(t, group_by)
        color = t.get("color", "#FFD166")
        title = t.get("title", "")

        s = _parse_dt(t.get("started_at", ""))
        e = _parse_dt(t.get("finished_at", ""))
        d = _parse_date(t.get("deadline", ""))

        if s:
            items.append({"dt": s, "group": grp, "color": color, "title": title, "kind": "start"})
        if e:
            items.append({"dt": e, "group": grp, "color": color, "title": title, "kind": "end"})
        if d and not e:
            items.append({"dt": datetime.combine(d, datetime.min.time()),
                          "group": grp, "color": color, "title": title, "kind": "deadline"})

    if not items:
        return None

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    all_dates = [i["dt"] for i in items] + [today]
    min_dt = min(all_dates) - timedelta(days=3)
    max_dt = max(all_dates) + timedelta(days=3)
    if (max_dt - min_dt).days < 7:
        max_dt = min_dt + timedelta(days=7)

    pct = _make_pct(min_dt, max_dt)
    ticks = _month_ticks(min_dt, max_dt, pct)
    today_pct = pct(today)

    group_items: dict[str, list] = {}
    for item in items:
        group_items.setdefault(item["group"], []).append(item)
    groups = sorted(group_items.keys())

    h: list[str] = []
    h.append('<div class="tl-wrap">')
    h += _axis_row(ticks)

    for grp in groups:
        h.append('<div class="tl-row">')
        h.append(f'<div class="tl-group-name" title="{html_mod.escape(grp)}">{html_mod.escape(grp)}</div>')
        h.append('<div class="tl-chart-area">')
        h += _bg_lines(ticks, today_pct)

        for item in group_items[grp]:
            x     = pct(item["dt"])
            label = html_mod.escape(item["title"])
            color = item["color"]
            kind  = item["kind"]

            if kind == "deadline":
                marker = f'<div class="tl-ms-triangle" style="border-top-color:{color}" title="{label}▼期限"></div>'
            elif kind == "end":
                marker = f'<div class="tl-ms-diamond-open" style="border-color:{color}" title="{label}◇終了"></div>'
            else:
                marker = f'<div class="tl-ms-diamond" style="background:{color}" title="{label}◆開始"></div>'

            h.append(
                f'<div class="tl-ms" style="left:{x:.3f}%">'
                f'<div class="tl-ms-name" title="{label}">{label}</div>'
                f'{marker}'
                f'</div>'
            )

        h.append('</div></div>')

    # 凡例
    h.append(
        '<div class="tl-legend">'
        '<div class="tl-legend-item"><div class="tl-legend-diamond"></div>開始</div>'
        '<div class="tl-legend-item"><div class="tl-legend-diamond-open"></div>終了</div>'
        '<div class="tl-legend-item"><div class="tl-legend-triangle"></div>期限</div>'
        '</div>'
    )
    h.append('</div>')
    return "".join(h)


# ── 共通HTML部品 ──────────────────────────────────────────────────────────────

def _axis_row(ticks: list[tuple[float, str]]) -> list[str]:
    h = ['<div class="tl-axis-row"><div class="tl-group-col"></div>']
    h.append('<div class="tl-chart-col">')
    for p, label in ticks:
        h.append(f'<div class="tl-tick" style="left:{p:.3f}%">{label}</div>')
    h.append('</div></div>')
    return h


def _bg_lines(ticks: list[tuple[float, str]], today_pct: float) -> list[str]:
    h = []
    for p, _ in ticks:
        h.append(f'<div class="tl-gridline" style="left:{p:.3f}%"></div>')
    if 0 <= today_pct <= 100:
        h.append(f'<div class="tl-today-line" style="left:{today_pct:.3f}%"></div>')
        h.append(f'<div class="tl-today-label" style="left:{today_pct:.3f}%">今日</div>')
    return h


# ── ヘルパー ──────────────────────────────────────────────────────────────────

def _make_pct(min_dt: datetime, max_dt: datetime):
    total_secs = (max_dt - min_dt).total_seconds()

    def pct(dt: datetime) -> float:
        return (dt - min_dt).total_seconds() / total_secs * 100

    return pct


def _month_ticks(min_dt: datetime, max_dt: datetime, pct) -> list[tuple[float, str]]:
    ticks = []
    cur = min_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    while cur <= max_dt:
        p = pct(cur)
        if 0 <= p <= 100:
            ticks.append((p, cur.strftime("%Y/%m")))
        cur = (cur.replace(month=cur.month + 1) if cur.month < 12
               else cur.replace(year=cur.year + 1, month=1))
    return ticks


def _get_group(task: dict, group_by: str) -> str:
    if group_by == "担当者":
        return task.get("assignee") or "（未割り当て）"
    col_key = task.get("column", "todo")
    return COL_META.get(col_key, {}).get("label", col_key)


def _parse_dt(s: str) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def _parse_date(s: str) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None
