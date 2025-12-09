# Law Matcher

자치법규 개정 검토 시스템 - 상위법령 개정 시 강남구 자치법규의 개정 필요성을 자동으로 검토합니다.

## 프로젝트 구조

```
law-matcher/
├── backend/          # FastAPI 백엔드
│   ├── api/          # API 엔드포인트
│   ├── models/       # SQLAlchemy 모델
│   ├── schemas/      # Pydantic 스키마
│   ├── services/     # 비즈니스 로직
│   ├── external/     # 외부 API 연동 (법제처)
│   └── utils/        # 유틸리티
├── frontend/         # React 프론트엔드
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
└── docs/             # 문서
```

## 기술 스택

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy 2.0 (async)
- PostgreSQL
- Redis
- Celery

### Frontend
- React 18
- TypeScript
- Ant Design
- React Query
- Vite

## 시작하기

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일에서 MOLEG_API_KEY 설정
```

### 2. Docker로 실행

```bash
docker-compose up -d
```

### 3. 개별 실행

#### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API 문서

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 주요 기능

1. **법령 동기화**: 법제처 API를 통해 상위법령 정보 동기화
2. **개정 감지**: 법령 개정 사항 자동 감지
3. **영향 분석**: 개정된 법령과 연관된 자치법규 분석
4. **검토 관리**: 개정 필요 여부 검토 및 리포트 생성

## 라이선스

MIT
