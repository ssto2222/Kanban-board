import uuid
from datetime import datetime
from .client import get_supabase
from supabase import create_client


def load_tasks() -> list[dict]:
    res = get_supabase().table("tasks").select("*").order("created_at").execute()
    return res.data or []


def create_task(data: dict):
    """タスクを新規作成する"""
    # 値が None または "" (空文字) のキーは、DBの自動デフォルト値に任せるため除外する
    # これにより、id などの自動生成カラムが正しく動作します
    filtered_data = {k: v for k, v in data.items() if v is not None and v != ""}
    
    return get_supabase().table("tasks").insert(filtered_data).execute()
    
    get_supabase().table("tasks").insert({
        "id":         str(uuid.uuid4()),
        "created_at": datetime.utcnow().isoformat(),
        **data,
    }).execute()


def update_task(task_id: str, data: dict):
    get_supabase().table("tasks").update(data).eq("id", task_id).execute()


def delete_task(task_id: str):
    get_supabase().table("tasks").delete().eq("id", task_id).execute()
