-- StickyKanban タスクテーブル
-- Supabase の SQL Editor で実行してください

CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT        PRIMARY KEY,
    title       TEXT        NOT NULL,
    assignee    TEXT        NOT NULL DEFAULT '',
    deadline    TEXT        NOT NULL DEFAULT '',
    color       TEXT        NOT NULL DEFAULT '#FFD166',
    "column"    TEXT        NOT NULL DEFAULT 'todo',
    note        TEXT        NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Row Level Security (RLS) を有効化
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

-- 全操作を許可するポリシー（認証不要の公開アプリ用）
-- 認証が必要な場合はこのポリシーを変更してください
CREATE POLICY "allow_all" ON tasks FOR ALL USING (true) WITH CHECK (true);
