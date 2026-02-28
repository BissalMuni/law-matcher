# Tasks: 개정 검토 대상 판별 방식 병렬 탭

**Input**: Design documents from `/specs/005-revision-detection-tabs/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 3탭 판별 기능 구현 준비

- [ ] T001 판별 API 라우팅 진입점 점검 in /home/jinkui/law-matcher/backend/api/v1/router.py
- [ ] T002 판별 전용 스키마 파일 생성 in /home/jinkui/law-matcher/backend/schemas/revision.py
- [ ] T003 [P] 탭 컴포넌트 인덱스 파일 생성 in /home/jinkui/law-matcher/frontend/src/components/detection/index.ts
- [ ] T004 [P] 비교 페이지 파일 생성 in /home/jinkui/law-matcher/frontend/src/pages/DetectionCompare.tsx

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 공통 데이터/서비스 기반 구축

- [ ] T005 LawRevisionReason ORM 모델 구현 in /home/jinkui/law-matcher/backend/models/law_revision_reason.py
- [ ] T006 RevisionDetectionResult ORM 모델 구현 in /home/jinkui/law-matcher/backend/models/revision_detection_result.py
- [ ] T007 Article 모델 확장 필드 추가 in /home/jinkui/law-matcher/backend/models/article.py
- [ ] T008 [P] 신규 모델 export 등록 in /home/jinkui/law-matcher/backend/models/__init__.py
- [ ] T009 제개정이유/판별결과 마이그레이션 추가 in /home/jinkui/law-matcher/backend/alembic/versions/20260228_01_add_law_revision_reasons.py
- [ ] T010 MolegClient 파싱 확장 구현 in /home/jinkui/law-matcher/backend/external/moleg_client.py

---

## Phase 3: User Story 1 - 탭 A 공포일자 기반 판별 (Priority: P1)

**Goal**: 공포일자 판별을 탭A로 독립 제공한다

**Independent Test**: 탭A에서 법령별 개정 필요 여부와 날짜 차이 확인

- [ ] T011 [US1] OrdinanceDetail Tabs 구조 전환 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx
- [ ] T012 [P] [US1] 탭A 컴포넌트 구현 in /home/jinkui/law-matcher/frontend/src/components/detection/TabA_ProclaimedDate.tsx
- [ ] T013 [US1] 탭A API 함수/타입 연동 in /home/jinkui/law-matcher/frontend/src/services/api.ts

---

## Phase 4: User Story 2 - 탭 B 조문 변경 기반 판별 (Priority: P1)

**Goal**: 조문 변경/제개정유형 기반 판별을 제공한다

**Independent Test**: 탭B에서 변경 조문과 매핑 중첩 조문 표시

- [ ] T014 [US2] 조문 동기화 시 신규 메타 저장 로직 반영 in /home/jinkui/law-matcher/backend/services/law_sync_service.py
- [ ] T015 [US2] 조문 응답 스키마/직렬화 반영 in /home/jinkui/law-matcher/backend/schemas/article.py
- [ ] T016 [P] [US2] 탭B 컴포넌트 구현 in /home/jinkui/law-matcher/frontend/src/components/detection/TabB_ArticleChange.tsx
- [ ] T017 [US2] 탭B API 함수/연동 반영 in /home/jinkui/law-matcher/frontend/src/services/api.ts

---

## Phase 5: User Story 3 - 탭 C 제개정이유 기반 판별 (Priority: P1)

**Goal**: 제개정이유/개정문 분석 기반 판별을 제공한다

**Independent Test**: 탭C에서 제개정이유 전문과 추출 조문 표시

- [ ] T018 [US3] 조문번호 추출 파서 구현 in /home/jinkui/law-matcher/backend/services/amendment_parser.py
- [ ] T019 [US3] 제개정이유 캐시 조회/갱신 로직 구현 in /home/jinkui/law-matcher/backend/services/revision_detection_service.py
- [ ] T020 [US3] revision-reason API 엔드포인트 구현 in /home/jinkui/law-matcher/backend/api/v1/laws.py
- [ ] T021 [P] [US3] 탭C 컴포넌트 및 연동 구현 in /home/jinkui/law-matcher/frontend/src/components/detection/TabC_RevisionReason.tsx

---

## Phase 6: User Story 4 - 탭 비교 및 최종 선택 (Priority: P2)

**Goal**: 관리자 비교 화면에서 3탭 결과를 확인한다

**Independent Test**: 비교 페이지에서 tab_a/tab_b/tab_c 결과 동시 조회

- [ ] T022 [US4] detection-results API/집계 로직 구현 in /home/jinkui/law-matcher/backend/api/v1/ordinances.py
- [ ] T023 [P] [US4] 비교 페이지 UI 구현 in /home/jinkui/law-matcher/frontend/src/pages/DetectionCompare.tsx
- [ ] T024 [US4] 관리자 메뉴/라우트 연결 in /home/jinkui/law-matcher/frontend/src/components/layout/MainLayout.tsx

---

## Phase 7: User Story 5 - 제개정이유 기반 자동 발송 기능 (Priority: P2)

**Goal**: detect 실행 후 판별결과 저장과 검토대상 생성을 수행한다

**Independent Test**: detect 실행 시 결과 저장과 대상 생성 확인

- [ ] T025 [US5] detect API 엔드포인트 구현 in /home/jinkui/law-matcher/backend/api/v1/ordinances.py
- [ ] T026 [US5] A/B/C 판별 실행 및 결과 저장 로직 구현 in /home/jinkui/law-matcher/backend/services/revision_detection_service.py

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 전 스토리 공통 품질 보강

- [ ] T027 [P] 판별 요약 배지 컴포넌트 구현 in /home/jinkui/law-matcher/frontend/src/components/detection/DetectionSummary.tsx
- [ ] T028 탭C 장애 폴백/문서 정리 in /home/jinkui/law-matcher/docs/revision-detection-tabs.md

---

## Dependencies & Execution Order

- Setup → Foundational 완료 후 US1~US5 진행
- P1(US1~US3) 완료 후 P2(US4~US5)
- Polish는 전체 완료 후 진행

## Parallel Opportunities

- T003, T004, T008
- T012, T016, T021, T023
- T027

## Implementation Strategy

1. MVP: US1
2. 확장: US2 + US3
3. 운영: US4 + US5
4. 마무리: Polish
