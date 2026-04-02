from __future__ import annotations
import html as html_mod
from datetime import datetime, date, timedelta
import streamlit as st
from config import COL_META
from utils.helpers import get_priority_color, parse_dt, JST, darken  # JST, darkenをインポート

# ── 定数 & CSS (大幅に強化) ──────────────────────────────────────────────────

_CSS = """
<style>
/* 全体コンテナ */
.tl-wrap {
    background: #1a1a2e;
    border-radius: 8px;
    padding: 8px 0;
    overflow-x: auto; /* 横スクロール有効 */
    box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
}

/* 軸行 (カレンダーヘッダー) */
.tl-axis-row {
    display: flex;
    align-items: flex-end;
    height: 40px;
    border-bottom: 2px solid #444;
    position: sticky; /* 上部に固定 */
    top: 0;
    background: #1a1a2e;
    z-index: 20;
}
.tl-group-col {
    width: 140px;
    min-width: 140px;
    flex-shrink: 0;
    border-right: 1px solid #444;
}
.tl-chart-col {
    flex: 1;
    position: relative;
    height: 40px;
    min-width: 1000px; /* 最低幅を広げて重なりを軽減 */
}

/* 目盛りテキスト */
.tl-tick {
    position: absolute;
    font-size: 10px;
    color: #9a9ab0;
    text-align: center;
    transform: translateX(-50%);
    line-height: 1.2;
    padding-bottom: 3px;
}
.tl-tick.sat { color: #4ecca3; font-weight: bold; }
.tl-tick.sun { color: #ff4b2b; font-weight: bold; }

/* データ行 (グループごと) */
.tl-row {
    display: flex;
    align-items: stretch;
    /* height は動的に計算されるため指定しない */
    border-bottom: 1px solid #2a2a4a;
    position: relative;
}
.tl-row:hover { background-color: rgba(255,255,255,0.02); } /* ホバー効果 */

/* グループ名ラベル */
.tl-group-name {
    width: 140px;
    min-width: 140px;
    padding: 10px;
    font-size: 12px;
    font-weight: bold;
    color: #eaeaea;
    border-right: 1px solid #2a2a4a;
    display: flex;
    align-items: flex-start; /* 上揃え */
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    box-sizing: border-box;
    background: #1a1a2e;
    position: sticky; /* 左側に固定 */
    left: 0;
    z-index: 15;
}

/* チャート描画エリア */
.tl-chart-area {
    flex: 1;
    position: relative;
    min-width: 1000px;
    /* タスクがない場合の最低の高さを確保 */
    min-height: 60px;
}

/* 背景グリッド線 */
.tl-gridline {
    position: absolute;
    top: 0; bottom: 0;
    width: 1px;
    background: #2a2a4a;
    z-index: 0;
}

/* 今日線 (Red Line) */
.tl-today-line {
    position: absolute;
    top: 0; bottom: 0;
    width: 2px;
    background: #e94560;
    z-index: 10;
    box-shadow: 0 0 4px #e94560;
}

/* 🌟 ガントバー本体 (重なり対策の中核) 🌟 */
.tl-bar-outer {
    position: absolute;
    /* top は動的に計算されるため指定しない */
    height: 24px; /* バーの高さを少し広げる */
    z-index: 2;
    cursor: pointer;
    transition: transform 0.2s; /* ホバー時のアニメーション */
}
.tl-bar-outer:hover {
    transform: scaleY(1.1); /* ホバー時に少し拡大 */
    z-index: 5; /* 前面に持ってくる */
}

/* バーの塗りつぶし */
.tl-bar-fill {
    width: 100%;
    height: 100%;
    border-radius: 12px; /* 丸みを強くして付箋っぽく */
    box-shadow: 1px 2px 5px rgba(0,0,0,0.5);
    border: 1px solid rgba(255,255,255,0.2); /* うっすら枠線 */
    box-sizing: border-box;
    overflow: hidden; /* はみ出した文字を隠す */
    display: flex;
    align-items: center;
    padding: 0 10px;
}

/* 🌟 タスク名テキスト (可読性向上) 🌟 */
.tl-bar-name {
    white-space: nowrap; /* 折り返さない */
    overflow: hidden;
    text-overflow: ellipsis; /* はみ出したら「...」 */
    font-size: 11px;
    font-weight: bold;
    color: #fff; /* 文字色は白固定 */
    /* 文字の可読性を保つための袋文字効果 (黒い縁取り) */
    text-shadow: 
        -1px -1px 0 #000,  
         1px -1px 0 #000,
        -1px  1px 0 #000,
         1px  1px 0 #000,
         0 1px 4px rgba(0,0,0,0.8);
    pointer-events: none; /* テキストへのマウスイベントを無効化 */
    width: 100%;
}
</style>
"""

def _get_wd(dt: datetime) -> str:
    """曜日ラベルを取得"""
    return ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]

def render_timeline(tasks: list[dict]) -> None:
    st.markdown("## 📅 タイムライン")
    st.markdown(_CSS, unsafe_allow_html=True)

    # 「今日」の設定 (Aware datetime)
    today = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)

    # コントロール UI
    ctrl_l, ctrl_r = st.columns(2)
    with ctrl_l: 
        group_by = st.radio("グループ分け", ["担当者", "ステータス"], horizontal=True, key="tl_grp")
    with ctrl_r: 
        view_mode = st.select_slider("表示スパン", options=["日次 (2週間)", "週次 (2ヶ月)", "月次 (6ヶ月)"], key="tl_scale")

    st.divider()

    # 1. データ加工とフィルタリング
    processed_rows = []
    for t in tasks:
        s = parse_dt(t.get("started_at"))
        e = parse_dt(t.get("finished_at"))
        deadline_str = t.get("deadline", "")
        
        # 開始も期限もないタスクは表示できない
        if not s and not deadline_str: continue
        
        # 開始がない場合は期限の前日に設定
        if not s and deadline_str:
            try:
                d_dt = datetime.strptime(deadline_str, "%Y-%m-%d").replace(tzinfo=JST)
                s = d_dt - timedelta(days=1)
            except: continue

        # 終了がない場合は開始の23時間後に設定
        if s and not e:
            e = s + timedelta(hours=23)

        # 期限による色の自動判定
        display_color = get_priority_color(deadline_str, t.get("color", "#FFD166"))

        if s and e and s < e:
            processed_rows.append({
                "id": t.get("id"), # IDを保持
                "title": t.get("title", "無題"),
                "start": s,
                "end": e,
                "group": _get_group_label(t, group_by),
                "color": display_color
            })

    if not processed_rows:
        st.info("表示可能なタスクがありません。開始日時または期限を設定してください。")
        return

    # 2. 表示範囲計算 (Naive/Aware不一致を避ける)
    all_starts = [r["start"] for r in processed_rows] + [today]
    all_ends = [r["end"] for r in processed_rows] + [today]
    
    # 少し余裕を持たせる
    chart_min = min(all_starts) - timedelta(days=3)
    chart_max = max(all_ends) + timedelta(days=7)
    total_secs = (chart_max - chart_min).total_seconds()

    def get_pct(dt: datetime) -> float:
        """日時をチャート内のパーセント位置に変換"""
        # 範囲外の場合はクランプする
        if dt < chart_min: return 0.0
        if dt > chart_max: return 100.0
        return (dt - chart_min).total_seconds() / total_secs * 100

    # 3. 目盛り (Ticks) の生成
    ticks = []
    curr = chart_min.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 表示スパンに応じた間隔設定
    if "日次" in view_mode: interval = timedelta(days=1)
    elif "週次" in view_mode: interval = timedelta(weeks=1)
    else: interval = timedelta(days=30) # 月次

    while curr <= chart_max:
        p = get_pct(curr)
        if 0 <= p <= 100:
            wd = _get_wd(curr)
            if "日次" in view_mode:
                label = f"{curr.strftime('%d')}<br>({wd})"
            else:
                label = curr.strftime("%m/%d")
            ticks.append((p, label, curr.weekday()))
        curr += interval

    # 4. HTML構築開始
    h = ['<div class="tl-wrap">']
    
    # ── 軸行 (カレンダーヘッダー) ──
    h.append('<div class="tl-axis-row">')
    h.append('<div class="tl-group-col"></div>') # グループ名カラム用の空き
    h.append('<div class="tl-chart-col">')
    for p, label, wd in ticks:
        cls = "sat" if wd == 5 else "sun" if wd == 6 else ""
        h.append(f'<div class="tl-tick {cls}" style="left:{p:.2f}%">{label}</div>')
    h.append('</div></div>') # end tl-axis-row

    # ── データ行の生成 (🌟重なり対策の中核🌟) ──
    
    # グループごとにタスクをまとめる
    group_map: dict[str, list] = {}
    for r in processed_rows:
        group_map.setdefault(r["group"], []).append(r)
    
    BAR_HEIGHT = 24  # バーの高さ (CSSと合わせる)
    BAR_MARGIN = 8   # バー同士の縦の間隔
    ROW_PADDING = 15 # 行の上下バッファ

    for grp in sorted(group_map.keys()):
        grp_tasks = group_map[grp]
        
        # 🌟 1. グループ内のタスクを開始日時順にソート
        grp_tasks.sort(key=lambda x: x["start"])
        
        # 🌟 2. 段組み (Lane allocation) ロジック
        # lanesリストの各要素は、その段(行)の最後のタスクの終了日時を保持する
        lanes: list[datetime] = []
        
        task_layout_data = []
        for t in grp_tasks:
            # このタスクを配置できる（＝期間が重ならない）段を探す
            lane_idx = -1
            for i, lane_end_dt in enumerate(lanes):
                # 既存の段の終了時間よりも、このタスクの開始時間が後であれば配置可能
                if t["start"] >= lane_end_dt:
                    lane_idx = i
                    break
            
            if lane_idx == -1:
                # 配置できる段がなければ、新しい段を追加
                lanes.append(t["end"])
                lane_idx = len(lanes) - 1
            else:
                # 見つかった段に配置し、その段の終了時間を更新
                lanes[lane_idx] = t["end"]
            
            # 配置情報（どの段か）をタスクデータに追加
            task_layout_data.append((t, lane_idx))
        
        # このグループに必要な総段数
        total_lanes = len(lanes)
        # 行全体の高さを動的に計算
        row_height = ROW_PADDING * 2 + total_lanes * BAR_HEIGHT + (total_lanes - 1) * BAR_MARGIN
        # タスクがない場合でも最低限の高さを確保
        row_height = max(row_height, 60)

        # ── HTML出力 (行) ──
        h.append(f'<div class="tl-row" style="height:{row_height}px;">')
        # グループ名 (sticky)
        h.append(f'<div class="tl-group-name" title="{html_mod.escape(grp)}">{html_mod.escape(grp)}</div>')
        h.append('<div class="tl-chart-area">')
        
        # 背景グリッド線
        for p, _, _ in ticks:
            h.append(f'<div class="tl-gridline" style="left:{p:.2f}%"></div>')
        
        # 今日線
        tp = get_pct(datetime.now(JST))
        if 0 <= tp <= 100:
            h.append(f'<div class="tl-today-line" style="left:{tp:.2f}%"></div>')
        
        # タスクバーの描画
        for t, lane_idx in task_layout_data:
            left = get_pct(t["start"])
            # 最低限の幅(1.5%)を確保して、短いタスクでも文字が見えるようにする
            width = max(get_pct(t["end"]) - left, 1.5)
            
            # 🌟 Y位置(top)を段数(lane_idx)に基づいて計算
            top_pos = ROW_PADDING + lane_idx * (BAR_HEIGHT + BAR_MARGIN)
            
            title_esc = html_mod.escape(t["title"])
            
            # バー出力
            # note: 文字色は黒系だと見づらいので、helpers.darkenを使ってバーの色を少し暗くし、白文字を際立たせる
            bar_bg = t["color"]
            
            h.append(
                f'<div class="tl-bar-outer" style="left:{left:.2f}%; width:{width:.2f}%; top:{top_pos}px;">'
                f'<div class="tl-bar-fill" style="background:{bar_bg};" title="{title_esc}">'
                f'<div class="tl-bar-name">{title_esc}</div>'
                f'</div>'
                f'</div>'
            )
        
        h.append('</div></div>') # end tl-chart-area, tl-row

    h.append('</div>') # end tl-wrap
    st.markdown("".join(h), unsafe_allow_html=True)

def _get_group_label(task: dict, mode: str) -> str:
    """タスクをどのグループ名で表示するかを決定"""
    if mode == "担当者":
        return task.get("assignee") or "（未設定）"
    # ステータス（カラム）名
    col_key = task.get("column", "todo")
    return COL_META.get(col_key, {}).get("label", col_key)
