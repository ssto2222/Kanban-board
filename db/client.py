import os
import streamlit as st
from supabase import create_client

@st.cache_resource
def get_supabase():
    # 1. まず os.environ (Heroku) を確認
    # 2. なければ st.secrets (ローカル/Streamlit Cloud) を確認
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

    if not url or not key:
        st.error("Supabaseの認証情報が見つかりません。HerokuのConfig Varsまたはsecrets.tomlを確認してください。")
        st.stop()

    return create_client(url, key)
