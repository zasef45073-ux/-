import os
# GPU를 사용하는 경우 CUDA_VISIBLE_DEVICES를 설정하지 않음
# CPU 전용 모드가 필요하면: os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from deepface import DeepFace
import cv2
import numpy as np
from datetime import datetime
from typing import Optional
from firebase import database as fb

# FastAPI 앱 초기화
app = FastAPI(
    title="DeepFace API Server",
    description="DeepFace 얼굴 분석 + LLM 주문 수신 + ROS2 연동 API",
    version="2.0.0"
)

# ── 웹캠 자동 탐지 ──────────────────────────────────────────────────────────────
def find_webcam_index() -> Optional[int]:
    """0~4번 인덱스를 순서대로 탐색해 사용 가능한 첫 번째 웹캠을 반환합니다."""
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            if ret:
                print(f"[웹캠] /dev/video{i} (인덱스 {i}) 자동 탐지 완료")
                return i
        cap.release()
    print("[웹캠] 사용 가능한 웹캠을 찾지 못했습니다.")
    return None

WEBCAM_INDEX: Optional[int] = find_webcam_index()

# ── LLM 결과 수신 스키마 ────────────────────────────────────────────────────────
class LLMResult(BaseModel):
    face_key: str                          # Firebase face_results_raw 키
    llm_recommendation: str               # LLM 추천 결과 (예: "아메리카노")
    llm_response: str                      # LLM 전체 응답 텍스트
    age: Optional[int] = None
    gender: Optional[str] = None
    emotion: Optional[str] = None
    robot_status: Optional[str] = "대기"  # ROS2 로봇 처리 상태

class RobotStatusUpdate(BaseModel):
    order_key: str
    robot_status: str                      # "처리중" | "완료" | "오류"

# ── 유틸 함수 ───────────────────────────────────────────────────────────────────
def convert_numpy_types(obj):
    if isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj

def analyze_face_from_webcam():
    if WEBCAM_INDEX is None:
        return None, "웹캠을 찾을 수 없습니다."
    cap = cv2.VideoCapture(WEBCAM_INDEX)
    if not cap.isOpened():
        return None, f"웹캠 인덱스 {WEBCAM_INDEX} 열기 실패"
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None, "프레임 읽기 실패"
    return frame, None

# ── 라우터 ─────────────────────────────────────────────────────────────────────
@app.get("/")
def read_root():
    return {"message": "DeepFace API 서버 정상 실행 중"}

@app.get("/status")
def get_status():
    """서버 및 웹캠 상태 확인"""
    return {
        "status": "running",
        "webcam_index": WEBCAM_INDEX,
        "webcam_available": WEBCAM_INDEX is not None,
        "gpu_disabled": os.environ.get('CUDA_VISIBLE_DEVICES') == '-1',
    }

@app.post("/analyze/")
async def analyze_face():
    """웹캠 촬영 → DeepFace 분석 → Firebase 저장"""
    try:
        img, err = analyze_face_from_webcam()
        if img is None:
            return JSONResponse(status_code=400, content={"status": "error", "message": err})

        raw_results = DeepFace.analyze(
            img_path=img,
            actions=['emotion', 'age', 'gender'],
            enforce_detection=False
        )

        clean_results = convert_numpy_types(raw_results)
        clean_results[-1]['datetime'] = datetime.now().isoformat()

        # Firebase 저장 후 키 반환 (LLM 시스템이 face_key 로 활용)
        face_key = fb.write_face_result(clean_results)

        age_groups = clean_results[0].get("age")
        gender = clean_results[0].get("dominant_gender")
        emotion = {
            k: v for k, v in clean_results[0].get("emotion").items()
            if k in ['happy', 'sad', 'angry', 'surprise', 'neutral']
        }

        return {
            "status": "success",
            "face_key": face_key,          # LLM 시스템에서 /llm/result 호출 시 사용
            "component_results": {
                "age": f"{(age_groups // 10) * 10}대" if age_groups is not None else None,
                "gender": gender,
                "emotion": emotion,
                "dominant_emotion": clean_results[0].get("dominant_emotion"),
            },
        }

    except ValueError as ve:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(ve)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/llm/result")
async def receive_llm_result(data: LLMResult):
    """LLM+RAG 시스템에서 추천 결과를 받아 Firebase orders 에 저장"""
    try:
        order = {
            "datetime": datetime.now().isoformat(),
            "face_key": data.face_key,
            "llm_recommendation": data.llm_recommendation,
            "llm_response": data.llm_response,
            "age": data.age,
            "gender": data.gender,
            "emotion": data.emotion,
            "robot_status": data.robot_status,
        }
        order_key = fb.write_order(order)
        return {"status": "success", "order_key": order_key}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/face/latest")
async def get_latest_face():
    """Firebase에 저장된 가장 최근 얼굴 분석 결과를 반환합니다.

    LLM 시스템이 /analyze/ 를 직접 트리거하지 않고
    이미 저장된 최신 결과를 읽어 칵테일 추천에 활용할 때 사용합니다.

    Response:
        face_key  : Firebase push 키
        age       : 나이대 문자열 (예: "30대")
        gender    : 성별 (예: "Man")
        emotion   : 감정 분포 dict
        dominant_emotion : 주요 감정
        datetime  : 분석 시각 (ISO 8601)
    """
    try:
        latest = fb.get_latest_face_result()
        if latest is None:
            return JSONResponse(status_code=404, content={"status": "not_found", "message": "저장된 얼굴 분석 결과가 없습니다."})

        face_key = latest["face_key"]
        raw = latest["data"]          # list (DeepFace.analyze 결과)
        entry = raw[0] if isinstance(raw, list) else raw

        age_val = entry.get("age")
        emotion_raw = entry.get("emotion", {})
        emotion = {k: round(float(v), 2) for k, v in emotion_raw.items()
                   if k in ['happy', 'sad', 'angry', 'surprise', 'neutral', 'fear', 'disgust']}

        return {
            "status": "success",
            "face_key": face_key,
            "age": f"{(age_val // 10) * 10}대" if age_val is not None else None,
            "gender": entry.get("dominant_gender"),
            "emotion": emotion,
            "dominant_emotion": entry.get("dominant_emotion"),
            "datetime": entry.get("datetime"),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.patch("/robot/status")
async def update_robot_status(data: RobotStatusUpdate):
    """ROS2 로봇이 처리 상태를 업데이트할 때 호출"""
    try:
        fb.update_robot_status(data.order_key, data.robot_status)
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/orders")
async def get_orders():
    """저장된 주문 내역 전체 조회"""
    try:
        return {"status": "success", "orders": fb.read_orders()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
