-- StickyKanban スキーマ
-- Supabase の SQL Editor で実行してください

-- ── ユーザーテーブル ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id           TEXT        PRIMARY KEY,
    username     TEXT        NOT NULL UNIQUE,
    display_name TEXT        NOT NULL DEFAULT '',
    password_hash TEXT       NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all" ON users FOR ALL USING (true) WITH CHECK (true);

-- ── タスクテーブル ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS tasks (
    id           TEXT        PRIMARY KEY,
    title        TEXT        NOT NULL,
    assignee     TEXT        NOT NULL DEFAULT '',
    deadline     TEXT        NOT NULL DEFAULT '',
    color        TEXT        NOT NULL DEFAULT '#FFD166',
    "column"     TEXT        NOT NULL DEFAULT 'todo',
    note         TEXT        NOT NULL DEFAULT '',
    started_at   TEXT        NOT NULL DEFAULT '',  -- 開始日時 "YYYY-MM-DD HH:MM"
    finished_at  TEXT        NOT NULL DEFAULT '',  -- 終了日時 "YYYY-MM-DD HH:MM"
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 既存テーブルへのカラム追加（既にテーブルがある場合）
-- ALTER TABLE tasks ADD COLUMN IF NOT EXISTS started_at  TEXT NOT NULL DEFAULT '';
-- ALTER TABLE tasks ADD COLUMN IF NOT EXISTS finished_at TEXT NOT NULL DEFAULT '';

-- Row Level Security (RLS) を有効化
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

-- 全操作を許可するポリシー（認証不要の公開アプリ用）
-- 認証が必要な場合はこのポリシーを変更してください
CREATE POLICY "allow_all" ON tasks FOR ALL USING (true) WITH CHECK (true);

-- ── 高所作業車テーブル ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS aerial_lifts (
    id       TEXT    PRIMARY KEY,
    name     TEXT    NOT NULL DEFAULT '',
    floor    INTEGER NOT NULL DEFAULT 1,
    color    TEXT    NOT NULL DEFAULT '#FFD166',
    operator TEXT    NOT NULL DEFAULT '',
    note     TEXT    NOT NULL DEFAULT ''
);

ALTER TABLE aerial_lifts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all" ON aerial_lifts FOR ALL USING (true) WITH CHECK (true);
