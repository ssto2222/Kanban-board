import streamlit as st
from datetime import datetime, timezone
from db.client import get_supabase

def load_tasks() -> list[dict]:
    """全タスクを読み込み、作成日時順に並べる"""
    try:
        res = get_supabase().table("tasks").select("*").order("created_at").execute()
        return res.data or []
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        return []

def create_task(data: dict):
    """
    タスクまたはマイルストーンを新規作成する。
    DB側のIdentity（自動採番）やDefault値を活かすため、空の項目は除外して送信する。
    """
    # 1. データのクリーニング
    # 値が None, "", "None" (文字列) のものは除外して、DB側のデフォルト値（idの自動採番など）を機能させる
    filtered_data = {
        k: v for k, v in data.items() 
        if v is not None and str(v).strip() != "" and str(v).lower() != "none"
    }

    # 2. 作成日時の明示（DB側で設定されている場合は不要ですが、アプリ側で制御する場合）
    if "created_at" not in filtered_data:
        filtered_data["created_at"] = datetime.now(timezone.utc).isoformat()

    # 3. 実行
    try:
        return get_supabase().table("tasks").insert(filtered_data).execute()
    except Exception as e:
        st.error(f"タスク登録エラー: {e}")
        # IDエラーが続く場合は、Supabaseのidカラム設定(Is Identity)を確認するよう促す
        if "23502" in str(e) and "id" in str(e):
            st.warning("⚠️ Supabase側の 'id' カラム設定で 'Is Identity' が ON になっているか確認してください。")
        raise e

def update_task(task_id: str, data: dict):
    """指定したIDのタスクを更新する"""
    try:
        return get_supabase().table("tasks").update(data).eq("id", task_id).execute()
    except Exception as e:
        st.error(f"更新エラー: {e}")
        raise e

def delete_task(task_id: str):
    """指定したIDのタスクを削除する"""
    try:
        return get_supabase().table("tasks").delete().eq("id", task_id).execute()
    except Exception as e:
        st.error(f"削除エラー: {e}")
        raise e
