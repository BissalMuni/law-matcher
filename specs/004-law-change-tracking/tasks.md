# Tasks: 개정법령 변경이력 관리

**Input**: Design documents from `/specs/004-law-change-tracking/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 변경이력/검토 워크플로우 정비 준비

- [ ] T001 변경이력 API 경계 점검 in /home/jinkui/law-matcher/backend/api/v1/law_changes.py
- [ ] T002 revision_status 전환 영향 파일 점검 in /home/jinkui/law-matcher/backend/models/ordinance.py
- [ ] T003 [P] 변경이력 화면 상태 표시 위치 점검 in /home/jinkui/law-matcher/frontend/src/pages/LawChangeList.tsx

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 감지 로그 단순화와 상태 생명주기 기반 구축

- [ ] T004 law_changes 감지 로그 전용 구조 반영 in /home/jinkui/law-matcher/backend/models/law_change.py
- [ ] T005 [P] ordinances.revision_status 모델/스키마 반영 in /home/jinkui/law-matcher/backend/models/ordinance.py
- [ ] T006 [P] review_result 값 제한 정리 in /home/jinkui/law-matcher/backend/models/ordinance_review.py
- [ ] T007 revision_status 마이그레이션 추가 in /home/jinkui/law-matcher/backend/alembic/versions/20260228_revision_status.py

---

## Phase 3: User Story 1 - 법령 변경사항 목록 조회 및 필터링 (Priority: P1)

**Goal**: 변경사항 목록을 필터와 함께 조회한다

**Independent Test**: 기간/상태 필터 변경 시 목록 갱신

- [ ] T008 [US1] 변경목록 필터 조회 로직 보강 in /home/jinkui/law-matcher/backend/services/law_sync_service.py
- [ ] T009 [US1] 변경목록 API 파라미터 반영 in /home/jinkui/law-matcher/backend/api/v1/law_changes.py

---

## Phase 4: User Story 2 - 변경사항 상세 조회 (Priority: P1)

**Goal**: 상세 화면에서 old/new 변경값을 확인한다

**Independent Test**: 목록 선택 시 상세 비교 정보 표시

- [ ] T010 [US2] 상세 응답 직렬화 보강(old/new) in /home/jinkui/law-matcher/backend/schemas/ordinance.py
- [ ] T011 [US2] 상세 표시 UI 보강 in /home/jinkui/law-matcher/frontend/src/pages/LawChangeList.tsx

---

## Phase 5: User Story 3 - 검토대상 조례 자동 플래깅 (Priority: P1)

**Goal**: 동기화 후 영향 조례를 자동 플래깅한다

**Independent Test**: 변경 감지 후 조례 상태가 자동으로 검토중 전환

- [ ] T012 [US3] 자동 플래깅 로직 추가 in /home/jinkui/law-matcher/backend/services/law_sync_service.py
- [ ] T013 [US3] 상태 전환 서비스 로직 보강 in /home/jinkui/law-matcher/backend/services/ordinance_service.py

---

## Phase 6: User Story 4 - 부서 담당자 조례 검토 및 의견 작성 (Priority: P1)

**Goal**: 담당자가 검토의견을 작성/저장한다

**Independent Test**: 의견 저장 후 검토 상태 및 이력 반영

- [ ] T014 [US4] 검토의견 저장 로직 보강 in /home/jinkui/law-matcher/backend/services/review_service.py
- [ ] T015 [US4] 검토의견 입력 UI 보강 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx

---

## Phase 7: User Story 5 - 관리자 검토의견 승인/반려 (Priority: P1)

**Goal**: 관리자 승인/반려와 상태 후처리를 수행한다

**Independent Test**: 승인/반려 후 review/ordinance 상태가 규칙대로 변경

- [ ] T016 [US5] 승인/반려 처리 로직 정비 in /home/jinkui/law-matcher/backend/services/review_service.py
- [ ] T017 [US5] 승인 후 상태 후처리 로직 보강 in /home/jinkui/law-matcher/backend/services/ordinance_service.py

---

## Phase 8: User Story 6 - Excel 내보내기 (Priority: P2)

**Goal**: 변경이력 데이터를 엑셀로 내보낸다

**Independent Test**: 필터 적용된 엑셀 다운로드 성공

- [ ] T018 [US6] 엑셀 내보내기 쿼리 보강 in /home/jinkui/law-matcher/backend/services/law_sync_service.py
- [ ] T019 [US6] 내보내기 API/버튼 연동 보강 in /home/jinkui/law-matcher/frontend/src/pages/LawChangeList.tsx

---

## Phase 9: User Story 7 - 변경이력 통계 조회 (Priority: P2)

**Goal**: 기간/상태 기준 통계를 조회한다

**Independent Test**: 기간 선택 시 통계 카드 값 갱신

- [ ] T020 [US7] 통계 집계 로직 추가 in /home/jinkui/law-matcher/backend/services/law_sync_service.py
- [ ] T021 [US7] 통계 화면 카드 연동 보강 in /home/jinkui/law-matcher/frontend/src/pages/Statistics.tsx

---

## Phase 10: User Story 8 - 특정 법령의 변경 이력 추적 (Priority: P3)

**Goal**: 법령 단위 이력 조회를 제공한다

**Independent Test**: 법령 선택 시 해당 법령 이력만 표시

- [ ] T022 [US8] 법령별 이력 조회 API 보강 in /home/jinkui/law-matcher/backend/api/v1/law_changes.py
- [ ] T023 [US8] 법령 추적 필터 UI 보강 in /home/jinkui/law-matcher/frontend/src/pages/LawChangeList.tsx

---

## Phase 11: User Story 9 - 동기화 배치 및 일자 관리 (Priority: P3)

**Goal**: 배치 실행/동기화 일자 기록을 관리한다

**Independent Test**: 배치 실행 후 상태와 일자 기록 확인

- [ ] T024 [US9] 배치 실행/기록 로직 보강 in /home/jinkui/law-matcher/backend/services/sync_service.py
- [ ] T025 [US9] 배치 상태 조회 API 보강 in /home/jinkui/law-matcher/backend/api/v1/sync.py

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: 변경이력 기능 전반 품질 정리

- [ ] T026 [P] 상태 전환 로깅/감사 필드 보강 in /home/jinkui/law-matcher/backend/services/ordinance_service.py
- [ ] T027 목록/상세/검토 문구 일관성 정리 in /home/jinkui/law-matcher/frontend/src/pages/ReviewList.tsx
- [ ] T028 변경이력 기능 문서 업데이트 in /home/jinkui/law-matcher/docs/law-change-tracking.md

---

## Dependencies & Execution Order

- Setup → Foundational 완료 후 US1~US9 진행
- P1(US1~US5) 우선 후 P2/P3 진행
- Polish는 전체 완료 후 진행

## Parallel Opportunities

- T003, T005, T006
- T011, T015, T019, T021, T023
- T026

## Implementation Strategy

1. MVP: US1~US5
2. 확장: US6~US7
3. 후순위: US8~US9
4. 마무리: Polish
