# ─────────────────────────────────────────────────────────────────────────────
# utils/firebase_init.py
# Firebase Realtime Database 초기화 (앱 전체에서 한 번만 수행)
# ─────────────────────────────────────────────────────────────────────────────
import os

import streamlit as st
import firebase_admin
from firebase_admin import credentials, db


@st.cache_resource
def init_firebase():
    """Firebase Admin SDK를 초기화하고 db 모듈을 반환합니다."""
    if not firebase_admin._apps:
        key_path = os.getenv(
            "FIREBASE_KEY_PATH",
            "./serviceAccountKey.json",
        )
        database_url = os.getenv(
            "FIREBASE_DATABASE_URL",
            "https://rokey-d3-default-rtdb.asia-southeast1.firebasedatabase.app/",
        )
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {"databaseURL": database_url})
    return db
