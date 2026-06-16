# ─────────────────────────────────────────────────────────────────────────────
# utils/data_loader.py
# Firebase에서 데이터를 로드하고 DataFrame으로 변환하는 함수 모음
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd

from utils.firebase_init import init_firebase


def _normalize_robot_status(status: object) -> str:
    """외부 시스템 상태값을 대시보드 표준 상태값으로 정규화합니다."""
    if status is None:
        return "대기"

    raw = str(status).strip()
    key = raw.lower()

    mapping = {
        "대기": "대기",
        "waiting": "대기",
        "queued": "대기",
        "queue": "대기",
        "recipe_triggered": "대기",
        "처리중": "처리중",
        "processing": "처리중",
        "in_progress": "처리중",
        "이동중": "이동중",
        "moving": "이동중",
        "서빙중": "서빙중",
        "serving": "서빙중",
        "완료": "완료",
        "done": "완료",
        "completed": "완료",
        "success": "완료",
        "오류": "오류",
        "error": "오류",
        "failed": "오류",
        "failure": "오류",
    }

    return mapping.get(key, raw if raw else "대기")


# ── 얼굴 분석 결과 로드 ────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def load_face_results() -> pd.DataFrame:
    """Firebase face_results_raw → DataFrame"""
    database = init_firebase()
    data = database.reference("face_results_raw").get()
    if not data:
        return pd.DataFrame()

    records = []
    for key, value in data.items():
        items = value if isinstance(value, list) else [value]
        for item in items:
            if not isinstance(item, dict):
                continue
            records.append({
                "face_key":        key,
                "datetime":        item.get("datetime", ""),
                "age":             item.get("age"),
                "gender":          item.get("dominant_gender", ""),
                "emotion":         item.get("dominant_emotion", ""),
                "face_confidence": item.get("face_confidence", 0),
            })

    df = pd.DataFrame(records)
    if not df.empty and "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        df = df.sort_values("datetime", ascending=False).reset_index(drop=True)
    return df


# ── 칵테일 주문 로드 ────────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def load_orders() -> pd.DataFrame:
    """Firebase orders → DataFrame"""
    database = init_firebase()
    data = database.reference("orders").get()
    if not data:
        return pd.DataFrame()

    records = []
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        records.append({
            "order_key": key,
            "datetime":  value.get("datetime", ""),
            "age":       value.get("age"),
            "gender":    value.get("gender", ""),
            "emotion":   value.get("emotion", ""),
            "추천":      value.get("llm_recommendation", ""),
            "LLM 응답":  value.get("llm_response", ""),
            "로봇 상태": _normalize_robot_status(value.get("robot_status", "대기")),
        })

    df = pd.DataFrame(records)
    if not df.empty and "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        df = df.sort_values("datetime", ascending=False).reset_index(drop=True)
    return df


# ── 공통 유틸 ───────────────────────────────────────────────────────────────────
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """DataFrame → UTF-8 BOM CSV bytes (엑셀 호환)"""
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
