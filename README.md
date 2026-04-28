# RAIchU — Real AI Card Hub System for You

신용카드 추천 AI 챗봇 서비스입니다. 사용자의 소비 패턴과 라이프스타일을 바탕으로 최적의 신용카드를 추천합니다.

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS v4, Zustand, TanStack Query |
| Backend | Django, Django REST Framework |
| AI / RAG | OpenAI GPT-4.1-mini, text-embedding-3-small, Hybrid Search (Vector + Keyword) |
| 데이터 | 10개 카드사 105종 카드 JSON 데이터 |
| 인프라 | Docker, Docker Compose |

---

## 프로젝트 구조

```
SKN25-4th-6Team/
├── backend/
│   ├── api/            # Django REST API (views, urls)
│   ├── config/         # Django 설정 (settings, wsgi)
│   ├── src/            # RAG 핵심 로직
│   │   ├── service.py  # 서비스 레이어 진입점
│   │   ├── retrieval.py# 하이브리드 검색 (벡터 + 키워드, RRF)
│   │   ├── llm.py      # OpenAI API 호출 및 fallback
│   │   ├── cards.py    # 카드 데이터 로딩 및 분류
│   │   ├── context.py  # LLM 컨텍스트 빌더
│   │   └── utils.py    # 토크나이저, 동의어 확장
│   ├── rag_config/     # RAG 파라미터, 카테고리 규칙, 동의어 JSON
│   ├── prompts/        # 프롬프트 템플릿 (.j2)
│   ├── scripts/        # 벡터 인덱스 빌드 스크립트
│   ├── data/
│   │   ├── cards/      # 카드 데이터 JSON (105종)
│   │   └── db.sqlite3  # Django 기본 DB
│   ├── vector_store/   # 벡터 임베딩 인덱스 (NPZ)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/      # SplashScreen, OnboardingPage, ChatPage, MyPage
│   │   ├── store/      # Zustand 전역 상태 (userStore)
│   │   └── api/        # axios 클라이언트
│   └── Dockerfile
└── docker-compose.yml
```

---

## 주요 기능

- **온보딩**: 연령대, 소비 패턴, 라이프스타일 입력으로 개인화된 추천 준비
- **AI 카드 추천**: 질문 기반 하이브리드 검색 + GPT 답변
- **하이브리드 검색**: 벡터 유사도(60%) + 키워드 매칭(40%), Reciprocal Rank Fusion으로 결합
- **자동 필터 추론**: 질문에서 카드사·카테고리·연회비 조건 자동 추출
- **마이페이지**: 프로필 및 보유 카드 관리

---

## 카드 데이터

BC카드, IBK카드, 국민카드, 농협카드, 롯데카드, 삼성카드, 신한카드, 우리카드, 하나카드, 현대카드 — **총 105종**

---

## 로컬 실행

### 사전 준비

```bash
# 1. 가상환경 생성 및 패키지 설치
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

# 2. 환경 변수 설정
cp backend/.env.example backend/.env
# backend/.env에 OPENAI_API_KEY 입력

# 3. DB 마이그레이션
cd backend && ../.venv/bin/python manage.py migrate
```

### 서버 실행

```bash
# 터미널 1 — 백엔드
cd backend
../.venv/bin/python manage.py runserver

# 터미널 2 — 프론트엔드
cd frontend
npm install   # 최초 1회
npm run dev
```

접속: **http://localhost:3000**

---

## Docker 실행

```bash
# backend/.env에 OPENAI_API_KEY 입력 후
docker compose up --build
```

접속: **http://localhost:3000**

---

## 환경 변수

### backend/.env

| 변수 | 설명 | 기본값 |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API 키 | 필수 |
| `SECRET_KEY` | Django 시크릿 키 | 변경 필요 |
| `DEBUG` | 디버그 모드 | `True` |
| `ALLOWED_HOSTS` | 허용 호스트 | `localhost,127.0.0.1` |

### frontend/.env

| 변수 | 설명 | 기본값 |
|---|---|---|
| `VITE_API_BASE_URL` | 백엔드 API 주소 | `http://localhost:8000` |

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/health/` | 서버 상태 확인 |
| POST | `/api/chat/` | 카드 추천 챗봇 |

### POST /api/chat/ 요청 예시

```json
{
  "message": "마트 할인 카드 추천해줘",
  "history": []
}
```

### 응답 예시

```json
{
  "answer": "롯데마트&MAXX 카드는 ...",
  "inferred_filters": {
    "banks": [],
    "categories": ["마트"],
    "fee_bands": []
  }
}
```
