from datetime import datetime, timezone
from .client import get_supabase


def load_tasks() -> list[dict]:
    try:
        res = get_supabase().table("tasks").select("*").order("created_at").execute()
        return res.data or []
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError("タスクの読み込みに失敗しました。") from e


def create_task(data: dict):
    # None / 空文字 / "None" 文字列のフィールドを除外してDBのデフォルト値を活かす
    filtered = {
        k: v for k, v in data.items()
        if v is not None and str(v).strip() != "" and str(v).lower() != "none"
    }
    if "created_at" not in filtered:
        filtered["created_at"] = datetime.now(timezone.utc).isoformat()

    try:
        get_supabase().table("tasks").insert(filtered).execute()
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError("タスクの作成に失敗しました。") from e


def update_task(task_id: str, data: dict):
    try:
        get_supabase().table("tasks").update(data).eq("id", task_id).execute()
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError("タスクの更新に失敗しました。") from e


def delete_task(task_id: str):
    try:
        get_supabase().table("tasks").delete().eq("id", task_id).execute()
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError("タスクの削除に失敗しました。") from e
