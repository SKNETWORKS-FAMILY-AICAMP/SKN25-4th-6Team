#!/usr/bin/env bash
# RAIchU 웹 서버 실행 스크립트
# 사용법: ./run_web.sh

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
NPM_CMD="/opt/homebrew/bin/npm"

if [[ ! -x "$NPM_CMD" ]]; then
  NPM_CMD="$(which npm 2>/dev/null || echo "")"
fi
if [[ -z "$NPM_CMD" ]]; then
  echo "[오류] npm을 찾을 수 없습니다."
  exit 1
fi

# 포트 번호로 프로세스 강제 종료
kill_port() {
  local port=$1
  local pids
  pids=$(lsof -ti :"$port" 2>/dev/null)
  if [[ -n "$pids" ]]; then
    echo "[INFO] 포트 $port 점유 프로세스 종료..."
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
}

echo "[INFO] 기존 프로세스 정리..."
kill_port 8000
kill_port 5173
pkill -9 -f "manage.py runserver" 2>/dev/null || true
pkill -9 -f "vite" 2>/dev/null || true
sleep 1

# .env 로드
if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a; source "$ROOT_DIR/.env"; set +a
fi

# Django 패키지 확인
"$VENV_PYTHON" -c "import django" 2>/dev/null || {
  echo "[INFO] Django 설치 중..."
  "$VENV_PYTHON" -m pip install django djangorestframework django-cors-headers --quiet
}

# DB 마이그레이션
cd "$ROOT_DIR/backend"
"$VENV_PYTHON" manage.py migrate --run-syncdb 2>/dev/null || true

# 백엔드 시작 (--noreload: 자식 프로세스 없이 단일 프로세스)
echo "[INFO] 백엔드 시작..."
"$VENV_PYTHON" manage.py runserver 8000 --noreload 2>/dev/null &
BACKEND_PID=$!

# 백엔드 준비 대기
for i in $(seq 1 10); do
  sleep 1
  if curl -sf http://localhost:8000/api/health/ >/dev/null 2>&1; then
    echo "[OK]  백엔드 → http://localhost:8000"
    break
  fi
  if [[ $i -eq 10 ]]; then
    echo "[오류] 백엔드 시작 실패"
    exit 1
  fi
done

# npm 패키지 설치
cd "$ROOT_DIR/frontend"
if [[ ! -d node_modules ]]; then
  echo "[INFO] npm 패키지 설치 중..."
  "$NPM_CMD" install
fi

# 종료 핸들러
cleanup() {
  echo ""
  echo "[INFO] 종료 중..."
  kill $BACKEND_PID 2>/dev/null || true
  kill_port 8000
  kill_port 5173
  exit 0
}
trap cleanup INT TERM

echo ""
echo "======================================"
echo "  접속 주소: http://localhost:5173"
echo "  종료: Ctrl+C"
echo "======================================"
echo ""

"$NPM_CMD" run dev
