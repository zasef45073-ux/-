# pick_and_place_voice_cup Workspace

이 문서는 현재 워크스페이스의 폴더 구조와 각 구성요소의 역할을 빠르게 파악하기 위한 안내입니다.

## Workspace Tree

```text
src/
├── od_msg/
│   ├── CMakeLists.txt
│   ├── package.xml
│   └── srv/
│       └── SrvDepthPosition.srv
└── pick_and_place_voice_cup/
    ├── CHANGELOG.md
    ├── DEV_LOG.md
    ├── package.xml
    ├── setup.cfg
    ├── setup.py
    ├── object_detection_cl/
    │   ├── __init__.py
    │   ├── detection_cl.py
    │   ├── realsense.py
    │   └── yolo.py
    ├── robot_control_cl/
    │   ├── __init__.py
    │   ├── onrobot.py
    │   └── robot_control_cl.py
    ├── voice_processing_cl/
    │   ├── __init__.py
    │   ├── get_keyword_cl.py
    │   ├── MicController.py
    │   ├── stt.py
    │   └── wakeup_word.py
    └── resource/
        ├── best.pt
        ├── class_name_tool.json
        ├── hello_rokey_8332_32.tflite
        ├── pick_and_place_voice
        ├── pick_and_place_voice_cup
        ├── T_gripper2camera.npy
        └── yolov8n_tools_0122.pt
```

## Package Overview

### 1) od_msg
ROS2 인터페이스(서비스 메시지) 전용 패키지입니다.

- `srv/SrvDepthPosition.srv`
  - 요청: `string target`
  - 응답: `float64[] depth_position`
  - 객체 이름(target)을 받아 카메라 기준 3D 좌표(depth position)를 반환할 때 사용합니다.
- `CMakeLists.txt`, `package.xml`
  - `rosidl` 인터페이스 생성 및 런타임 의존성 설정을 담당합니다.

### 2) pick_and_place_voice_cup
컵 탐지/그리핑/음성 처리 로직이 들어있는 메인 ROS2 Python 패키지입니다.

- `setup.py`
  - 설치 대상 Python 패키지 등록: `object_detection_cl`, `robot_control_cl`, `voice_processing_cl`
  - console script 엔트리 포인트 등록:
    - `robot_control_cl`
    - `object_detection_cl`
    - `get_keyword_cl`
- `package.xml`
  - `rclpy`, `sensor_msgs`, `cv_bridge`, `od_msg` 등 실행 의존성 선언.
- `CHANGELOG.md`, `DEV_LOG.md`
  - 기능 변경 내역 및 개발/디버깅 기록 문서.

## Module Details

### object_detection_cl
카메라 프레임 수집 + YOLO 추론 + 깊이 좌표 계산 노드입니다.

- `detection_cl.py`
  - `get_3d_position` 서비스 제공.
  - 단일 타겟 탐지와 cleanup 스냅샷(캐시) 기반 다중 타겟 좌표 조회를 처리.
  - 깊이 프레임에서 유효 깊이를 샘플링하고 픽셀 좌표를 카메라 3D 좌표로 변환.
- `realsense.py`
  - RealSense color/depth 토픽 subscribe 및 intrinsics 관리.
  - aligned depth 우선, 필요 시 raw depth fallback 처리.
- `yolo.py`
  - Ultralytics YOLO 모델 로딩 및 타겟별 최적 bbox 선택.
  - 다중 프레임 IoU 기반 집계와 unreasonable box 필터링 로직 포함.

### robot_control_cl
로봇 모션/그리퍼 제어 및 트리거 기반 작업 시퀀스를 담당합니다.

- `robot_control_cl.py`
  - `/cup_cleanup/trigger` 구독 후 이벤트 기반 동작 수행.
  - 관측 자세 이동 -> 목표 컵 탐지 요청 -> 접근/파지 -> 배치 동작 수행.
  - cleanup 모드(여러 컵 순차 처리), 취소 이벤트 처리, 상태 피드백 퍼블리시 포함.
- `onrobot.py`
  - OnRobot RG2/RG6 그리퍼 Modbus 제어 래퍼.
  - 열기/닫기/폭 이동/상태 조회 API 제공.

### voice_processing_cl
음성 트리거 및 STT 처리 모듈입니다.

- `get_keyword_cl.py`
  - 마이크/웨이크워드/STT를 엮은 ROS2 서비스 노드.
  - LLM 프롬프트 기반 키워드(객체/목적지) 추출 로직 포함.
- `MicController.py`
  - PyAudio 기반 스트림 오픈/녹음/저장 유틸리티.
- `wakeup_word.py`
  - openWakeWord 모델 기반 웨이크워드 감지.
- `stt.py`
  - OpenAI Whisper API 호출로 음성 -> 텍스트 변환.

## Resource Files

- `best.pt`, `yolov8n_tools_0122.pt`: YOLO 모델 가중치
- `class_name_tool.json`: 클래스 ID <-> 이름 매핑
- `hello_rokey_8332_32.tflite`: 웨이크워드 모델
- `T_gripper2camera.npy`: 그리퍼-카메라 변환 행렬
- `pick_and_place_voice`, `pick_and_place_voice_cup`: ROS 패키지 인덱스 리소스 파일

## Notes

- 현재 워크스페이스는 ROS2 기준으로 `od_msg`(인터페이스)와 `pick_and_place_voice_cup`(애플리케이션) 두 패키지로 분리되어 있습니다.
- 실제 실행은 `pick_and_place_voice_cup/setup.py`의 console scripts를 통해 노드를 시작하는 구조입니다.
