# AI 칵테일바 시스템 아키텍처

> DeepFace × LLM+RAG × 서빙 로봇 통합 관제 시스템

---

## 목차

1. [시스템 개요](#시스템-개요)
2. [전체 아키텍처 다이어그램](#전체-아키텍처-다이어그램)
3. [컴포넌트 상세](#컴포넌트-상세)
   - [Backend (FastAPI)](#backend-fastapi)
   - [Frontend (Streamlit)](#frontend-streamlit)
   - [Qdrant 벡터 DB](#qdrant-벡터-db)
   - [Firebase Realtime DB](#firebase-realtime-db)
   - [외부 연동 시스템](#외부-연동-시스템)
4. [데이터 흐름](#데이터-흐름)
5. [API 명세](#api-명세)
6. [인프라 구성](#인프라-구성)
7. [기술 선택 이유](#기술-선택-이유)
8. [프로젝트 디렉토리 구조](#프로젝트-디렉토리-구조)

---

## 시스템 개요

AI 칵테일바는 얼굴 인식(DeepFace)으로 고객의 나이·성별·감정을 분석하고, LLM+RAG 시스템이 칵테일을 추천하며, ROS2 서빙 로봇이 음료를 전달하는 자동화 서비스입니다. 관리자는 Streamlit 대시보드에서 전체 운영 현황을 실시간으로 모니터링합니다.

---

## 전체 아키텍처 다이어그램

```
┌──────────────────────────────────────────────────────────────────┐
│                    Docker Network: deepface-net                   │
│                                                                  │
│  ┌─────────────────────────┐   ┌────────────────────────────┐   │
│  │  Backend  :8000          │   │  Frontend  :8501           │   │
│  │  (cocktailbar-backend)   │   │  (cocktailbar-frontend)    │   │
│  │                          │   │                            │   │
│  │  FastAPI                 │   │  Streamlit 대시보드         │   │
│  │  ├─ OpenCV 웹캠 캡처      │   │  ├─ 홈 (운영 현황 요약)     │   │
│  │  ├─ DeepFace 얼굴 분석    │   │  ├─ 고객 분석              │   │
│  │  ├─ Firebase 저장/조회    │   │  ├─ 칵테일 주문 내역        │   │
│  │  └─ 로봇 상태 업데이트    │   │  ├─ 통계                   │   │
│  │                          │   │  └─ 로봇 대시보드           │   │
│  └──────────┬───────────────┘   └──────────┬─────────────────┘   │
│             │                              │                     │
│  ┌──────────┴───────────────────────────────────────────────┐    │
│  │  Qdrant  :6333                                            │    │
│  │  (cocktailbar-qdrant)  ─ 칵테일 임베딩 벡터 DB             │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
  ┌─────────────┐    ┌───────────────┐    ┌──────────────┐
  │  Firebase   │    │  LLM+RAG      │    │  ROS2 서빙   │
  │  Realtime   │    │  시스템 (외부) │    │  로봇 (외부) │
  │  DB (외부)   │    │               │    │              │
  └─────────────┘    └───────────────┘    └──────────────┘
```

---

## 컴포넌트 상세

### Backend (FastAPI)

| 항목 | 내용 |
|------|------|
| 컨테이너명 | `cocktailbar-backend` |
| 포트 | `8000` |
| 베이스 이미지 | `tensorflow/tensorflow:2.21.0-gpu` (CUDA 12.x + cuDNN 9.3) |
| GPU | NVIDIA GPU 1개 예약 (`nvidia` driver) |
| 웹캠 | `/dev/video0` 마운트, `video` 그룹 권한 |

**주요 라이브러리**

| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| fastapi | 0.136.1 | REST API 서버 |
| uvicorn | 0.47.0 | ASGI 서버 |
| deepface | 0.0.100 | 얼굴 분석 (나이·성별·감정) |
| opencv-python | 4.13.0.92 | 웹캠 프레임 캡처 |
| tensorflow | 2.21.0 (이미지 내장) | DeepFace 추론 백엔드 |
| firebase-admin | 7.4.0 | Firebase Realtime DB 연동 |
| numpy | 2.2.6 | 배열 처리 |

**내부 모듈 구조**

```
backend/
├── main.py              # FastAPI 앱, 라우터 정의
└── firebase/
    ├── client.py        # Firebase 앱 초기화 (싱글턴)
    ├── config.py        # 경로 상수, 환경변수 설정
    └── database.py      # DB CRUD 함수
```

---

### Frontend (Streamlit)

| 항목 | 내용 |
|------|------|
| 컨테이너명 | `cocktailbar-frontend` |
| 포트 | `8501` |
| 시작 조건 | Backend `healthcheck` 통과 후 실행 |

**페이지 구성**

| 파일 | 페이지 | 주요 기능 |
|------|--------|-----------|
| `dashboard.py` | 홈 | 오늘 감지 건수, 주문 수, 완료율, 주요 감정, 미성년자 차단 건수 요약 |
| `pages/1_Customer_Analysis.py` | 고객 분석 | DeepFace 분석 결과 테이블, 미성년자 감지 현황, CSV 다운로드 |
| `pages/2_Cocktail_Orders.py` | 칵테일 주문 | LLM 추천 주문 목록, 고객 정보, 로봇 서빙 상태, datetime 결측값(NaT/None) 안전 표시 |
| `pages/3_Statistics.py` | 통계 | 시간대별/감정별/성별 분포 차트 |
| `pages/4_Robot_Dashboard.py` | 로봇 대시보드 | ROS2 서빙 로봇 상태 실시간 모니터링 |

로봇 상태값은 Frontend 데이터 로더에서 표준화해 표시합니다. 예: `recipe_triggered`, `waiting` → `대기`, `completed` → `완료`, `error` → `오류`.

**주요 유틸**

```
frontend/utils/
├── data_loader.py   # Firebase 데이터 로드 → pandas DataFrame 변환
├── firebase_init.py # Firebase Admin SDK 초기화
└── styles.py        # 전역 CSS, 사이드바, 자동 새로고침 루프
```

주문 상세 선택(selectbox) 라벨 생성 시 `datetime`이 `NaT` 또는 `None`인 경우에도 예외 없이 동작하도록 안전 포맷 처리(`strftime` 예외 처리)를 적용했습니다.

---

### Qdrant 벡터 DB

| 항목 | 내용 |
|------|------|
| 컨테이너명 | `cocktailbar-qdrant` |
| REST 포트 | `6333` |
| gRPC 포트 | `6334` |
| 이미지 | `qdrant/qdrant:latest` |
| 스토리지 | `./qdrant_data` 볼륨 마운트 |
| 용도 | 칵테일 설명 임베딩 저장, LLM RAG 검색 |

LLM+RAG 시스템이 고객의 감정/나이/성별 정보를 기반으로 칵테일 컬렉션에서 유사도 검색을 수행합니다.

---

### Firebase Realtime DB

| 경로 | 내용 |
|------|------|
| `face_results_raw/` | DeepFace 분석 결과 (나이·성별·감정·신뢰도·타임스탬프) |
| `orders/` | 칵테일 주문 (LLM 추천·LLM 응답·고객 정보·로봇 상태) |

- DB URL: `https://rokey-d3-default-rtdb.asia-southeast1.firebasedatabase.app/`
- 인증 키 기본 경로
  - Backend: `./firebase/serviceAccountKey.json`
  - Frontend: `./serviceAccountKey.json` (빌드 시 `backend/firebase/serviceAccountKey.json`을 복사)
- Firebase push 키의 시간순 정렬 특성을 활용해 `limitToLast(1)`로 최신 결과를 O(1)로 조회

---

### 외부 연동 시스템

#### LLM+RAG 시스템

프로젝트 외부에서 동작하며 Backend API를 통해 연동됩니다.

1. `GET /face/latest` → 최신 얼굴 분석 결과 조회
2. Qdrant 검색 → 고객 감정/나이/성별에 맞는 칵테일 추천
3. `POST /llm/result` → 추천 결과를 Backend로 전달

#### ROS2 서빙 로봇

- `PATCH /robot/status` → 주문 처리 상태 업데이트 (`대기` → `처리중` → `완료` / `오류`)

---

## 데이터 흐름

```
[웹캠]
  │
  ▼
[Backend: POST /analyze/]
  │  OpenCV 프레임 캡처
  │  DeepFace.analyze(emotion, age, gender)
  │
  ├──→ [Firebase: face_results_raw/] 저장 → face_key 반환
  │
  ▼
[LLM+RAG 시스템]
  │  GET /face/latest → 나이·성별·감정 수신
  │  Qdrant 벡터 검색 → 칵테일 후보 추출
  │  LLM 추론 → 최종 추천 칵테일 결정
  │
  ├──→ [Backend: POST /llm/result] → [Firebase: orders/] 저장
  │
  ▼
[ROS2 서빙 로봇]
  │  주문 수신 후 음료 서빙
  │
  └──→ [Backend: PATCH /robot/status] → [Firebase: orders/{key}/robot_status] 업데이트
  
[Streamlit 대시보드]
  └── Firebase 직접 읽기 → 실시간 현황 표시 (자동 새로고침)
```

---

## API 명세

### GET `/`
API 루트 메시지 확인

**Response**
```json
{
  "message": "DeepFace API 서버 정상 실행 중"
}
```

---

### GET `/status`
서버 및 웹캠 상태 확인

**Response**
```json
{
  "status": "running",
  "webcam_index": 0,
  "webcam_available": true,
  "gpu_disabled": false
}
```

---

### POST `/analyze/`
웹캠 촬영 → DeepFace 분석 → Firebase 저장

**Response**
```json
{
  "status": "success",
  "face_key": "-OAbc123...",
  "component_results": {
    "age": "30대",
    "gender": "Man",
    "emotion": { "happy": 72.3, "neutral": 18.1, "sad": 5.2, "angry": 2.1, "surprise": 2.3 },
    "dominant_emotion": "happy"
  }
}
```

---

### GET `/face/latest`
Firebase에서 가장 최근 얼굴 분석 결과 반환 (LLM 시스템용)

**Response**
```json
{
  "status": "success",
  "face_key": "-OAbc123...",
  "age": "30대",
  "gender": "Man",
  "emotion": { "happy": 72.3, "neutral": 18.1 },
  "dominant_emotion": "happy",
  "datetime": "2026-05-27T10:30:00.123456"
}
```

---

### POST `/llm/result`
LLM+RAG 시스템에서 추천 결과 수신 → Firebase orders 저장

**Request Body**
```json
{
  "face_key": "-OAbc123...",
  "llm_recommendation": "모히토",
  "llm_response": "활기찬 감정과 30대 남성에게 상쾌한 모히토를 추천드립니다.",
  "age": 32,
  "gender": "Man",
  "emotion": "happy",
  "robot_status": "대기"
}
```

**Response**
```json
{
  "status": "success",
  "order_key": "-OXyz456..."
}
```

---

### PATCH `/robot/status`
ROS2 로봇 서빙 상태 업데이트

**Request Body**
```json
{
  "order_key": "-OXyz456...",
  "robot_status": "완료"
}
```

**로봇 상태값**: `대기` → `처리중` → `완료` / `오류`

---

### GET `/orders`
저장된 주문 내역 전체 조회

**Response**
```json
{
  "status": "success",
  "orders": {
    "-OXyz456...": {
      "face_key": "-OAbc123...",
      "llm_recommendation": "모히토",
      "robot_status": "대기"
    }
  }
}
```

---

## 인프라 구성

### Docker Compose 서비스 의존 관계

```
qdrant
  └─── deepface-api (depends_on: qdrant)
          └─── dashboard (depends_on: deepface-api [healthy])
```

### 헬스체크

```yaml
# deepface-api healthcheck
test: ["CMD", "curl", "-f", "http://localhost:8000/status"]
interval: 30s
timeout: 10s
retries: 3
start_period: 90s   # TF 모델 로딩 시간 확보
```

### 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `QDRANT_HOST` | `qdrant` | Qdrant 서비스 호스트 |
| `QDRANT_PORT` | `6333` | Qdrant REST 포트 |
| `FIREBASE_KEY_PATH` | `./firebase/serviceAccountKey.json` | Firebase 인증 키 경로 |
| `FIREBASE_DATABASE_URL` | `https://rokey-d3-default-rtdb.asia-southeast1.firebasedatabase.app/` | Firebase DB URL |
| `TF_CPP_MIN_LOG_LEVEL` | `2` | TensorFlow 로그 수준 |

환경변수 주의사항:

- 현재 `docker-compose.yml`은 `env_file`을 사용하지 않으므로 `.env` 값이 컨테이너 런타임 환경변수로 자동 주입되지 않습니다.
- 런타임 반영이 필요하면 `docker-compose.yml`의 `environment` 또는 `env_file`에 명시해야 합니다.

---

## 기술 선택 이유

### Streamlit을 사용한 이유

- 이 프로젝트의 프론트는 일반 사용자용 제품 화면이 아니라 운영자용 관제 대시보드입니다.
- 홈, 고객 분석, 주문 내역, 통계, 로봇 상태처럼 표와 지표 중심 화면이 많아 Streamlit의 선언형 UI가 잘 맞습니다.
- pandas DataFrame과 Firebase 조회 결과를 바로 화면에 연결할 수 있어 구현 속도가 빠릅니다.
- 별도의 프런트 빌드 파이프라인 없이 Python 코드만으로 UI 수정과 배포가 가능합니다.
- `auto_refresh_loop` 같은 주기적 갱신 구조를 넣어 실시간 모니터링 화면을 단순하게 유지할 수 있습니다.

### FastAPI를 사용한 이유

- 얼굴 분석, LLM 결과 수신, 로봇 상태 갱신처럼 API 중심 기능을 명확하게 분리할 수 있습니다.
- `/`, `/status`, `/analyze/`, `/face/latest`, `/llm/result`, `/robot/status`, `/orders`처럼 역할이 분리된 엔드포인트 구성이 가능합니다.
- 자동 API 문서화(Swagger UI)가 제공되어 연동 테스트와 디버깅이 쉽습니다.
- Pydantic 스키마로 요청/응답 구조를 강하게 정의할 수 있어 외부 시스템과의 계약을 유지하기 좋습니다.

### DeepFace와 OpenCV를 사용한 이유

- 이 시스템의 입력은 웹캠 프레임이고, 핵심 처리는 얼굴 속성 분석입니다.
- OpenCV는 `/dev/video0` 기반 웹캠 캡처를 간단하게 처리할 수 있어 운영 환경과 맞습니다.
- DeepFace는 나이, 성별, 감정 분석을 한 흐름으로 제공해서 요구 기능과 직접적으로 맞습니다.
- 추론을 백엔드 내부에서 수행하므로 외부 영상 분석 서비스에 의존하지 않아도 됩니다.

### Qdrant를 사용한 이유

- 칵테일 추천은 정적인 분류보다 고객 상태에 맞는 후보 검색이 중요합니다.
- Qdrant는 임베딩 기반 유사도 검색에 적합해서 LLM+RAG 구조와 잘 맞습니다.
- 벡터 저장소와 추천 로직을 분리하면 칵테일 레시피/설명 데이터가 늘어나도 확장하기 쉽습니다.
- REST와 gRPC를 모두 제공해 외부 추천 시스템과 연동하기 좋습니다.

### Firebase Realtime DB를 사용한 이유

- 얼굴 분석 결과와 주문 상태는 Backend, Frontend, 외부 LLM, 로봇이 함께 읽고 쓰는 공용 데이터입니다.
- Realtime DB는 단순한 경로 기반 구조로 저장/조회가 쉬워 현재 구조와 잘 맞습니다.
- push key와 최신 항목 조회 패턴이 `limitToLast(1)` 같은 구현과 자연스럽게 연결됩니다.
- 대시보드에서 실시간 상태를 보여주는 관제용 데이터 저장소로 적합합니다.

### Docker Compose를 사용한 이유

- Backend, Frontend, Qdrant를 하나의 네트워크와 실행 단위로 묶을 수 있습니다.
- 서비스 간 의존 관계를 명시해서 대시보드가 백엔드 준비 전에 뜨는 문제를 줄일 수 있습니다.
- GPU, 웹캠, 볼륨 마운트, 포트 노출 같은 운영 요소를 코드로 관리할 수 있습니다.
- 재현 가능한 실행 환경을 만들어 개발/운영 간 차이를 줄입니다.

### ROS2 연동을 분리한 이유

- 로봇 제어는 HTTP API와 별개인 실시간 시스템이므로 책임 분리가 중요합니다.
- Backend는 주문과 상태 저장만 담당하고, 실제 서빙 동작은 ROS2가 담당하는 구조가 유지보수에 유리합니다.
- 로봇 구현이 바뀌어도 API 계약만 유지되면 Backend 영향이 작습니다.


## 프로젝트 디렉토리 구조

```
deepface_project/
├── docker-compose.yml          # 전체 서비스 오케스트레이션
├── README.md                   # 통합 실행/운영 가이드
├── ARCHITECTURE.md             # 이 문서
│
├── backend/
│   ├── Dockerfile              # tensorflow:2.21.0-gpu 기반 이미지
│   ├── main.py                 # FastAPI 앱 + 라우터
│   ├── requirements.txt
│   └── firebase/
│       ├── __init__.py
│       ├── client.py           # Firebase 앱 싱글턴 초기화
│       ├── config.py           # 경로·URL 상수
│       ├── database.py         # CRUD 함수
│       └── serviceAccountKey.json
│
├── frontend/
│   ├── Dockerfile
│   ├── dashboard.py            # 메인 홈 페이지
│   ├── requirements.txt
│   ├── pages/
│   │   ├── 1_Customer_Analysis.py   # 고객 얼굴 분석
│   │   ├── 2_Cocktail_Orders.py     # 칵테일 주문 내역
│   │   ├── 3_Statistics.py          # 통계 차트
│   │   └── 4_Robot_Dashboard.py     # 로봇 현황
│   └── utils/
│       ├── __init__.py
│       ├── data_loader.py      # Firebase → DataFrame
│       ├── firebase_init.py    # Firebase 초기화
│       └── styles.py           # CSS · 사이드바 · 자동새로고침
│
└── qdrant_data/                # Qdrant 벡터 데이터 (볼륨)
    ├── raft_state.json
    ├── aliases/
    └── collections/
```
