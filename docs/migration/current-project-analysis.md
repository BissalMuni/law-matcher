# 현재 프로젝트 (law-matcher) 분석 결과

## 조사일: 2026-03-23

## 1. 기술 스택

| 항목 | 내용 |
|------|------|
| Backend | Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) |
| Frontend | React 18 + TypeScript 5.3 + Ant Design 5 + Vite |
| DB | PostgreSQL 15 |
| Task Queue | Celery 5.3 + Redis |
| API 연동 | 법제처 OpenAPI (law.go.kr) |
| AI | Claude/GPT/Gemini LLM 연동 |
| 컨테이너 | Docker Compose (6 서비스) |

## 2. 프로젝트 규모

| 항목 | 수량 |
|------|------|
| DB 모델 | 16개 |
| API 엔드포인트 | ~50개 |
| 서비스 모듈 | 14개 (총 ~213KB) |
| 프론트 페이지 | 27개 |
| 프론트 컴포넌트 | 8개 |
| Alembic 마이그레이션 | 18개 |

## 3. DB 모델 목록 (16개)

| Model | 파일 | 용도 |
|-------|------|------|
| User | user.py | 사용자 계정 |
| Department | department.py | 부서/조직 |
| Ordinance | ordinance.py | 자치법규 (조례/규칙) |
| Law | law.py | 상위법령 |
| OrdinanceLawMapping | ordinance_law_mapping.py | 조례-법령 N:M 연계 |
| OrdinanceReview | ordinance_review.py | 조례 검토이력 |
| LawChange | law_change.py | 법령 변경 감지 로그 |
| RevisionDetectionResult | revision_detection_result.py | 개정 판별 결과 |
| LawRevisionReason | law_revision_reason.py | 법령 제개정이유 캐시 |
| LlmAnalysisResult | llm_analysis_result.py | AI 분석 결과 |
| LlmProvider | llm_provider.py | AI 프로바이더 설정 |
| OrdinanceText | ordinance_text.py | 조례 원문 저장 |
| AmendmentReview | review.py | 개정 검토 (legacy) |
| LawAmendment | amendment.py | 법령 개정 정보 (legacy) |
| LawSnapshot | law_snapshot.py | 법령 스냅샷 |
| Amendment | amendment.py | 개정 기본정보 |

## 4. API 엔드포인트 (~50개)

### Auth (/auth)
- POST /login, GET /me, PUT /change-password

### Ordinances (/ordinances) - 가장 큼
- GET / (목록), GET /export (엑셀)
- POST /sync, /upload, /create, /search-api, /register-from-api
- POST /update-all-info
- GET /{id}, GET /{id}/parent-laws
- POST /{id}/parent-laws, PUT /parent-laws/{id}, DELETE /parent-laws/{id}
- POST /{id}/law-mappings, PUT /law-mappings/{id}, DELETE /law-mappings/{id}
- POST /{id}/no-parent-law, DELETE /{id}/no-parent-law
- POST /{id}/detect, GET /{id}/detection-results
- POST /{id}/start-review, POST /{id}/clear-revision
- POST /{id}/sync-parent-laws
- GET /reviews-all

### Laws (/laws)
- GET /, POST /sync, GET /{id}
- GET /{id}/revision-reason, GET /{id}/articles

### Law Changes (/law-changes)
- GET /, GET /{id}

### Reviews (/reviews)
- GET /, POST /, PUT /{id}, DELETE /{id}

### Departments (/departments)
- GET /, POST /, PUT /{id}, DELETE /{id}

### Dashboard (/dashboard)
- GET /statistics, GET /recent-changes, GET /revision-needed

### AI Analysis
- POST /{ordinance_id}/ai-analysis, GET /{ordinance_id}/ai-analysis

### Admin (/admin)
- GET /maintenance, POST /maintenance
- POST /sync-laws, GET /sync-status

### Health
- GET /health

## 5. 서비스 모듈 (14개)

| 서비스 | 크기 | 핵심 기능 |
|--------|------|----------|
| law_sync_service.py | 53KB | 법제처 API 법령 동기화 |
| ordinance_service.py | 53KB | 조례 CRUD, 벌크 import/export |
| llm_analysis_service.py | 20KB | AI 리뷰 생성 |
| department_service.py | 19KB | 부서 관리 |
| revision_detection_service.py | 15KB | 개정 판별 3탭 (날짜/조문/이유) |
| dashboard_service.py | 14KB | 대시보드 통계 |
| law_api_service.py | 11KB | 법제처 API 연동 |
| auth_service.py | 9KB | 인증/JWT |
| llm_client.py | 7KB | LLM 프로바이더 추상화 |
| review_service.py | 4KB | 리뷰 관리 |
| amendment_parser.py | 2KB | 개정 내용 파싱 |
| amendment_service.py | 2KB | 개정 추적 |
| sync_service.py | 2KB | 동기화 조정 |
| llm_rate_limiter.py | 1KB | LLM 속도제한 |

## 6. 외부 연동

### 법제처 API (moleg_client.py - 25KB)
- Base: https://www.law.go.kr/DRF
- lawSearch.do?target=law (법령 검색)
- lawService.do?target=law (법령 상세 - 조문, 제개정이유)
- lawService.do?target=ordin (조례 상세)
- lnkOrg.do (연계 조례)
- Exponential backoff, 30초 timeout, XML 파싱

### LLM (llm_client.py)
- Anthropic Claude, OpenAI GPT, Google Gemini
- Token bucket rate limiting

## 7. 프론트엔드 페이지 (27개)

- 인증: Login, Register, ForgotPassword, ResetPassword, ChangePassword
- 메인: OrdinanceList, OrdinanceDetail, LawList, RevisionNeededList
- 분석: DetectionCompare (3탭), AiAnalytics
- 리뷰: ReviewList, ReviewDetail
- 관리: AdminSettings, DepartmentList, DepartmentDetail, LawChangeList
- 기타: Dashboard, Landing, Statistics, Maintenance, AmendmentList, ArticleList, ArticleDetail

## 8. 핵심 비즈니스 플로우

1. 조례 브라우징: Frontend → FastAPI → PostgreSQL
2. 법령 동기화: Celery Beat (매일 9시) → 법제처 API → DB
3. 개정 판별: 3가지 방법 (날짜비교, 조문비교, 이유비교)
4. AI 리뷰: LLM API → 요약/검토의견 생성
5. 변경 추적: 법령변경 감지 → 대시보드 알림
