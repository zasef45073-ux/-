# ROS2 칵테일 주문 시스템 코드 분석 보고서

작성일: 2026-05-27
대상 워크스페이스: /home/rokey/d3_ws_1.6
분석 범위: 설정 파일 제외, 실행/로직 코드 및 인터페이스 정의

## 1. 분석 대상 파일

- src/cocktail_order_pkg/cocktail_order_pkg/integrated_order_node.py
- src/cocktail_order_pkg/cocktail_order_pkg/MicController.py
- src/cocktail_order_pkg/cocktail_order_pkg/stt.py
- src/cocktail_order_pkg/cocktail_order_pkg/tts.py
- src/cocktail_order_pkg/cocktail_order_pkg/wakeup_word.py
- src/cocktail_order_pkg/cocktail_order_pkg/build_db.py
- src/cocktail_order_pkg/cocktail_order_pkg/post_api.py
- src/cocktail_order_interfaces/action/CocktailOrder.action
- src/cocktail_order_interfaces/srv/TriggerCleanup.srv

참고: 아래 파일들은 분석 범위에서 제외함
- package.xml, setup.cfg, CMakeLists.txt, .vscode/*, resource/*, 빌드 산출물, 캐시/pyc

## 2. 시스템 구조 요약

### 2.1 전체 흐름

1. 웨이크워드 감지 또는 액션 요청으로 대화 세션 시작
2. 실시간 음성 수집(동적 임계치 기반)
3. Whisper STT로 사용자 발화 텍스트화
4. GPT + Vector DB 기반 메뉴 추천/확정 대화 진행
5. 성공 시 레시피 코드 토픽 발행으로 로봇 동작 트리거
6. 컵 정리 ASK_TRIGGER 수신 시 별도 음성 확인 플로우 수행

### 2.2 핵심 컴포넌트 역할

- IntegratedOrderManager: 전체 오케스트레이션 노드(상태 관리, 액션 서버, 토픽 I/O, 대화 세션)
- MicController: PyAudio 스트림 열기/닫기, 녹음 프레임 처리
- STT: Whisper API 호출
- TTS: OpenAI TTS 생성 후 로컬 재생
- WakeupWord: openWakeWord 모델 기반 키워드 감지
- build_db: ChromaDB 로컬 벡터 DB 초기화
- 인터페이스: CocktailOrder.action, TriggerCleanup.srv

## 3. 파일별 상세 분석

### 3.1 integrated_order_node.py

핵심 기능:
- ROS2 액션 서버 생성 및 실행
- 웨이크워드 상시 감시 스레드 운용
- 컵 정리 관련 트리거 토픽 처리
- 음성 대화 루프 및 GPT 상태 전이 처리
- 레시피 코드 발행

강점:
- 리소스 경로를 설치 환경/소스 환경 모두 대응
- 벡터 DB 실패 시 fallback 메뉴로 동작 지속
- 주문과 컵 정리 플로우를 하나의 노드에서 통합

주요 리스크:
- TriggerCleanup 서비스 타입은 import/콜백만 존재하고 create_service 연결 부재
- self.state를 여러 스레드에서 잠금 없이 읽고 쓰므로 경쟁 상태 가능
- 예외를 폭넓게 삼키는 구간이 많아 장애 원인 추적 어려움
- 고정 대기(sleep 7초)로 응답성 저하 가능
- 장치 인덱스와 비전 서버 주소 하드코딩

### 3.2 MicController.py

핵심 기능:
- 마이크 스트림 제어 및 WAV 데이터 생성

강점:
- 스트림 open/close 분리로 재사용 가능

리스크:
- 생성자 기본 인자에 MicConfig 인스턴스 직접 사용(가변 기본 인자 패턴 회피 필요)
- close 이후 stream을 None으로 명시하지 않아 상태 혼동 가능

### 3.3 stt.py

핵심 기능:
- 바이트 오디오를 메모리 내 WAV로 변환 후 Whisper 호출

강점:
- 임시 파일 없이 BytesIO로 처리
- language="ko" 명시로 한국어 환경 안정성 개선

리스크:
- 예외 처리 시 빈 문자열 반환만 하고 상세 복구 전략 없음

### 3.4 tts.py

핵심 기능:
- OpenAI TTS 생성 후 temp 파일 재생

강점:
- 간단하고 직관적인 재생 흐름

리스크:
- os.system 기반 실행은 운영 안정성/에러 제어 측면에서 취약
- mpg123 의존성 미설치 환경에서 실패 가능

### 3.5 wakeup_word.py

핵심 기능:
- 마이크 입력 리샘플링 후 wakeword 모델 추론

강점:
- 모델 경로 존재 확인 로그 제공

리스크:
- threshold 값이 코드 하드코딩, 환경별 튜닝 어려움
- 모델 파일 부재 시 런타임 실패 가능

### 3.6 build_db.py

핵심 기능:
- ChromaDB 재생성 및 칵테일 데이터 적재

강점:
- 기존 DB 삭제 후 재생성으로 멱등 처리
- 설치/소스 경로 fallback 처리

리스크:
- 데이터셋이 코드 내 하드코딩
- 실행 중 예외/검증 로직 최소화

### 3.7 post_api.py

핵심 기능:
- 비전 서버 API 단일 테스트 스크립트

리스크:
- 절대경로(/home/hyung/...) 하드코딩
- 패키지 내부 운영 코드와 혼재 시 혼동 가능

### 3.8 인터페이스 정의

CocktailOrder.action:
- Goal: start_chat
- Result: is_success, final_menu, recipe_code
- Feedback: current_turn, user_text, bot_message

TriggerCleanup.srv:
- Request: cup_id
- Response: success

관찰:
- srv는 정의되어 있으나 현재 노드 코드에서 서비스 서버 생성 연결이 확인되지 않음

## 4. 우선순위 이슈 정리

### High

1. 서비스 미연결: TriggerCleanup 서비스 create_service 누락
2. 동시성 위험: state 전이가 스레드 간 동기화 없이 수행
3. 하드코딩 의존성: device_index, 비전 서버 URL, 테스트 파일 경로

### Medium

1. 광범위 예외 처리로 장애 은닉
2. reset_to_idle의 고정 sleep으로 반응 지연
3. TTS 실행 방식(os.system) 안정성 낮음

### Low

1. 프롬프트 설명의 턴 제한과 실제 코드 상수(MAX_TURNS) 불일치
2. 테스트성 파일(post_api.py)의 배포 혼재 가능성

## 5. 개선 권고안

1. 서비스 연결 완성
- create_service(TriggerCleanup, ...) 추가 또는 미사용 코드 정리

2. 상태 동기화 도입
- threading.Lock 또는 상태 전이 함수화로 원자적 변경 보장

3. 환경 설정 외부화
- device_index, 비전 서버 URL, threshold를 ROS 파라미터 또는 .env로 분리

4. 예외 처리 고도화
- except Exception 최소화, 에러 유형별 로깅 및 복구 경로 분리

5. 응답성 개선
- reset_to_idle 고정 지연 제거 또는 조건부 축소

6. TTS 실행 안전화
- subprocess.run으로 교체하고 종료 코드/예외 처리 추가

7. 코드 정리
- legacy/unused 함수 정리, post_api.py 위치 재조정(테스트 디렉터리)

## 6. 결론

현재 코드는 기능 통합 측면에서 완성도가 높고 실제 데모 흐름(음성 대화-추천-확정-트리거 발행)이 잘 구성되어 있다.
다만 운영 안정성 관점에서는 서비스 연결 누락, 상태 경쟁, 하드코딩 의존성 3가지가 주요 위험 요소다.
해당 항목을 우선 개선하면 현장 적용성과 유지보수성이 크게 향상될 것으로 판단된다.
