import os

# 환경변수로 오버라이드 가능 (Docker 환경에서 유연하게 설정)
SERVICE_ACCOUNT_KEY_PATH: str = os.getenv(
    "FIREBASE_KEY_PATH",
    "./firebase/serviceAccountKey.json",
)

DATABASE_URL: str = os.getenv(
    "FIREBASE_DATABASE_URL",
    "https://rokey-d3-default-rtdb.asia-southeast1.firebasedatabase.app/",
)

# Firebase Realtime Database 경로 상수
PATH_FACE_RESULTS = "face_results_raw"
PATH_ORDERS = "orders"
