STICKY_COLORS = [
    "#FFD166", "#EF476F", "#06D6A0", "#118AB2", "#FFB347",
    "#C77DFF", "#F72585", "#4CC9F0", "#80ED99", "#9842f5",
    "#f2c2ed",
]

COLUMNS = [
    {"key": "todo", "label": "📋 待機中", "bg": "#0f3460"},
    {"key": "wip",  "label": "⚡ 進行中", "bg": "#533483"},
    {"key": "done", "label": "✅ 完了",   "bg": "#1a6b3c"},
]
COL_KEYS = [c["key"] for c in COLUMNS]
COL_META = {c["key"]: c for c in COLUMNS}

# サイドバーナビゲーション
NAV_PAGES = [
    ("📋 カンバン",   "kanban"),
    ("👤 担当者別",  "assignee"),
    ("📅 タイムライン", "timeline"),
    ("➕ 新規タスク", "new_task"),
]

# 今後追加予定ページ（リンクなし・目次表示のみ）
COMING_SOON = [
    "📊 統計・レポート",
    "🔔 通知設定",
    "👥 チーム管理",
    "⚙️ 設定",
]
