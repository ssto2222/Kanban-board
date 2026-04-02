from __future__ import annotations
from datetime import datetime, timedelta
import plotly.graph_objects as go
import streamlit as st
from config import COL_META
from utils.helpers import get_priority_color, parse_dt, JST


def _get_wd(dt: datetime) -> str:
    return ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]


def render_timeline(tasks: list[dict]) -> None:
    st.markdown("## 📅 タイムライン (未完了のみ)")

    today = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)

    # ── 1. コントロールパネル ─────────────────────
    ctrl_l, ctrl_r = st.columns(2)
    with ctrl_l:
        group_by = st.radio("グループ分け", ["担当者", "ステータス"], horizontal=True, key="tl_grp")
    with ctrl_r:
        view_mode = st.select_slider(
            "表示スパン",
            options=["日次 (2週間)", "週次 (2ヶ月)", "月次 (6ヶ月)", "年次 (12ヶ月)"],
            value="日次 (2週間)",
            key="tl_scale"
        )

    # ── 2. 表示範囲の決定 ──────────────────
    if "日次" in view_mode:
        days_back, days_fwd = 3, 11
    elif "週次" in view_mode:
        days_back, days_fwd = 14, 46
    elif "月次" in view_mode:
        days_back, days_fwd = 30, 150
    else:
        days_back, days_fwd = 30, 335

    chart_min = today - timedelta(days=days_back)
    chart_max = today + timedelta(days=days_fwd)

    # ── 3. データ加工 ──────────────────────────
    processed_rows: list[dict] = []
    task_lookup: dict[str, dict] = {}

    for t in tasks:
        if t.get("column") == "done":
            continue
        task_id = t.get("id")
        if not task_id:
            continue

        title = t.get("title", "無題")
        is_ms = "🔷" in title
        s = parse_dt(t.get("started_at"))
        e = parse_dt(t.get("finished_at"))
        deadline_str = t.get("deadline", "")
        status = t.get("column", "todo")

        if not s and deadline_str:
            try:
                d_dt = datetime.strptime(deadline_str, "%Y-%m-%d").replace(tzinfo=JST)
                s, e = d_dt - timedelta(days=1), d_dt
            except Exception:
                continue

        if not s:
            continue
        if s and not e:
            e = s + timedelta(hours=23)
        if e < chart_min or s > chart_max:
            continue

        display_color = get_priority_color(deadline_str, t.get("color", "#FFD166"), column=status)

        processed_rows.append({
            "id":    task_id,
            "title": title,
            "start": max(s, chart_min),
            "end":   min(e, chart_max),
            "group": _get_group_label(t, group_by),
            "color": display_color,
            "is_ms": is_ms,
        })
        task_lookup[task_id] = t

    # ── 4. Plotly タイムライン ────────────────────
    from components.dialog import task_dialog

    if not processed_rows:
        st.info("表示できるタスクがありません（期限・作業期間が未設定、または完了済み）。")
    else:
        fig = _build_plotly_timeline(processed_rows, chart_min, chart_max, today)
        st.plotly_chart(
            fig,
            use_container_width=True,
            key="timeline_chart",
            on_select="rerun",
        )

        # ── 5. クリックイベント処理 ───────────────────
        chart_state = st.session_state.get("timeline_chart")
        if chart_state and getattr(chart_state, "selection", None):
            pts = chart_state.selection.points
            if pts:
                tid = pts[0].get("customdata")
                if tid and tid in task_lookup:
                    st.session_state[f"_open_dialog_{tid}"] = True
                    st.session_state["timeline_chart"] = None
                    st.rerun()

    for tid, orig_task in task_lookup.items():
        if st.session_state.pop(f"_open_dialog_{tid}", False):
            task_dialog(orig_task)
            break


def _build_plotly_timeline(
    processed_rows: list[dict],
    chart_min: datetime,
    chart_max: datetime,
    today: datetime,
) -> go.Figure:
    group_map: dict[str, list] = {}
    for r in processed_rows:
        group_map.setdefault(r["group"], []).append(r)

    y_labels: list[str] = []
    bases: list[datetime] = []
    durations: list[int] = []
    colors: list[str] = []
    custom: list[str] = []
    texts: list[str] = []
    borders: list[str] = []

    for grp in sorted(group_map.keys()):
        grp_tasks = sorted(group_map[grp], key=lambda x: x["start"])
        lanes: list[datetime] = []
        for t in grp_tasks:
            lane_idx = next(
                (i for i, end in enumerate(lanes) if t["start"] >= end), -1
            )
            if lane_idx == -1:
                lanes.append(t["end"])
                lane_idx = len(lanes) - 1
            else:
                lanes[lane_idx] = t["end"]

            y_label = grp if lane_idx == 0 else f"{grp} [{lane_idx}]"
            duration_ms = max(
                int((t["end"] - t["start"]).total_seconds() * 1000),
                3_600_000,  # 最低1時間分の幅
            )

            y_labels.append(y_label)
            bases.append(t["start"])
            durations.append(duration_ms)
            colors.append(t["color"])
            custom.append(t["id"])
            texts.append(t["title"])
            borders.append("white" if t.get("is_ms") else "rgba(255,255,255,0.3)")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        orientation="h",
        y=y_labels,
        x=durations,
        base=bases,
        marker=dict(
            color=colors,
            line=dict(
                color=borders,
                width=[2 if b == "white" else 1 for b in borders],
            ),
        ),
        text=texts,
        textposition="inside",
        insidetextanchor="start",
        textfont=dict(size=11, color="white"),
        customdata=custom,
        hovertemplate="<b>%{text}</b><extra></extra>",
        showlegend=False,
        selected=dict(marker=dict(opacity=1.0)),
        unselected=dict(marker=dict(opacity=0.4)),
    ))

    # 今日の縦線
    fig.add_vline(
        x=today.timestamp() * 1000,
        line_width=2,
        line_color="#e94560",
        opacity=0.9,
    )

    chart_height = max(400, 50 * len(set(y_labels)) + 80)

    fig.update_layout(
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#1a1a2e",
        font=dict(color="#eaeaea", size=11),
        margin=dict(l=160, r=20, t=30, b=40),
        height=chart_height,
        xaxis=dict(
            type="date",
            range=[chart_min.isoformat(), chart_max.isoformat()],
            gridcolor="#2a2a4a",
            tickfont=dict(color="#9a9ab0", size=10),
            showgrid=True,
        ),
        yaxis=dict(
            gridcolor="#2a2a4a",
            tickfont=dict(color="#eaeaea", size=11),
            autorange="reversed",
        ),
        dragmode="select",
        bargap=0.3,
    )
    return fig


def _get_group_label(task: dict, mode: str) -> str:
    if mode == "担当者":
        return task.get("assignee") or "（未設定）"
    return COL_META.get(task.get("column", "todo"), {}).get("label", "不明")
