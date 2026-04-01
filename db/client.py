import os
import streamlit as st
from supabase import create_client

@st.cache_resource
def get_supabase():
    # 1. まずStreamlitのSecretsを確認し、なければ環境変数を探す
    url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")

    if not url or not key:
        st.error("Supabaseの認証情報が見つかりません。")
        st.stop()

    return create_client(url, key)
