# Tasks: 조례 관리 기능

**Input**: Design documents from `/specs/002-ordinance-management/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 조례 관리 보강 작업 준비

- [ ] T001 조례 API/서비스 진입점 점검 in /home/jinkui/law-matcher/backend/api/v1/ordinances.py
- [ ] T002 조례 상태 확장 영향 범위 점검 in /home/jinkui/law-matcher/backend/models/ordinance.py
- [ ] T003 [P] 목록/상세 상태 표현 UI 점검 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceList.tsx

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 상태 생명주기와 공통 응답 기반 정비

- [ ] T004 ABOLISHED 상태 값 반영 in /home/jinkui/law-matcher/backend/models/ordinance.py
- [ ] T005 [P] 조례 스키마 status 필드 정리 in /home/jinkui/law-matcher/backend/schemas/ordinance.py
- [ ] T006 [P] 프론트 status 타입 확장 in /home/jinkui/law-matcher/frontend/src/types/api.ts
- [ ] T007 기존 데이터 상태 전환 마이그레이션 추가 in /home/jinkui/law-matcher/backend/alembic/versions/20260228_add_abolished_status.py

---

## Phase 3: User Story 1 - 조례 목록 조회 (Priority: P1)

**Goal**: 상태 필터 기반 목록 조회를 제공한다

**Independent Test**: status 필터 변경 시 목록 결과가 즉시 반영된다

- [ ] T008 [US1] 목록 조회 기본 status 필터 로직 반영 in /home/jinkui/law-matcher/backend/services/ordinance_service.py
- [ ] T009 [US1] 목록 API status 파라미터 반영 in /home/jinkui/law-matcher/backend/api/v1/ordinances.py
- [ ] T010 [P] [US1] 목록 페이지 status 필터 UI 반영 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceList.tsx

---

## Phase 4: User Story 2 - 조례 등록 (Priority: P1)

**Goal**: 등록 실패 시 한국어 오류를 명확히 안내한다

**Independent Test**: 중복 등록 시 한국어 오류, 정상 등록 시 성공

- [ ] T011 [US2] 등록 검증/중복 오류 메시지 한국어화 in /home/jinkui/law-matcher/backend/services/ordinance_service.py
- [ ] T012 [US2] 등록 API 예외 응답 매핑 보강 in /home/jinkui/law-matcher/backend/api/v1/ordinances.py
- [ ] T013 [P] [US2] 등록 실패 메시지 UI 정리 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceList.tsx

---

## Phase 5: User Story 3 - 법제처 일괄 동기화 (Priority: P1)

**Goal**: 동기화 시 폐지 조례를 감지해 상태를 전환한다

**Independent Test**: 동기화 후 ABOLISHED 전환 및 응답 건수 확인

- [ ] T014 [US3] 동기화 폐지 감지 로직 추가 in /home/jinkui/law-matcher/backend/services/ordinance_service.py
- [ ] T015 [US3] 동기화 응답에 abolished_count 필드 반영 in /home/jinkui/law-matcher/backend/schemas/ordinance.py
- [ ] T016 [US3] 동기화 API 응답 구조 반영 in /home/jinkui/law-matcher/backend/api/v1/ordinances.py
- [ ] T017 [P] [US3] 동기화 결과 폐지 건수 UI 반영 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceList.tsx

---

## Phase 6: User Story 4 - 조례 상세 조회 (Priority: P1)

**Goal**: 상세 화면에서 폐지 상태를 명확하게 노출한다

**Independent Test**: 폐지 조례 상세에 상태 배지 표시

- [ ] T018 [US4] 상세 응답 상태 표현 필드 보강 in /home/jinkui/law-matcher/backend/schemas/ordinance.py
- [ ] T019 [US4] 상세 페이지 폐지 상태 배지 반영 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx

---

## Phase 7: User Story 5 - 부서 일괄 배정 (Priority: P2)

**Goal**: 상태와 충돌 없이 일괄 배정 기능을 유지한다

**Independent Test**: 상태 혼합 조례 선택 시 배정 처리 정상 동작

- [ ] T020 [US5] 배정 로직의 ABOLISHED 처리 규칙 반영 in /home/jinkui/law-matcher/backend/services/ordinance_service.py
- [ ] T021 [P] [US5] 배정 UI 상태 안내 메시지 보강 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceList.tsx

---

## Phase 8: User Story 6 - 조례 목록 엑셀 내보내기 (Priority: P2)

**Goal**: 기본 내보내기에서 폐지 조례를 제외한다

**Independent Test**: 기본 내보내기에서 ABOLISHED 제외, 옵션으로 포함 가능

- [ ] T022 [US6] 엑셀 내보내기 status 기본 필터 반영 in /home/jinkui/law-matcher/backend/services/ordinance_service.py
- [ ] T023 [US6] 엑셀 API status 파라미터 반영 in /home/jinkui/law-matcher/backend/api/v1/ordinances.py
- [ ] T024 [P] [US6] 내보내기 옵션 토글 UI 추가 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceList.tsx

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 조례 관리 기능 전반 품질 정리

- [ ] T025 [P] 상태 문구/뱃지 표현 통일 in /home/jinkui/law-matcher/frontend/src/types/api.ts
- [ ] T026 상태 전환 로깅/예외 문구 보강 in /home/jinkui/law-matcher/backend/services/ordinance_service.py
- [ ] T027 목록/상세 공통 오류 표시 정리 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx
- [ ] T028 조례 관리 문서 업데이트 in /home/jinkui/law-matcher/docs/ordinance-management.md

---

## Dependencies & Execution Order

- Setup → Foundational 완료 후 US1~US6 진행
- P1(US1~US4) 우선 후 P2(US5~US6)
- Polish는 전체 완료 후 진행

## Parallel Opportunities

- T003, T005, T006
- T010, T013, T017
- T021, T024
- T025

## Implementation Strategy

1. MVP: US1~US4
2. 확장: US5~US6
3. 마무리: Polish
