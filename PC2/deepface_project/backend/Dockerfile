# TensorFlow 2.21 공식 GPU 이미지 (CUDA 12.x + cuDNN 9.3 포함)
FROM tensorflow/tensorflow:2.21.0-gpu

# GPU 활성화
ENV TF_CPP_MIN_LOG_LEVEL=2 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# OpenCV + 웹캠 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    libv4l-dev \
    v4l-utils \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 설치 (레이어 캐싱)
# --ignore-installed blinker: TF 이미지 내 distutils 설치 충돌 우회
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --ignore-installed blinker -r requirements.txt

# 소스 코드 복사 (빌드 컨텍스트: 프로젝트 루트)
# firebase/ 폴더 안에 인증 파일 포함
COPY backend/ ./

# DeepFace 모델 사전 다운로드 (첫 요청 지연 방지, deepface 0.0.100 API)
RUN python -c "\
from deepface.modules.modeling import build_model; \
build_model(task='facial_attribute', model_name='Emotion'); \
build_model(task='facial_attribute', model_name='Age'); \
build_model(task='facial_attribute', model_name='Gender')" || true

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
