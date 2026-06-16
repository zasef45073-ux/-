FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 빌드 컨텍스트: 프로젝트 루트
COPY frontend/dashboard.py .
COPY frontend/pages/ ./pages/
COPY frontend/utils/ ./utils/
# Firebase 인증 파일 (backend/firebase/ 에서 복사)
COPY backend/firebase/serviceAccountKey.json .

EXPOSE 8501
CMD ["streamlit", "run", "dashboard.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
