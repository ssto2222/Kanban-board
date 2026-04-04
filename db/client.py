import os
from supabase import create_client


def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Supabaseの認証情報が見つかりません。環境変数 SUPABASE_URL / SUPABASE_KEY を設定してください。"
        )
    return create_client(url, key)
