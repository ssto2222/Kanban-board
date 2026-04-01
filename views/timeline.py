from __future__ import annotations

import html as html_mod
from datetime import datetime, date, timedelta

import streamlit as st

from config import COL_META

try:
    import plotly.graph_objects as go
    import plotly.express as px
    import pandas as pd
    _PLOTLY_OK = True
except ImportError:
    _PLOTLY_OK = False


# ── 定数 ─────────────────────────────────────────────────────────────────────

_BG       = "#1a1a2e"
_GRID     = "#2a2a4a"
_TEXT     = "#eaeaea"
_TODAY_CL = "#e94560"

# ホバーカードのテンプレート
_HOVER_TMPL = (
    "<span style='font-size:13px;font-weight:bold'>%{customdata[0]}</span><br>"
    "👤 %{customdata[1]}<br>"
    "📋 %{customdata[2]}<br>"
    "📅 期限: %{customdata[3]}<br>"
    "🕐 %{customdata[4]} → %{customdata[5]}<br>"
    "<i style='color:#aaa;font-size:10px'>%{customdata[6]}</i>"
    "<extra></extra>"
)


# ── パブリック ────────────────────────────────────────────────────────────────

def render_timeline(tasks: list[dict]) -> None:
    """タイムラインページ（ガントチャート / マイルストーン）。"""

    if not _PLOTLY_OK:
        st.error("Plotly と pandas が必要です。`pip install plotly pandas` を実行してください。")
        return

    st.markdown("## 📅 タイムライン")

    ctrl_l, ctrl_r = st.columns(2)
    with ctrl_l:
        mode = st.radio(
            "表示モード",
            ["📊 ガントチャート", "🔷 マイルストーン"],
            horizontal=True,
            key="tl_mode",
        )
    with ctrl_r:
        group_by = st.radio(
            "グループ",
            ["担当者", "ステータス"],
            horizontal=True,
            key="tl_group",
        )

    st.divider()

    if mode == "📊 ガントチャート":
        fig = _build_gantt(tasks, group_by)
    else:
        fig = _build_milestone(tasks, group_by)

    if fig is None:
        st.info("表示できるタスクがありません。開始日時または期限が設定されたタスクを追加してください。")
        return

    st.plotly_chart(fig, use_container_width=True)


# ── ガントチャート ────────────────────────────────────────────────────────────

def _build_gantt(tasks: list[dict], group_by: str):
    """開始日〜終了日（または期限）のバーを描画する。"""
    rows = []
    for t in tasks:
        start_dt = _parse_dt(t.get("started_at", ""))
        end_dt   = _parse_dt(t.get("finished_at", ""))
        dl_dt    = _parse_date(t.get("deadline", ""))

        if start_dt is None and dl_dt is None:
            continue

        if start_dt is None:
            start_dt = datetime.combine(dl_dt - timedelta(days=1), datetime.min.time())  # type: ignore[arg-type]

        if end_dt is None:
            if dl_dt:
                end_dt = datetime.combine(dl_dt, datetime.min.time())
            else:
                end_dt = start_dt + timedelta(days=1)

        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(hours=1)

        note = (t.get("note") or "").strip()
        note_short = (note[:40] + "…") if len(note) > 40 else note

        rows.append({
            "Task":      html_mod.escape(t.get("title", "")),
            "Start":     start_dt,
            "Finish":    end_dt,
            "Group":     _get_group(t, group_by),
            "Color":     t.get("color", "#FFD166"),
            "Assignee":  t.get("assignee") or "―",
            "Status":    COL_META.get(t.get("column", "todo"), {}).get("label", ""),
            "Deadline":  t.get("deadline") or "―",
            "StartStr":  start_dt.strftime("%Y-%m-%d"),
            "FinishStr": end_dt.strftime("%Y-%m-%d"),
            "Note":      note_short,
        })

    if not rows:
        return None

    df = pd.DataFrame(rows)
    groups = sorted(df["Group"].unique())

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Group",
        text="Task",
        color="Color",
        color_discrete_map={c: c for c in df["Color"].unique()},
        category_orders={"Group": groups},
        custom_data=["Task", "Assignee", "Status", "Deadline", "StartStr", "FinishStr", "Note"],
    )

    fig.update_traces(
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="#111", size=11),
        marker_line_width=0,
        hovertemplate=_HOVER_TMPL,
    )

    _add_today_line(fig)
    _apply_dark_theme(fig, groups)
    return fig


# ── マイルストーン ────────────────────────────────────────────────────────────

def _build_milestone(tasks: list[dict], group_by: str):
    """日付を持つタスクをダイヤモンドマーカーとカードラベルで描画する。"""
    start_rows, end_rows, dl_rows = [], [], []

    for t in tasks:
        group    = _get_group(t, group_by)
        color    = t.get("color", "#FFD166")
        title    = html_mod.escape(t.get("title", ""))
        assignee = t.get("assignee") or "―"
        status   = COL_META.get(t.get("column", "todo"), {}).get("label", "")
        deadline = t.get("deadline") or "―"
        note     = (t.get("note") or "").strip()
        note_s   = (note[:40] + "…") if len(note) > 40 else note

        s = _parse_dt(t.get("started_at", ""))
        e = _parse_dt(t.get("finished_at", ""))
        d = _parse_date(t.get("deadline", ""))

        base = dict(y=group, text=title, color=color,
                    assignee=assignee, status=status, deadline=deadline,
                    note=note_s)

        if s:
            start_rows.append({**base, "x": s,
                                "start_s": s.strftime("%Y-%m-%d"),
                                "end_s": e.strftime("%Y-%m-%d") if e else "―"})
        if e:
            end_rows.append({**base, "x": e,
                              "start_s": s.strftime("%Y-%m-%d") if s else "―",
                              "end_s": e.strftime("%Y-%m-%d")})
        if d and not e:
            dl_rows.append({**base, "x": datetime.combine(d, datetime.min.time()),
                             "start_s": s.strftime("%Y-%m-%d") if s else "―",
                             "end_s": d.strftime("%Y-%m-%d")})

    all_rows = start_rows + end_rows + dl_rows
    if not all_rows:
        return None

    df_all = pd.DataFrame(all_rows)
    groups = sorted(df_all["y"].unique())

    fig = go.Figure()

    def _add_scatter(rows, symbol, marker_name):
        if not rows:
            return
        df = pd.DataFrame(rows)
        for grp in groups:
            sub = df[df["y"] == grp]
            if sub.empty:
                continue
            cd = sub[["text", "assignee", "status", "deadline",
                       "start_s", "end_s", "note"]].values
            fig.add_trace(go.Scatter(
                x=sub["x"],
                y=sub["y"],
                mode="markers+text",
                marker=dict(
                    symbol=symbol, size=16,
                    color=sub["color"].tolist(),
                    line=dict(color="#fff", width=1.5),
                ),
                text=sub["text"],
                textposition="top center",
                textfont=dict(color=_TEXT, size=10),
                name=marker_name,
                showlegend=True,
                customdata=cd,
                hovertemplate=_HOVER_TMPL,
            ))

    _add_scatter(start_rows, "diamond",       "開始")
    _add_scatter(end_rows,   "diamond-open",  "終了")
    _add_scatter(dl_rows,    "triangle-down", "期限")

    _add_today_line(fig)
    _apply_dark_theme(fig, groups)

    fig.update_layout(
        showlegend=True,
        legend=dict(
            bgcolor=_GRID,
            font=dict(color=_TEXT),
            orientation="h",
            y=1.05,
        ),
    )
    return fig


# ── ヘルパー ──────────────────────────────────────────────────────────────────

def _add_today_line(fig) -> None:
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    fig.add_vline(
        x=today.timestamp() * 1000,
        line_width=2,
        line_dash="dash",
        line_color=_TODAY_CL,
        annotation_text="今日",
        annotation_font_color=_TODAY_CL,
        annotation_position="top right",
    )


def _apply_dark_theme(fig, groups: list[str]) -> None:
    fig.update_layout(
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        font=dict(color=_TEXT),
        xaxis=dict(
            gridcolor=_GRID,
            zeroline=False,
            showline=False,
            tickfont=dict(color=_TEXT),
        ),
        yaxis=dict(
            gridcolor=_GRID,
            zeroline=False,
            showline=False,
            tickfont=dict(color=_TEXT),
            categoryorder="array",
            categoryarray=groups,
        ),
        margin=dict(l=10, r=10, t=40, b=10),
        height=max(320, 100 + 70 * len(groups)),
        showlegend=False,
    )


def _get_group(task: dict, group_by: str) -> str:
    if group_by == "担当者":
        return task.get("assignee") or "（未割り当て）"
    col_key = task.get("column", "todo")
    return COL_META.get(col_key, {}).get("label", col_key)


def _parse_dt(s: str) -> datetime | None:
    """'YYYY-MM-DD HH:MM' または 'YYYY-MM-DD' を datetime に変換。"""
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
