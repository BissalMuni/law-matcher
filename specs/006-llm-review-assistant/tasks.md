# Tasks: LLM 기반 검토의견 자동 생성

**Input**: Design documents from `/specs/006-llm-review-assistant/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: LLM 기능 도입 준비

- [ ] T001 LLM 라우터 연결 지점 점검 in /home/jinkui/law-matcher/backend/api/v1/router.py
- [ ] T002 LLM 환경변수 로딩 지점 점검 in /home/jinkui/law-matcher/backend/core/config.py
- [ ] T003 [P] 프론트 AI 컴포넌트 배치 지점 점검 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: LLM 호출/저장 공통 인프라 구축

- [ ] T004 LLM 설정값(API 키/모델/타임아웃) 추가 in /home/jinkui/law-matcher/backend/core/config.py
- [ ] T005 LlmAnalysisResult ORM 모델 구현 in /home/jinkui/law-matcher/backend/models/llm_analysis_result.py
- [ ] T006 [P] OrdinanceReview AI 메타 필드 추가 in /home/jinkui/law-matcher/backend/models/ordinance_review.py
- [ ] T007 LLM 결과/리뷰 AI 필드 마이그레이션 추가 in /home/jinkui/law-matcher/backend/alembic/versions/20260228_add_llm_analysis_results.py
- [ ] T008 LLM 요청/응답 스키마 정의 in /home/jinkui/law-matcher/backend/schemas/llm.py

---

## Phase 3: User Story 1 - 개정내용 AI 요약 조회 (Priority: P1)

**Goal**: 제개정이유 기반 AI 요약을 생성/조회한다

**Independent Test**: 요약 요청 시 결과와 메타데이터 반환

- [ ] T009 [US1] LLM 클라이언트 격리 모듈 구현 in /home/jinkui/law-matcher/backend/services/llm_client.py
- [ ] T010 [US1] 요약 생성 서비스 로직 구현 in /home/jinkui/law-matcher/backend/services/llm_review_service.py
- [ ] T011 [US1] 요약 API 엔드포인트 구현 in /home/jinkui/law-matcher/backend/api/v1/llm_reviews.py
- [ ] T012 [P] [US1] 요약 패널 UI 및 API 연동 구현 in /home/jinkui/law-matcher/frontend/src/components/ai/AiSummaryPanel.tsx

---

## Phase 4: User Story 2 - 검토의견 초안 자동 생성 (Priority: P1)

**Goal**: 검토의견 초안을 자동 생성해 입력폼에 반영한다

**Independent Test**: 초안 생성 버튼 실행 후 입력폼 자동 채움

- [ ] T013 [US2] 초안 생성 프롬프트/응답 매핑 구현 in /home/jinkui/law-matcher/backend/services/llm_review_service.py
- [ ] T014 [US2] 초안 생성 API 엔드포인트 구현 in /home/jinkui/law-matcher/backend/api/v1/llm_reviews.py
- [ ] T015 [P] [US2] 초안 생성 버튼 컴포넌트 구현 in /home/jinkui/law-matcher/frontend/src/components/ai/AiDraftButton.tsx
- [ ] T016 [US2] 조례 상세 입력폼 자동 채움 연동 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx

---

## Phase 5: User Story 3 - AI 결과 보존 및 재조회 (Priority: P2)

**Goal**: 결과를 저장하고 1회 실행 원칙을 보장한다

**Independent Test**: 재요청 시 기존 결과 재조회, 재실행 차단

- [ ] T017 [US3] input_hash 기반 1회 실행 제한 로직 구현 in /home/jinkui/law-matcher/backend/services/llm_review_service.py
- [ ] T018 [US3] AI 결과 저장/재조회 API 구현 in /home/jinkui/law-matcher/backend/api/v1/llm_reviews.py
- [ ] T019 [P] [US3] AI 생성 라벨 컴포넌트 구현 in /home/jinkui/law-matcher/frontend/src/components/ai/AiLabel.tsx
- [ ] T020 [US3] 재실행 비활성화 UI 반영 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx

---

## Phase 6: User Story 4 - AI 분석 이력 조회 (Priority: P3)

**Goal**: 관리자가 AI 분석 이력을 조회한다

**Independent Test**: 기간/상태 필터로 이력 조회 가능

- [ ] T021 [US4] AI 이력 조회 서비스/쿼리 구현 in /home/jinkui/law-matcher/backend/services/llm_review_service.py
- [ ] T022 [US4] AI 이력 조회 API 구현 in /home/jinkui/law-matcher/backend/api/v1/llm_reviews.py
- [ ] T023 [US4] AI 이력 페이지/라우트 연동 구현 in /home/jinkui/law-matcher/frontend/src/pages/AiAnalytics.tsx

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: LLM 기능 운영 안정성/문서 보강

- [ ] T024 [P] LLM 타임아웃/재시도 로깅 보강 in /home/jinkui/law-matcher/backend/services/llm_client.py
- [ ] T025 LLM 실패 시 폴백 메시지 정리 in /home/jinkui/law-matcher/frontend/src/components/ai/AiSummaryPanel.tsx
- [ ] T026 API 응답 스키마/타입 일관성 정리 in /home/jinkui/law-matcher/frontend/src/services/api.ts
- [ ] T027 보안 전송 정책(공개 데이터만) 반영 점검 in /home/jinkui/law-matcher/backend/services/llm_review_service.py
- [ ] T028 LLM 기능 문서 업데이트 in /home/jinkui/law-matcher/docs/llm-review-assistant.md

---

## Dependencies & Execution Order

- Setup → Foundational 완료 후 US1~US4 진행
- P1(US1~US2) 우선 후 US3, US4 진행
- Polish는 전체 완료 후 진행

## Parallel Opportunities

- T003, T006
- T012, T015, T019
- T024

## Implementation Strategy

1. MVP: US1 + US2
2. 안정화: US3
3. 운영: US4
4. 마무리: Polish
