# Tasks: LLM 기반 검토의견 자동 생성

**Input**: Design documents from `/specs/006-llm-review-assistant/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/api-contracts.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

## Phase 1: Setup

**Purpose**: 프로젝트 의존성 및 환경 설정

- [ ] T001 [P] LLM 프로바이더 패키지 설치: `anthropic`, `openai`, `google-generativeai`를 `requirements.txt`에 추가
- [ ] T002 [P] LLM 환경변수 추가 — `backend/core/config.py`에 `LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_AI_API_KEY`, `LLM_TIMEOUT(30)`, `LLM_MAX_RETRIES(2)` 설정 추가
- [ ] T003 [P] `.env.example` 업데이트 — LLM 관련 환경변수 템플릿 추가

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 User Story에 필요한 공통 인프라. 이 Phase 완료 전까지 US 작업 불가

- [ ] T004 `LlmAnalysisResult` 모델 생성 — `backend/models/llm_analysis_result.py`. ordinance_id(FK), law_id(FK), analysis_type, input_hash, prompt, response_text, model_name, token_usage, status, error_message, created_at. UNIQUE(ordinance_id, law_id, analysis_type)
- [ ] T005 [P] `OrdinanceReview` 모델 수정 — `backend/models/ordinance_review.py`에 `is_ai_generated(BOOLEAN)`, `ai_modified(BOOLEAN)`, `ai_model(VARCHAR)`, `ai_generated_at(TIMESTAMP)` 필드 추가
- [ ] T006 Alembic 마이그레이션 생성 — `backend/alembic/versions/`에 (1) llm_analysis_results 테이블 생성, (2) ordinance_reviews AI 필드 추가 마이그레이션 2개 작성
- [ ] T007 LLM 프로바이더 추상화 클라이언트 구현 — `backend/services/llm_client.py`
  - `LlmClient` ABC 인터페이스: `async def generate(prompt, system_prompt) -> LlmResponse`
  - `AnthropicClient(LlmClient)`: Claude API 어댑터
  - `OpenAIClient(LlmClient)`: ChatGPT API 어댑터
  - `GeminiClient(LlmClient)`: Gemini API 어댑터
  - `get_llm_client()`: `LLM_PROVIDER` 환경변수로 클라이언트 팩토리
  - 공통: 타임아웃(30초), 재시도(최대 2회, 지수 백오프), 토큰 사용량 추적
- [ ] T008 [P] LLM 관련 Pydantic 스키마 정의 — `backend/schemas/llm.py`. AiSummaryResponse, AiDraftResponse, AiResultsResponse, AiAnalyticsResponse, LlmResponse(내부용)
- [ ] T009 [P] 프론트엔드 AI 타입 정의 — `frontend/src/types/api.ts`에 AiSummaryResult, AiDraftResult, AiResultItem, AiAnalytics 타입 추가
- [ ] T010 [P] `AiLabel` 공통 컴포넌트 — `frontend/src/components/ai/AiLabel.tsx`. "AI 생성" 배지 (Constitution VIII: AI 생성 라벨 필수)

**Checkpoint**: Foundation ready — User Story 구현 시작 가능

---

## Phase 3: User Story 1 — 개정내용 AI 요약 조회 (Priority: P1)

**Goal**: 조례 상세 페이지에서 "AI 요약" 버튼 클릭 시 상위법령 제개정이유를 LLM이 분석하여 요약 표시

**Independent Test**: 조례 상세 → AI 요약 버튼 → 개정내용 요약 표시 (주요 변경사항, 변경 조문, 조례 영향)

### Implementation

- [ ] T011 [US1] AI 요약 서비스 로직 — `backend/services/llm_review_service.py`의 `generate_summary(ordinance_id, law_id)` 구현
  - LawRevisionReason에서 제개정이유/개정문 데이터 조회 (005 의존)
  - input_hash 계산 (SHA-256)
  - 1회 실행 검증: LlmAnalysisResult UNIQUE 체크
  - 프롬프트 템플릿: 한국어, 법률 용어, 구조화된 출력 (주요 변경사항 / 변경 조문 / 조례 영향)
  - LLM 호출 → 결과 DB 저장 (prompt + response 모두 보존)
- [ ] T012 [US1] AI 요약 API 엔드포인트 — `backend/api/v1/llm_reviews.py`의 `POST /ordinances/{id}/ai-summary`
  - JWT 인증 (FR-009)
  - 409: 이미 완료, 422: 제개정이유 없음, 502: LLM 오류, 504: 타임아웃
- [ ] T013 [P] [US1] 프론트엔드 AI API 호출 함수 — `frontend/src/services/api.ts`에 `requestAiSummary(ordinanceId)`, `getAiResults(ordinanceId)` 추가
- [ ] T014 [US1] `AiSummaryPanel` 컴포넌트 — `frontend/src/components/ai/AiSummaryPanel.tsx`
  - "AI 요약" 버튼 + 로딩 상태
  - 요약 결과 구조화 표시 (주요 변경사항, 변경 조문, 조례 영향)
  - AiLabel 배지 표시
  - 에러 시 "AI 요약을 생성할 수 없습니다. 직접 검토해 주세요" 안내
  - 법령별 개별 표시 (상위법령 복수 연결 시)
- [ ] T015 [US1] `OrdinanceDetail.tsx` 수정 — 기존 조례 상세 페이지에 AiSummaryPanel 통합. 상위법령 탭 또는 별도 AI 섹션에 배치

**Checkpoint**: AI 요약 생성 및 표시 독립 동작 확인

---

## Phase 4: User Story 2 — 검토의견 초안 자동 생성 (Priority: P1)

**Goal**: 검토의견 작성 시 "AI 초안 생성" 버튼 클릭으로 LLM이 초안(개정필요/개정불필요 + 사유)을 자동 생성하여 입력 필드에 채움

**Independent Test**: 검토의견 작성 → AI 초안 생성 → 입력 필드 자동 채움 → 담당자 수정 후 제출

### Implementation

- [ ] T016 [US2] AI 초안 서비스 로직 — `backend/services/llm_review_service.py`의 `generate_draft(ordinance_id, law_id)` 구현
  - 제개정이유 + 조례 정보 → LLM → 결과(개정필요/개정불필요) + 의견 내용
  - 1회 실행 검증 (summary와 동일 패턴)
  - 프롬프트: 검토 결과(개정필요 or 개정불필요) + 구체적 사유 + 관련 조문 언급
- [ ] T017 [US2] AI 초안 API 엔드포인트 — `backend/api/v1/llm_reviews.py`의 `POST /ordinances/{id}/ai-draft`
  - JWT 인증, 에러 응답 ai-summary와 동일
- [ ] T018 [P] [US2] 프론트엔드 AI 초안 API 함수 — `frontend/src/services/api.ts`에 `requestAiDraft(ordinanceId)` 추가
- [ ] T019 [US2] `AiDraftButton` 컴포넌트 — `frontend/src/components/ai/AiDraftButton.tsx`
  - "AI 초안 생성" 버튼 + 로딩 상태
  - 생성 결과를 검토의견 입력 필드(review_result, review_content)에 자동 채움
  - AiLabel 배지 표시
- [ ] T020 [US2] 검토의견 작성 UI 수정 — `frontend/src/pages/OrdinanceDetail.tsx`의 검토의견 모달/폼에 AiDraftButton 통합
- [ ] T021 [US2] AI 메타데이터 추적 — 검토의견 제출 시 `is_ai_generated`, `ai_modified`, `ai_model`, `ai_generated_at` 값 설정
  - 프론트: AI 초안 수정 여부 감지 (`ai_modified` 판단)
  - 백엔드: `backend/services/ordinance_service.py`의 검토의견 생성/수정 로직에 AI 필드 처리 추가

**Checkpoint**: AI 초안 생성 → 입력 필드 자동 채움 → 수정/미수정 제출 → 메타데이터 기록 확인

---

## Phase 5: User Story 3 — AI 결과 보존 및 재조회 (Priority: P2)

**Goal**: 이미 생성된 AI 분석 결과를 저장/재조회하고, 완료된 건은 버튼 비활성화

**Independent Test**: 최초 요청 → 결과 저장 → 재조회 시 저장된 결과 반환 → AI 버튼 비활성화

### Implementation

- [ ] T022 [US3] AI 결과 조회 API — `backend/api/v1/llm_reviews.py`의 `GET /ordinances/{id}/ai-results`. 법령별 분석 결과(summary + review_draft) 목록 반환. 없으면 빈 배열
- [ ] T023 [US3] 프론트엔드 결과 캐시 표시 — `AiSummaryPanel`, `AiDraftButton` 수정
  - 페이지 로드 시 `getAiResults()` 호출하여 기존 결과 확인
  - 결과가 있으면 즉시 표시 + 버튼 비활성화 (FR-012)
  - 결과가 없으면 버튼 활성화
- [ ] T024 [US3] 법령 재동기화 시 새 분석 허용 — `backend/services/llm_review_service.py`에 input_hash 비교 로직 추가. 해시 불일치 시 기존 결과 이력 보존 + 새 분석 1회 허용 (FR-005a)

**Checkpoint**: 기존 결과 재조회 → 버튼 비활성화 → 법령 변경 시 재분석 가능 확인

---

## Phase 6: User Story 4 — AI 분석 이력 조회 (Priority: P3)

**Goal**: 관리자가 AI 생성 건수, 채택률 등 통계를 조회

**Independent Test**: 관리자 → AI 분석 이력 → 기간별 생성 건수, 채택률 확인

### Implementation

- [ ] T025 [US4] AI 통계 서비스 — `backend/services/llm_review_service.py`에 `get_ai_analytics(start_date, end_date)` 추가. 요약 건수, 초안 건수, 채택률(ai_modified=false 비율), 모델별 사용량
- [ ] T026 [US4] AI 통계 API — `backend/api/v1/llm_reviews.py`의 `GET /admin/ai-analytics`. 관리자 전용 (user_type=ADMIN 검증)
- [ ] T027 [US4] `AiAnalytics` 페이지 — `frontend/src/pages/AiAnalytics.tsx`. 기간 선택, 요약/초안 건수 카드, 채택률 표시, 모델별 분포

**Checkpoint**: 관리자 AI 통계 페이지 동작 확인

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 전체 기능 통합 검증 및 보안 점검

- [ ] T028 [P] 프론트엔드 네비게이션 — AI 분석 이력 메뉴를 관리자 네비게이션에 추가 (FR-007 역할별 메뉴, 001-login spec 참조)
- [ ] T029 [P] LLM API 장애 격리 검증 — LLM API 키 미설정/장애 상태에서 수동 검토의견 작성이 정상 동작하는지 확인 (FR-006)
- [ ] T030 에러 메시지 한국어 통일 — 모든 AI 관련 에러 응답의 메시지가 한국어 UI 기준에 맞는지 확인 (VII. 사용자 중심 설계)
- [ ] T031 [P] 보안 전송 정책 점검 — LLM API로 전송되는 데이터가 공공데이터(제개정이유, 개정문, 조례 원문)만 포함하는지 검증. 사용자 개인정보, 내부 의견 등 민감 정보가 프롬프트에 포함되지 않도록 확인 (VI. 보안 기본 적용)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — 즉시 시작
- **Foundational (Phase 2)**: Setup 완료 후 시작. **모든 US를 차단**
- **US1 (Phase 3)**: Foundational 완료 후 시작
- **US2 (Phase 4)**: Foundational 완료 후 시작. US1과 병렬 가능하나, `llm_review_service.py` 파일 공유로 US1 선행 권장
- **US3 (Phase 5)**: US1 + US2 완료 후 시작 (결과 보존/재조회는 생성 기능에 의존)
- **US4 (Phase 6)**: US1 + US2 완료 후 시작 (통계는 데이터 축적 후 의미 있음)
- **Polish (Phase 7)**: 모든 US 완료 후

### Feature Dependencies

- **005-revision-detection-tabs** 선행 필요: `LawRevisionReason` 테이블의 `revision_reason`, `amendment_content` 데이터를 LLM 입력으로 사용

### Within Each User Story

- 서비스 로직 → API 엔드포인트 → 프론트엔드 순서
- 백엔드와 프론트엔드 타입/API 함수는 [P]로 병렬 가능

### Parallel Opportunities

- T001, T002, T003: 모두 병렬
- T005, T008, T009, T010: 모두 병렬 (T004 모델 생성 후)
- T013, T018: 프론트 API 함수는 병렬
- US1과 US2의 프론트엔드 컴포넌트(T014, T019): 병렬 가능

---

## Implementation Strategy

### MVP First (US1 Only)

1. Phase 1: Setup (T001-T003)
2. Phase 2: Foundational (T004-T010)
3. Phase 3: US1 AI 요약 (T011-T015)
4. **STOP and VALIDATE**: AI 요약 독립 동작 확인
5. Demo 가능

### Full Implementation

1. Setup → Foundational → Foundation ready
2. US1 AI 요약 → Test → AI 요약 동작
3. US2 검토의견 초안 → Test → 초안 생성 + 메타데이터
4. US3 결과 보존/재조회 → Test → 버튼 비활성화 + 캐시
5. US4 AI 이력 (P3, optional) → Test → 관리자 통계
6. Polish → 통합 검증

---

## Notes

- LLM 클라이언트(T007)는 III. 외부 의존 격리 원칙의 핵심. 반드시 별도 모듈로 격리
- 1회 실행 원칙(Constitution VIII)은 DB UNIQUE 제약(T004) + 서비스 로직(T011, T016) 양쪽에서 보장
- AI 생성 라벨(T010)은 Constitution VIII 필수 요구사항
- 법령별 개별 분석: 복수 상위법령 연결 시 각 (ordinance_id, law_id) 조합에 대해 별도 분석
- 프로바이더 추상화: Claude/ChatGPT/Gemini 3개 어댑터 구현, `LLM_PROVIDER` 환경변수로 선택
