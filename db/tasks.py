import uuid
from datetime import datetime
from .client import get_supabase


def load_tasks() -> list[dict]:
    res = get_supabase().table("tasks").select("*").order("created_at").execute()
    return res.data or []


def create_task(data: dict):
    get_supabase().table("tasks").insert({
        "id":         str(uuid.uuid4()),
        "created_at": datetime.utcnow().isoformat(),
        **data,
    }).execute()


def update_task(task_id: str, data: dict):
    get_supabase().table("tasks").update(data).eq("id", task_id).execute()


def delete_task(task_id: str):
    get_supabase().table("tasks").delete().eq("id", task_id).execute()
