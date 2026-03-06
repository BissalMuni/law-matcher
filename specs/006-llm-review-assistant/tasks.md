# Tasks: LLM 기반 검토의견 자동 생성

**Input**: Design documents from `/specs/006-llm-review-assistant/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-contracts.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

## Phase 1: Setup

**Purpose**: 의존성 및 환경 설정

- [x] T001 [P] LLM SDK 패키지 추가 — `backend/requirements.txt`에 `anthropic`, `openai`, `google-generativeai`, `pyyaml` 추가
- [x] T002 [P] LLM 환경변수 추가 — `backend/core/config.py`에 `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_AI_API_KEY`, `LLM_TIMEOUT(30)`, `LLM_MAX_RETRIES(2)` 설정
- [x] T003 [P] `.env.example` 업데이트 — LLM 관련 환경변수 템플릿 추가
- [x] T004 [P] Docker 환경변수 — `docker-compose.yml`의 backend 서비스에 LLM API 키 환경변수 추가

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 User Story에 필요한 공통 인프라. 이 Phase 완료 전까지 US 작업 불가

- [x] T005 `LlmProvider` 모델 생성 — `backend/models/llm_provider.py`. provider_name(UNIQUE), display_name, model_name, api_key_env_name, is_active, rate_limit_per_minute, created_at, updated_at
- [x] T006 [P] `LlmAnalysisResult` 모델 생성 — `backend/models/llm_analysis_result.py`. ordinance_id(FK), law_id(FK), law_proclaimed_date, status(pending/success/failed), input_hash(CHAR64), prompt_text, summary_text, review_draft_text, review_draft_result, provider_name, model_name, token_usage(JSONB), error_message, created_at. UNIQUE(ordinance_id, law_id, law_proclaimed_date)
- [x] T007 [P] `OrdinanceReview` 모델 수정 — `backend/models/ordinance_review.py`에 `is_ai_generated(BOOLEAN)`, `ai_modified(BOOLEAN)`, `ai_analysis_id(FK → llm_analysis_results.id, SET NULL)` 필드 추가
- [x] T008 Alembic 마이그레이션 3건 — `backend/alembic/versions/`에 (1) llm_providers 테이블 생성 + 초기 데이터 (claude/chatgpt/gemini), (2) llm_analysis_results 테이블 생성, (3) ordinance_reviews AI 필드 추가
- [x] T009 LLM 클라이언트 추상화 — `backend/services/llm_client.py`
  - `LlmClient` ABC: `async def generate(prompt, system_prompt) -> LlmResponse`
  - `ClaudeClient(LlmClient)`: anthropic SDK messages.create()
  - `ChatGptClient(LlmClient)`: openai SDK chat.completions.create() (response_format=json_object)
  - `GeminiClient(LlmClient)`: google-generativeai generate_content()
  - `get_active_llm_client(db)`: DB is_active=True 프로바이더 → 해당 클라이언트 반환
  - 공통: 타임아웃 30초, 재시도 최대 2회 (지수 백오프), JSON 파싱 검증
- [x] T010 [P] 프롬프트 YAML 템플릿 — `backend/config/prompts.yaml`. 통합 분석 system_prompt + user_prompt (변수: law_name, law_proclaimed_date, revision_reason, amendment_content, ordinance_name), 토큰 초과 시 요약 프롬프트, JSON 출력 형식 정의
- [x] T011 [P] Rate Limiter — `backend/services/llm_rate_limiter.py`. Redis INCR+EXPIRE(60s) 패턴, LlmProvider.rate_limit_per_minute 참조, 초과 시 429 에러
- [x] T012 [P] LLM 관련 Pydantic 스키마 — `backend/schemas/llm.py`. AiAnalyzeRequest(law_id), AiAnalyzeResponse, AiResultsResponse, LlmProviderResponse, LlmProviderUpdate, AiAnalyticsResponse
- [x] T013 [P] 프론트엔드 AI 타입 정의 — `frontend/src/types/api.ts`에 LlmAnalysisResult, LlmProvider, AiAnalyzeResponse, AiAnalyticsData 타입 추가
- [x] T014 [P] `AiLabel` 공통 컴포넌트 — `frontend/src/components/ai/AiLabel.tsx`. "AI 생성" 배지 (Constitution VIII 필수)

**Checkpoint**: Foundation ready — User Story 구현 시작 가능

---

## Phase 3: User Story 1 — AI 통합 분석 (Priority: P1) MVP

**Goal**: "AI 분석" 버튼 1회 클릭 → 1회 LLM 호출로 개정내용 요약 + 검토의견 초안을 동시 생성

**Independent Test**: 조례 상세 → AI 분석 버튼 → 로딩 스피너 → 요약 표시 + 검토의견 모달에 초안 자동 채움

### Implementation

- [x] T015 [US1] AI 통합 분석 서비스 — `backend/services/llm_analysis_service.py`
  - `analyze_ordinance(ordinance_id, law_id, db)`: 메인 진입점
  - 1회 실행 검증: UNIQUE 제약 + status 확인 (실패 건 1회 재시도 허용)
  - 법령 버전 확인: law.proclaimed_date → law_proclaimed_date
  - 입력 데이터 수집: LawRevisionReason.revision_reason + amendment_content (005 의존)
  - input_hash 계산: SHA-256 (입력 데이터만, 프롬프트 제외)
  - 토큰 초과 검사 → 초과 시 1차 요약 LLM 호출 (2단계 처리)
  - 프롬프트 렌더링: prompts.yaml 로드 + 변수 치환
  - Rate Limit 검사 (llm_rate_limiter)
  - LLM 호출 → JSON 파싱 → 파싱 실패 시 1회 재시도 → 2회 실패 시 에러
  - 결과 DB 저장: summary_text, review_draft_text, review_draft_result, status
  - `get_analysis_results(ordinance_id, law_id?)`: 결과 조회
- [x] T016 [US1] AI 분석 API 엔드포인트 — `backend/api/v1/llm_analysis.py`
  - `POST /ordinances/{id}/ai-analyze`: 통합 AI 분석 실행. JWT 인증, body: {law_id}
  - `GET /ordinances/{id}/ai-results`: 분석 결과 조회. query: law_id(optional)
  - 에러: 400(매핑 미존재), 404(조례 미발견), 409(이미 완료), 422(제개정이유 없음), 429(Rate Limit), 502(LLM 오류), 503(프로바이더 미설정), 504(타임아웃)
  - `backend/api/v1/router.py`에 라우터 등록
- [x] T017 [P] [US1] 프론트엔드 AI API 함수 — `frontend/src/services/api.ts`에 `aiApi.analyze(ordinanceId, lawId)`, `aiApi.getResults(ordinanceId, lawId?)` 추가
- [x] T018 [US1] `AiAnalysisButton` 컴포넌트 — `frontend/src/components/ai/AiAnalysisButton.tsx`
  - "AI 분석" 버튼 + 로딩 스피너 (동기 대기)
  - 이미 완료 시 비활성화 (FR-012)
  - 에러 시 "AI 분석을 수행할 수 없습니다. 직접 검토해 주세요" 안내
- [x] T019 [P] [US1] `AiSummaryPanel` 컴포넌트 — `frontend/src/components/ai/AiSummaryPanel.tsx`
  - AI 요약 구조화 표시 (주요 변경사항, 변경 조문 목록, 조례 영향)
  - AiLabel 배지 + 프로바이더/모델명 표시
  - 법령별 결과 구분 (상위법령 복수 연결 시)
- [x] T020 [P] [US1] `AiDraftModal` 컴포넌트 — `frontend/src/components/ai/AiDraftModal.tsx`
  - 검토의견 작성 모달에 AI 초안 자동 채움 (review_result + review_content)
  - 수정 여부 추적 (ai_modified): 원본과 비교하여 수정 시 true
  - AiLabel 배지 표시
- [x] T021 [US1] OrdinanceDetail 통합 — `frontend/src/pages/OrdinanceDetail.tsx` 수정
  - 개정검토 탭에 법령별 AiAnalysisButton + AiSummaryPanel 배치
  - 검토의견 작성 모달에 AiDraftModal 연동
  - 검토의견 제출 시 is_ai_generated, ai_modified, ai_analysis_id 전송
- [x] T022 [US1] 검토의견 AI 메타데이터 처리 — `backend/services/ordinance_service.py` 수정
  - 검토의견 생성/수정 시 is_ai_generated, ai_modified, ai_analysis_id 저장 로직

**Checkpoint**: AI 통합 분석 → 요약 표시 + 초안 자동 채움 → 메타데이터 기록 독립 동작 확인

---

## Phase 4: User Story 3(P2) — AI 결과 보존 및 재조회

**Goal**: 이미 생성된 AI 결과를 즉시 표시하고 버튼 비활성화. 법령 새 버전 시 재분석 허용

**Independent Test**: 최초 분석 → 결과 저장 → 재조회 시 저장 결과 반환 → 버튼 비활성화 → 법령 재동기화 → 새 분석 가능

### Implementation

- [x] T023 [US3] 프론트엔드 결과 캐시 표시 — `AiAnalysisButton`, `AiSummaryPanel`, `AiDraftModal` 수정
  - 페이지 로드 시 `aiApi.getResults()` 호출로 기존 결과 확인
  - 결과 있으면 즉시 표시 + "AI 분석" 버튼 비활성화 (FR-012)
  - 결과 없으면 버튼 활성화
- [x] T024 [US3] 법령 버전 기반 재분석 — `backend/services/llm_analysis_service.py` 수정
  - law.proclaimed_date 변경 감지: UNIQUE(ordinance_id, law_id, law_proclaimed_date)로 새 버전 허용
  - 기존 결과는 이력으로 보존 (FR-005a)

**Checkpoint**: 결과 재조회 + 버튼 비활성화 + 법령 변경 시 재분석 확인

---

## Phase 5: User Story 4(P2) — LLM 프로바이더/모델 관리

**Goal**: 관리자가 설정 탭에서 프로바이더 모델명 변경, 활성 전환, Rate Limit 조정

**Independent Test**: 관리자 → LLM 설정 탭 → 모델명 변경 → 활성 프로바이더 전환 → AI 분석 시 변경 반영

### Implementation

- [x] T025 [US4] 프로바이더 관리 API — `backend/api/v1/admin.py` (신규 또는 기존 확장)
  - `GET /admin/llm-providers`: 프로바이더 목록 (api_key_configured 런타임 계산, 키 마스킹)
  - `PATCH /admin/llm-providers/{id}`: 모델명/활성 상태/Rate Limit 변경
  - is_active=true 설정 시 API 키 환경변수 존재 검증
  - 동시 1개만 active 보장 (기존 active 자동 비활성화)
  - `backend/api/v1/router.py`에 라우터 등록
- [x] T026 [P] [US4] 프론트엔드 Admin API 함수 — `frontend/src/services/api.ts`에 `adminApi.getLlmProviders()`, `adminApi.updateLlmProvider(id, data)` 추가
- [x] T027 [US4] 관리자 LLM 설정 탭 — `frontend/src/pages/AdminSettings.tsx` (신규)
  - 프로바이더 목록 테이블 (모델명, 활성 상태, API 키 설정 여부, Rate Limit)
  - 인라인 편집: 모델명 변경, 활성 프로바이더 전환 (Switch), Rate Limit 조정
  - 관리자 네비게이션 메뉴에 "LLM 설정" 추가

**Checkpoint**: 프로바이더 관리 → 활성 전환 → AI 분석 시 변경된 프로바이더로 호출 확인

---

## Phase 6: User Story 3(P3) — AI 분석 이력 조회

**Goal**: 관리자가 AI 생성 건수, 채택률, 프로바이더별 통계를 조회

**Independent Test**: 관리자 → AI 분석 이력 → 기간별 생성 건수, 채택률 확인

### Implementation

- [x] T028 [US3b] AI 통계 서비스 — `backend/services/llm_analysis_service.py`에 `get_ai_analytics(start_date, end_date)` 추가. total_analyses, success/failed 수, 채택률(is_ai_generated+ai_modified 기반), 프로바이더별 분포
- [x] T029 [US3b] AI 통계 API — `backend/api/v1/admin.py`에 `GET /admin/ai-analytics`. 관리자 전용. query: start_date, end_date
- [x] T030 [US3b] AI 이력 페이지 — `frontend/src/pages/AiAnalytics.tsx` (신규). 기간 선택 DatePicker, 요약 카드 (생성 건수, 성공률, 채택률), 프로바이더별 사용량 테이블

**Checkpoint**: 관리자 AI 통계 페이지 동작 확인

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 통합 검증 및 보안 점검

- [x] T031 [P] 네비게이션 메뉴 — AdminSettings, AiAnalytics 페이지를 관리자 전용 메뉴에 추가 (MainLayout.tsx 수정)
- [x] T032 [P] LLM 장애 격리 검증 — LLM API 키 미설정/장애 상태에서 수동 검토의견 작성이 정상 동작하는지 확인 (FR-006)
- [x] T033 [P] 보안 전송 점검 — LLM API로 전송 데이터가 공개 정보(제개정이유, 개정문, 조례 원문)만 포함하는지 검증 (VI. 보안)
- [x] T034 에러 메시지 한국어 통일 — 모든 AI 관련 에러 응답 메시지 한국어 확인 (VII. 사용자 중심 설계)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — 즉시 시작
- **Foundational (Phase 2)**: Setup 완료 후 시작. **모든 US를 차단**
- **US1 (Phase 3)**: Foundational 완료 후 시작. **MVP**
- **US3-P2 (Phase 4)**: US1 완료 후 시작 (결과 재조회는 생성 기능에 의존)
- **US4 (Phase 5)**: Foundational 완료 후 시작. US1과 병렬 가능 (API/UI 분리)
- **US3-P3 (Phase 6)**: US1 완료 후 시작 (통계는 데이터 축적 후 의미)
- **Polish (Phase 7)**: 모든 US 완료 후

### Feature Dependencies

- **005-revision-detection-tabs** 선행 필요: `LawRevisionReason` 테이블의 `revision_reason`, `amendment_content` 데이터를 LLM 입력으로 사용

### Parallel Opportunities

- T001~T004: 모두 병렬
- T006, T007, T010~T014: 모두 병렬 (T005 모델 생성 후)
- T017, T019, T020: 프론트엔드 컴포넌트 병렬
- US1(Phase 3)과 US4(Phase 5): 병렬 가능 (서로 다른 파일)

---

## Implementation Strategy

### MVP First (US1 Only)

1. Phase 1: Setup (T001-T004)
2. Phase 2: Foundational (T005-T014)
3. Phase 3: US1 AI 통합 분석 (T015-T022)
4. **STOP and VALIDATE**: AI 분석 → 요약 + 초안 독립 동작 확인

### Full Implementation

1. Setup → Foundational → Foundation ready
2. US1 AI 통합 분석 (P1) → MVP 검증
3. US3-P2 결과 보존 + US4 프로바이더 관리 (병렬 가능)
4. US3-P3 AI 이력 (후순위)
5. Polish → 통합 검증
