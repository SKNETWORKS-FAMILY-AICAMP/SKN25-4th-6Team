FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 프로젝트 루트 구조 복제 (/project = PROJECT_ROOT)
WORKDIR /project
COPY backend/ ./backend/
COPY src/     ./src/
COPY config/  ./config/
COPY prompts/ ./prompts/

# Django는 backend/ 안에서 실행
WORKDIR /project/backend

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
