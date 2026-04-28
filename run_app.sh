#!/usr/bin/env bash
# Streamlit 앱 실행 스크립트 (자동 포트 선택)

set -uo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

# 기존 Streamlit 프로세스 종료
pkill -f "streamlit run app.py" 2>/dev/null || true
sleep 1

# Python으로 사용 가능한 포트 찾기
PORT=$(python3 -c "
import socket
for port in range(8501, 8600):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', port))
        sock.close()
        print(port)
        break
    except OSError:
        continue
else:
    print(8501)
")

echo "[INFO] Streamlit 앱 시작: 포트 $PORT"
echo "[접속] http://localhost:$PORT"
streamlit run app.py --server.port "$PORT" --server.headless false
