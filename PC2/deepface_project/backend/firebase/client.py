import firebase_admin
from firebase_admin import credentials, db
from firebase.config import SERVICE_ACCOUNT_KEY_PATH, DATABASE_URL


def get_db():
    """Firebase Realtime Database 클라이언트를 반환합니다. (싱글톤)"""
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
        firebase_admin.initialize_app(cred, {"databaseURL": DATABASE_URL})
    return db
