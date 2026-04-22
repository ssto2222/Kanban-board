"""
付箋タスク管理アプリ - StickyKanban
ドラッグ＆ドロップで付箋を動かすカンバンボード
"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import json
import os
import uuid
from datetime import datetime, date
import math

# ──────────────────────────────────────────────
# 定数・カラーパレット
# ──────────────────────────────────────────────

COLORS = {
    "bg":        "#1a1a2e",
    "panel":     "#16213e",
    "col_todo":  "#0f3460",
    "col_wip":   "#533483",
    "col_done":  "#1a6b3c",
    "header":    "#e94560",
    "text":      "#eaeaea",
    "subtext":   "#9a9ab0",
    "border":    "#2a2a4a",
    "shadow":    "#0d0d1a",
    "btn":       "#e94560",
    "btn_hover": "#ff6b6b",
    "entry_bg":  "#0f3460",
}

STICKY_COLORS = [
    "#FFD166", "#EF476F", "#06D6A0",
    "#118AB2", "#FFB347", "#C77DFF",
    "#F72585", "#4CC9F0", "#80ED99",
    "#9842f5", "#f2c2ed",
]

COLUMN_DEFS = [
    {"key": "todo",  "label": "📋  待機中",  "color": COLORS["col_todo"]},
    {"key": "wip",   "label": "⚡  進行中",  "color": COLORS["col_wip"]},
    {"key": "done",  "label": "✅  完了",    "color": COLORS["col_done"]},
]

SAVE_FILE = os.path.join(os.path.expanduser("~"), ".sticky_kanban.json")

FONT_TITLE  = ("Helvetica", 11, "bold")
FONT_BODY   = ("Helvetica", 9)
FONT_SMALL  = ("Helvetica", 8)
FONT_HEADER = ("Helvetica", 22, "bold")
FONT_COL    = ("Helvetica", 12, "bold")
FONT_BTN    = ("Helvetica", 10, "bold")

CARD_W  = 200
CARD_H  = 120
CARD_R  = 10   # corner radius
GAP     = 14
PAD_TOP = 60

# ──────────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────────

def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    pts = [
        x1+r, y1, x2-r, y1,
        x2, y1, x2, y1+r,
        x2, y2-r, x2, y2,
        x2-r, y2, x1+r, y2,
        x1, y2, x1, y2-r,
        x1, y1+r, x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)

def lighten(hex_color, factor=0.25):
    hex_color = hex_color.lstrip("#")
    r, g, b = [int(hex_color[i:i+2], 16) for i in (0,2,4)]
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"

def darken(hex_color, factor=0.3):
    hex_color = hex_color.lstrip("#")
    r, g, b = [int(hex_color[i:i+2], 16) for i in (0,2,4)]
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    return f"#{r:02x}{g:02x}{b:02x}"

def days_remaining(deadline_str):
    if not deadline_str:
        return None
    try:
        dl = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        return (dl - date.today()).days
    except Exception:
        return None

# ──────────────────────────────────────────────
# タスクデータ
# ──────────────────────────────────────────────

class Task:
    def __init__(self, title, assignee="", deadline="",
                 color="#FFD166", column="todo", tid=None, note=""):
        self.id       = tid or str(uuid.uuid4())[:8]
        self.title    = title
        self.assignee = assignee
        self.deadline = deadline
        self.color    = color
        self.column   = column
        self.note     = note

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d):
        return cls(
            title    = d.get("title",""),
            assignee = d.get("assignee",""),
            deadline = d.get("deadline",""),
            color    = d.get("color","#FFD166"),
            column   = d.get("column","todo"),
            tid      = d.get("id"),
            note     = d.get("note",""),
        )

# ──────────────────────────────────────────────
# タスク編集ダイアログ
# ──────────────────────────────────────────────

class TaskDialog(tk.Toplevel):
    def __init__(self, master, task=None, on_save=None):
        super().__init__(master)
        self.task    = task
        self.on_save = on_save
        self.result  = None
        self._chosen_color = task.color if task else "#FFD166"

        self.title("タスク編集" if task else "新規タスク")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.grab_set()

        self._build()
        self.update_idletasks()
        # center
        w, h = 380, 380
        sx = master.winfo_rootx() + (master.winfo_width()  - w) // 2
        sy = master.winfo_rooty() + (master.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{sx}+{sy}")

    def _label(self, parent, text):
        tk.Label(parent, text=text, bg=COLORS["bg"],
                 fg=COLORS["subtext"], font=FONT_SMALL).pack(anchor="w")

    def _entry(self, parent, textvariable):
        e = tk.Entry(parent, textvariable=textvariable,
                     bg=COLORS["entry_bg"], fg=COLORS["text"],
                     insertbackground=COLORS["text"],
                     relief="flat", font=FONT_BODY, bd=6)
        e.pack(fill="x", pady=(2, 10))
        return e

    def _build(self):
        f = tk.Frame(self, bg=COLORS["bg"], padx=24, pady=20)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="タスク編集" if self.task else "新規タスク",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0,14))

        self.v_title    = tk.StringVar(value=self.task.title    if self.task else "")
        self.v_assignee = tk.StringVar(value=self.task.assignee if self.task else "")
        self.v_deadline = tk.StringVar(value=self.task.deadline if self.task else "")
        self.v_note     = tk.StringVar(value=self.task.note     if self.task else "")

        self._label(f, "タスク名 *")
        self._entry(f, self.v_title)

        self._label(f, "担当者")
        self._entry(f, self.v_assignee)

        self._label(f, "期限 (YYYY-MM-DD)")
        self._entry(f, self.v_deadline)

        self._label(f, "メモ")
        self._entry(f, self.v_note)

        # color picker row
        cf = tk.Frame(f, bg=COLORS["bg"])
        cf.pack(fill="x", pady=(0,16))
        tk.Label(cf, text="付箋の色", bg=COLORS["bg"],
                 fg=COLORS["subtext"], font=FONT_SMALL).pack(side="left")
        self._color_preview = tk.Label(
            cf, bg=self._chosen_color, width=4, relief="flat", cursor="hand2")
        self._color_preview.pack(side="left", padx=8)
        self._color_preview.bind("<Button-1>", self._pick_color)

        # preset swatches
        for c in STICKY_COLORS:
            sw = tk.Label(cf, bg=c, width=2, relief="flat", cursor="hand2")
            sw.pack(side="left", padx=2)
            sw.bind("<Button-1>", lambda e, col=c: self._set_color(col))

        # buttons
        bf = tk.Frame(f, bg=COLORS["bg"])
        bf.pack(fill="x")
        tk.Button(bf, text="キャンセル", command=self.destroy,
                  bg=COLORS["border"], fg=COLORS["text"],
                  relief="flat", font=FONT_BTN, padx=12, pady=6,
                  cursor="hand2").pack(side="left")
        tk.Button(bf, text="保存",      command=self._save,
                  bg=COLORS["btn"], fg="white",
                  relief="flat", font=FONT_BTN, padx=20, pady=6,
                  cursor="hand2", activebackground=COLORS["btn_hover"]).pack(side="right")
        if self.task:
            tk.Button(bf, text="削除", command=self._delete,
                      bg="#c0392b", fg="white",
                      relief="flat", font=FONT_BTN, padx=12, pady=6,
                      cursor="hand2").pack(side="right", padx=8)

    def _pick_color(self, _=None):
        _, hx = colorchooser.askcolor(color=self._chosen_color, parent=self)
        if hx:
            self._set_color(hx)

    def _set_color(self, c):
        self._chosen_color = c
        self._color_preview.configure(bg=c)

    def _save(self):
        t = self.v_title.get().strip()
        if not t:
            messagebox.showwarning("入力エラー", "タスク名を入力してください", parent=self)
            return
        self.result = {
            "title":    t,
            "assignee": self.v_assignee.get().strip(),
            "deadline": self.v_deadline.get().strip(),
            "color":    self._chosen_color,
            "note":     self.v_note.get().strip(),
            "delete":   False,
        }
        if self.on_save:
            self.on_save(self.result)
        self.destroy()

    def _delete(self):
        if messagebox.askyesno("削除確認", "このタスクを削除しますか？", parent=self):
            self.result = {"delete": True}
            if self.on_save:
                self.on_save(self.result)
            self.destroy()

# ──────────────────────────────────────────────
# カラム (列) ウィジェット
# ──────────────────────────────────────────────

class KanbanColumn(tk.Frame):
    def __init__(self, master, col_def, app, **kw):
        super().__init__(master, bg=COLORS["panel"],
                         highlightbackground=COLORS["border"],
                         highlightthickness=1, **kw)
        self.col_def = col_def
        self.app     = app
        self.key     = col_def["key"]
        self._highlight = False

        self._build_header()
        self._build_canvas()

    def _build_header(self):
        hf = tk.Frame(self, bg=self.col_def["color"], pady=10)
        hf.pack(fill="x")
        tk.Label(hf, text=self.col_def["label"],
                 bg=self.col_def["color"], fg="white",
                 font=FONT_COL).pack(side="left", padx=14)
        self.count_lbl = tk.Label(hf, text="0",
                                   bg=lighten(self.col_def["color"], 0.15),
                                   fg="white", font=FONT_SMALL,
                                   padx=6, pady=2)
        self.count_lbl.pack(side="right", padx=10)

    def _build_canvas(self):
        outer = tk.Frame(self, bg=COLORS["panel"])
        outer.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(outer, bg=COLORS["panel"],
                                highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(outer, orient="vertical",
                            command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)

        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<MouseWheel>",
                         lambda e: self.canvas.yview_scroll(-1*(e.delta//120), "units"))
        self.canvas.bind("<Button-4>",
                         lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>",
                         lambda e: self.canvas.yview_scroll( 1, "units"))

    def _on_resize(self, _=None):
        self.app.render_all()

    def set_highlight(self, on: bool):
        if self._highlight == on:
            return
        self._highlight = on
        color = lighten(self.col_def["color"], 0.1) if on else COLORS["panel"]
        self.canvas.configure(bg=color)

    def update_count(self, n):
        self.count_lbl.configure(text=str(n))

# ──────────────────────────────────────────────
# メインアプリ
# ──────────────────────────────────────────────

class StickyKanbanApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🗒  StickyKanban")
        self.configure(bg=COLORS["bg"])
        self.geometry("1100x700")
        self.minsize(800, 500)

        self.tasks: list[Task] = []
        self._drag_state = None   # drag info dict

        self._build_ui()
        self._load()
        self.render_all()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI構築 ──────────────────────────────────
    def _build_ui(self):
        # トップバー
        top = tk.Frame(self, bg=COLORS["bg"], pady=12)
        top.pack(fill="x", padx=20)

        tk.Label(top, text="🗒  StickyKanban",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=FONT_HEADER).pack(side="left")

        tk.Button(top, text="＋  新規タスク",
                  command=self._new_task,
                  bg=COLORS["btn"], fg="white", relief="flat",
                  font=FONT_BTN, padx=18, pady=8,
                  cursor="hand2",
                  activebackground=COLORS["btn_hover"]).pack(side="right")

        # 検索バー
        sf = tk.Frame(self, bg=COLORS["bg"])
        sf.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(sf, text="🔍", bg=COLORS["bg"], fg=COLORS["subtext"]).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.render_all())
        se = tk.Entry(sf, textvariable=self.search_var,
                      bg=COLORS["entry_bg"], fg=COLORS["text"],
                      insertbackground=COLORS["text"],
                      relief="flat", font=FONT_BODY, bd=6, width=30)
        se.pack(side="left", padx=6)

        # カラム
        cols_frame = tk.Frame(self, bg=COLORS["bg"])
        cols_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))

        self.columns: dict[str, KanbanColumn] = {}
        for i, cd in enumerate(COLUMN_DEFS):
            cols_frame.columnconfigure(i, weight=1)
            col = KanbanColumn(cols_frame, cd, self)
            col.grid(row=0, column=i, sticky="nsew", padx=6, pady=4)
            self.columns[cd["key"]] = col
            cols_frame.rowconfigure(0, weight=1)

    # ── タスク操作 ───────────────────────────────
    def _new_task(self):
        TaskDialog(self, task=None, on_save=self._on_dialog_save)

    def _edit_task(self, task: Task):
        TaskDialog(self, task=task, on_save=lambda r: self._on_dialog_save(r, task))

    def _on_dialog_save(self, result: dict, task: Task = None):
        if result.get("delete") and task:
            self.tasks.remove(task)
        elif task:
            task.title    = result["title"]
            task.assignee = result["assignee"]
            task.deadline = result["deadline"]
            task.color    = result["color"]
            task.note     = result["note"]
        else:
            new_task = Task(
                title    = result["title"],
                assignee = result["assignee"],
                deadline = result["deadline"],
                color    = result["color"],
                note     = result["note"],
                column   = "todo",
            )
            self.tasks.append(new_task)
        self._save()
        self.render_all()

    # ── レンダリング ─────────────────────────────
    def render_all(self):
        q = self.search_var.get().lower()
        for col in self.columns.values():
            col.canvas.delete("all")

        for cd in COLUMN_DEFS:
            key = cd["key"]
            col = self.columns[key]
            tasks_in_col = [t for t in self.tasks
                            if t.column == key and
                            (not q or q in t.title.lower()
                             or q in t.assignee.lower())]
            col.update_count(len(tasks_in_col))
            cw = col.canvas.winfo_width() or 220

            for i, task in enumerate(tasks_in_col):
                x = (cw - CARD_W) // 2
                y = GAP + i * (CARD_H + GAP)
                self._draw_card(col.canvas, task, x, y)

            total_h = GAP + len(tasks_in_col) * (CARD_H + GAP) + 20
            col.canvas.configure(scrollregion=(0, 0, cw, max(total_h, 300)))

    def _draw_card(self, canvas: tk.Canvas, task: Task, x, y):
        # shadow
        rounded_rect(canvas, x+3, y+4, x+CARD_W+3, y+CARD_H+4,
                     CARD_R, fill=COLORS["shadow"], outline="")
        # body
        body_id = rounded_rect(canvas, x, y, x+CARD_W, y+CARD_H,
                               CARD_R, fill=task.color, outline="",
                               tags=(task.id,))
        # top accent strip
        rounded_rect(canvas, x, y, x+CARD_W, y+22,
                     CARD_R, fill=darken(task.color, 0.2), outline="",
                     tags=(task.id,))
        canvas.create_rectangle(x, y+12, x+CARD_W, y+22,
                                 fill=darken(task.color, 0.2), outline="",
                                 tags=(task.id,))

        # title
        canvas.create_text(x+10, y+11, text=task.title,
                            anchor="w", fill="#111",
                            font=FONT_TITLE, width=CARD_W-20,
                            tags=(task.id,))

        # assignee
        if task.assignee:
            canvas.create_text(x+10, y+34, anchor="w",
                                text=f"👤 {task.assignee}",
                                fill="#333", font=FONT_BODY,
                                tags=(task.id,))

        # deadline + days
        if task.deadline:
            days = days_remaining(task.deadline)
            if days is None:
                dl_text = f"📅 {task.deadline}"
                dl_color = "#444"
            elif days < 0:
                dl_text = f"📅 {task.deadline}  (期限切れ {abs(days)}日)"
                dl_color = "#c0392b"
            elif days == 0:
                dl_text = f"📅 {task.deadline}  (本日期限!)"
                dl_color = "#e67e22"
            elif days <= 3:
                dl_text = f"📅 {task.deadline}  (残り{days}日)"
                dl_color = "#e67e22"
            else:
                dl_text = f"📅 {task.deadline}  (残り{days}日)"
                dl_color = "#27ae60"
            canvas.create_text(x+10, y+52, anchor="w",
                                text=dl_text, fill=dl_color,
                                font=FONT_SMALL, tags=(task.id,))

        # note
        if task.note:
            canvas.create_text(x+10, y+70, anchor="w",
                                text=task.note,
                                fill="#555", font=FONT_SMALL,
                                width=CARD_W-20, tags=(task.id,))

        # edit icon
        edit_id = canvas.create_text(x+CARD_W-12, y+10, text="✏️",
                                      font=("Helvetica", 9),
                                      anchor="ne", tags=(task.id, "edit"))

        # bind drag & click
        for item_id in canvas.find_withtag(task.id):
            canvas.tag_bind(item_id, "<ButtonPress-1>",
                            lambda e, t=task: self._drag_start(e, t))
            canvas.tag_bind(item_id, "<B1-Motion>",
                            lambda e, t=task: self._drag_move(e, t))
            canvas.tag_bind(item_id, "<ButtonRelease-1>",
                            lambda e, t=task: self._drag_end(e, t))
            canvas.tag_bind(item_id, "<Double-Button-1>",
                            lambda e, t=task: self._edit_task(t))

        # edit icon single click
        canvas.tag_bind("edit", "<ButtonPress-1>",
                        lambda e, t=task: (e.widget.after(10, lambda: self._edit_task(t))))

    # ── ドラッグ＆ドロップ ────────────────────────
    def _drag_start(self, event, task: Task):
        canvas = event.widget
        # ghost frame
        ghost = tk.Toplevel(self)
        ghost.overrideredirect(True)
        ghost.attributes("-alpha", 0.80)
        ghost.configure(bg=task.color)
        ghost.geometry(f"{CARD_W}x{CARD_H}")
        lbl = tk.Label(ghost, text=task.title, bg=task.color,
                       fg="#111", font=FONT_TITLE, wraplength=CARD_W-20)
        lbl.pack(expand=True)

        self._drag_state = {
            "task":     task,
            "ghost":    ghost,
            "start_xy": (event.x_root, event.y_root),
        }
        self._move_ghost(event)

    def _drag_move(self, event, task: Task):
        if not self._drag_state or self._drag_state["task"] is not task:
            return
        self._move_ghost(event)
        self._highlight_target(event)

    def _drag_end(self, event, task: Task):
        if not self._drag_state or self._drag_state["task"] is not task:
            return
        self._drag_state["ghost"].destroy()

        target_col = self._col_at(event.x_root, event.y_root)
        if target_col and target_col != task.column:
            task.column = target_col
            self._save()

        for col in self.columns.values():
            col.set_highlight(False)

        dx = abs(event.x_root - self._drag_state["start_xy"][0])
        dy = abs(event.y_root - self._drag_state["start_xy"][1])

        self._drag_state = None
        self.render_all()

        # tiny move → treat as click / edit
        if dx < 5 and dy < 5:
            self._edit_task(task)

    def _move_ghost(self, event):
        if not self._drag_state:
            return
        g = self._drag_state["ghost"]
        g.geometry(f"{CARD_W}x{CARD_H}+{event.x_root - CARD_W//2}+{event.y_root - CARD_H//2}")

    def _highlight_target(self, event):
        tk_col = self._col_at(event.x_root, event.y_root)
        for key, col in self.columns.items():
            col.set_highlight(key == tk_col and tk_col != self._drag_state["task"].column)

    def _col_at(self, rx, ry):
        for key, col in self.columns.items():
            cx = col.winfo_rootx()
            cy = col.winfo_rooty()
            cw = col.winfo_width()
            ch = col.winfo_height()
            if cx <= rx <= cx+cw and cy <= ry <= cy+ch:
                return key
        return None

    # ── 保存/読込 ────────────────────────────────
    def _save(self):
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump([t.to_dict() for t in self.tasks], f,
                          ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存エラー: {e}")

    def _load(self):
        if not os.path.exists(SAVE_FILE):
            self._add_samples()
            return
        try:
            with open(SAVE_FILE, encoding="utf-8") as f:
                data = json.load(f)
            self.tasks = [Task.from_dict(d) for d in data]
        except Exception as e:
            print(f"読込エラー: {e}")
            self._add_samples()

    def _add_samples(self):
        today = date.today()
        samples = [
            Task("UIデザイン確認",   "田中",  str(today), "#FFD166", "todo",  "ワイヤーフレームレビュー"),
            Task("APIテスト",         "佐藤",  str(today), "#4CC9F0", "todo",  "エンドポイント全件"),
            Task("バックエンド実装", "鈴木",  "", "#06D6A0", "wip",   "認証モジュール"),
            Task("DB設計",            "田中",  "", "#C77DFF", "wip",   "ER図作成"),
            Task("要件定義",          "高橋",  "", "#EF476F", "done",  "承認済み"),
        ]
        self.tasks = samples
        self._save()

    def _on_close(self):
        self._save()
        self.destroy()

# ──────────────────────────────────────────────

if __name__ == "__main__":
    app = StickyKanbanApp()
    app.mainloop()
