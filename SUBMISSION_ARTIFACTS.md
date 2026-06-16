# D3 Submission Artifacts

이 문서는 제출용 파일을 빠르게 정리하기 위한 목록입니다.

## 1. ROS2 패키지 소스코드 (`src`)

### PC1

- `PC1/cobot_ws/src/cobot2_ws/object_detection`
  - RealSense + YOLO 기반 객체 탐지 및 3D 위치 추정 패키지
- `PC1/cobot_ws/src/cobot2_ws/od_msg`
  - 객체 위치 반환용 ROS2 서비스 인터페이스 패키지
- `PC1/cobot_ws/src/cobot2_ws/robot_control`
  - Doosan 로봇 및 그리퍼 제어 패키지
- `PC1/cobot_ws/src/cobot2_ws/voice_processing`
  - 웨이크워드, STT, LLM 기반 음성 처리 패키지
- `PC1/cobot_ws/src/cobot2_ws/rokey`
  - 로봇 제어 보조 및 실습성 패키지
- `PC1/pick_and_place_voice_cup/src/od_msg`
  - 별도 통합 워크스페이스용 서비스 인터페이스 패키지
- `PC1/pick_and_place_voice_cup/src/pick_and_place_voice_cup`
  - 음성 + 객체 탐지 + pick-and-place 통합 패키지

### PC2

- `PC2/d3_ws_1.6/src/cocktail_order_interfaces`
  - 주문 액션 및 컵 정리 확인 서비스 인터페이스 패키지
- `PC2/d3_ws_1.6/src/cocktail_order_pkg`
  - 음성 주문, STT/TTS, GPT, 벡터 DB 연동 패키지

## 2. 소스코드 압축본 (`.zip`)

- 제출용 압축본: `D3_source_code.zip`
- 포함 대상:
  - `PC1/cobot_ws/src/cobot2_ws`
  - `PC1/pick_and_place_voice_cup/src`
  - `PC2/d3_ws_1.6/src`
  - `PC1/cup_cleanup`
- 제외 대상:
  - `.env`
  - `serviceAccountKey.json`
  - `.pt`, `.pth`, `.joblib`, `.pkl`
  - `build/`, `install/`, `log/`, `.vscode/`, `__pycache__/`, `.venv/`, `venv/`

## 3. AI 모델 파일 (`.pt`)

- `PC1/cobot_ws/src/cobot2_ws/object_detection/resource/best.pt`
- `PC1/cobot_ws/src/cobot2_ws/object_detection/resource/best_f.pt`
- `PC1/cobot_ws/src/cobot2_ws/object_detection/resource/best_o.pt`
- `PC1/pick_and_place_voice_cup/src/pick_and_place_voice_cup/resource/best.pt`
- `PC1/pick_and_place_voice_cup/src/pick_and_place_voice_cup/resource/yolov8n_tools_0122.pt`

## 4. API / 규칙 / 설정 파일

프로젝트 안에 `game_rule`이라는 이름의 단일 파일은 없지만, 아래 파일들이 그 역할에 가장 가깝습니다.

### 규칙성 로직 / 정책 규칙

- `PC1/cup_cleanup/configs/config.yaml`
  - 컵 정리 판단 임계값, 정책 파라미터, ROS2 트리거 매핑
- `PC2/d3_ws_1.6/src/cocktail_order_pkg/cocktail_order_pkg/build_db.py`
  - 칵테일 추천용 규칙성 데이터와 레시피 코드 정의
- `PC1/cobot_ws/src/cobot2_ws/voice_processing/voice_processing/get_keyword.py`
  - JSON 상태와 사용자 발화를 바탕으로 컵/목적지 추출 규칙 정의

### JSON 설정 파일

- `PC1/cobot_ws/src/cobot2_ws/object_detection/resource/class_name_tool.json`
  - YOLO 클래스 이름 매핑
- `PC1/cobot_ws/src/cobot2_ws/voice_processing/voice_processing/mock_scenarios.json`
  - 음성 처리 테스트용 상태 시나리오 JSON
- `PC2/deepface_project/firebase-adminsdk.example.json`
  - Firebase 설정 예시 파일

### 외부 API 및 연동 스크립트

- `PC2/deepface_project/backend/main.py`
  - FastAPI 서버, 얼굴 분석 API, 주문 결과 수신 API, 로봇 상태 업데이트 API
- `PC2/deepface_project/backend/firebase/config.py`
  - Firebase 경로 및 환경변수 설정
- `PC2/deepface_project/backend/firebase/database.py`
  - Firebase CRUD 함수
- `PC2/d3_ws_1.6/src/cocktail_order_pkg/cocktail_order_pkg/integrated_order_node.py`
  - OpenAI, ChromaDB, 원격 비전 API, ROS2 주문/정리 연동
- `PC2/d3_ws_1.6/src/cocktail_order_pkg/cocktail_order_pkg/firebase_store.py`
  - Firebase 저장/업데이트 연동
- `PC2/d3_ws_1.6/src/cocktail_order_pkg/cocktail_order_pkg/post_api.py`
  - 외부 얼굴 분석 API 호출 예제 스크립트

## 5. README 문서

- `README.md`
  - 전체 워크스페이스 개요
- `ARCHITECTURE.md`
  - 전체 시스템 아키텍처 문서
- `PC1/cup_cleanup/README.md`
  - 컵 정리 프로젝트 설명
- `PC1/pick_and_place_voice_cup/src/README.md`
  - 음성 기반 pick-and-place 워크스페이스 설명
- `PC1/cobot_ws/src/doosan-robot2/README.md`
  - Doosan ROS2 패키지 설명
- `PC2/deepface_project/README.md`
  - 얼굴 분석/관제 시스템 설명
- `PC2/d3_ws_1.6/READMD.md`
  - 음성 주문 ROS2 시스템 설명

## 6. 제출 시 주의사항

- `.zip`에는 API 키, Firebase 인증 키 같은 민감정보를 포함하지 않는 것을 권장합니다.
- `voice_processing/resource/.env`, `pick_and_place_voice_cup/resource/.env`, `serviceAccountKey.json` 계열은 제출본에서 제외하는 것이 안전합니다.
- 모델 파일은 소스 압축본과 분리해서 제출하는 편이 관리하기 쉽습니다.