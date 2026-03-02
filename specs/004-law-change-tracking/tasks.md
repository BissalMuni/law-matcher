# Tasks: 개정법령 변경이력 관리

**Input**: Design documents from `/specs/004-law-change-tracking/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api-contracts.md

## Phase 1: Setup & Migration

**Purpose**: DB 스키마 변경 및 마이그레이션

- [ ] T001 [US3] Alembic 마이그레이션 — ordinances 테이블에 revision_status (VARCHAR 20, nullable, default null) 추가, needs_revision→revision_status 데이터 이관 (needs_revision=true → "검토대기"), needs_revision 컬럼 제거 (`backend/alembic/versions/YYYYMMDD_add_revision_status.py`)
- [ ] T002 [P] [US1] Alembic 마이그레이션 — law_changes 테이블에서 status, processed_at, processed_by, process_note, updated_at 컬럼 제거. UNIQUE(law_id, sync_batch_id) 제약 추가 (`backend/alembic/versions/YYYYMMDD_simplify_law_changes.py`)
- [ ] T003 [P] [US5] Alembic 마이그레이션 — ordinance_reviews.review_result 기존 "검토중" 값을 "개정필요"로 변환. 향후 "개정필요"/"개정불필요" 2가지만 허용 (`backend/alembic/versions/YYYYMMDD_constrain_review_result.py`)

---

## Phase 2: Foundational — Model & Schema

**Purpose**: 모든 US에 필요한 모델/스키마 변경. 이 Phase 완료 후 US별 서비스/API 구현 가능

**⚠️ CRITICAL**: Phase 2 완료 전까지 서비스 레이어 작업 불가

- [ ] T004 [US1] law_change 모델 단순화 — ChangeStatus enum 제거, 승인/반려 관련 필드(status, processed_at, processed_by, process_note, updated_at) 제거, sync_batch_id 추가, 감지 로그 전용으로 정리 (`backend/models/law_change.py`)
- [ ] T005 [P] [US3] ordinance 모델 revision_status 도입 — needs_revision(Boolean) → revision_status(nullable VARCHAR) 전환. 허용 값: null/"검토대기"/"검토중"/"개정확정". 빨간불 판별 property 추가 (`backend/models/ordinance.py`)
- [ ] T006 [P] [US5] ordinance_review 모델 review_result 제한 — review_result 값을 "개정필요"/"개정불필요" 2가지만 허용, 기존 다른 값 관련 enum/상수 정리 (`backend/models/ordinance_review.py`)
- [ ] T007 [P] [US1] law_change 스키마 단순화 — 승인/반려 관련 필드 제거, 목록/상세 응답 스키마 정리, sync_batch_id 포함 (`backend/schemas/ordinance.py` 내 LawChange 관련)
- [ ] T008 [P] [US3] ordinance 스키마 업데이트 — needs_revision → revision_status 필드 전환, 응답에 revision_status 포함 (`backend/schemas/ordinance.py`)
- [ ] T009 [P] [US5] review 스키마 업데이트 — review_result를 "개정필요"/"개정불필요" 2가지로 정리, 승인/반려 응답에 ordinance_revision_status 포함 (`backend/schemas/review.py`)
- [ ] T010 [P] [US1] 프론트엔드 타입 정의 업데이트 — Ordinance 타입에 revision_status 추가 (null|"검토대기"|"검토중"|"개정확정"), needs_revision 제거, LawChange 타입에서 승인/반려 상태 필드 제거, ReviewResult 타입을 2가지로 제한 (`frontend/src/types/api.ts`)

**Checkpoint**: 모델/스키마 변경 완료 — 서비스 레이어 구현 시작 가능

---

## Phase 3: US1+US2 — 법령 변경사항 조회 (P1) 🎯 MVP

**Goal**: 관리자가 동기화 후 감지된 법령 변경 기록을 목록/상세로 조회, 필터링/검색 가능

**Independent Test**: 변경 기록 존재 상태에서 목록 접근 → 필터링/검색 → 상세 조회 정상 동작

- [ ] T011 [US1] law_changes API 정리 — approve/reject/bulk 엔드포인트 제거, 목록 조회(필터링/페이지네이션/검색) 유지, 상세 조회 유지 (`backend/api/v1/law_changes.py`)
- [ ] T012 [P] [US1] 프론트엔드 API 호출 함수 — law_changes 관련 approve/reject 함수 제거 (`frontend/src/services/api.ts`)
- [ ] T013 [US1] LawChangeList 페이지 수정 — 승인/반려 UI 완전 제거, 법령명/변경유형/감지일시 등 조회용 컬럼만 유지, 필터(API상태/소관부처/동기화일자/개정유형) 유지 (`frontend/src/pages/LawChangeList.tsx`)

**Checkpoint**: 변경사항 목록/상세 조회 및 필터링 동작 확인

---

## Phase 4: US3 — 검토대상 조례 자동 플래깅 (P1)

**Goal**: 동기화 후 검토대상 조례에 자동으로 빨간불(revision_status="검토대기") 부여

**Independent Test**: 동기화 실행 → 연계 조례에 빨간불 표시, 비연계 조례는 무변경

- [ ] T014 [US3] 동기화 후 자동 플래깅 서비스 — 법령 변경 감지 시 ordinance_law_mappings로 관련 조례 조회, revision_status가 null인 조례만 "검토대기"로 설정, 이미 "검토중"/"개정확정" 상태는 덮어쓰지 않음 (`backend/services/law_sync_service.py`)

**Checkpoint**: 동기화 후 관련 조례에 revision_status="검토대기" 정확 부여

---

## Phase 5: US4 — 부서 담당자 검토 시작 및 의견 작성 (P1)

**Goal**: 부서 담당자가 빨간불 조례에서 "검토 시작" 클릭 → "검토중" 전환 → 검토의견 작성

**Independent Test**: "검토대기" 조례 → "검토 시작" 클릭 → "검토중" → 검토의견(개정필요/불필요) 작성 확인

- [ ] T015 [US4] ordinance_service revision_status 전환 로직 — "검토 시작": revision_status "검토대기"→"검토중" (FR-010, 명시적 버튼 클릭), 부서 담당자 본인 소관 조례만 접근 가능 (FR-017), 상태 전환 유효성 검증 (`backend/services/ordinance_service.py`)
- [ ] T016 [US4] "검토 시작" API 엔드포인트 — POST /api/v1/ordinances/{id}/start-review, revision_status="검토대기"일 때만 "검토중"으로 전환 허용, 부서 권한 체크 (`backend/api/v1/ordinances.py`)
- [ ] T017 [P] [US4] 프론트엔드 API 함수 추가 — startReview(id) 함수 추가 (POST /ordinances/{id}/start-review), clearRevisionStatus(id) 함수 추가 (`frontend/src/services/api.ts`)
- [ ] T018 [US4] OrdinanceDetail 페이지 수정 — "검토 시작" 버튼 (revision_status="검토대기"일 때만 표시), 클릭 시 startReview API 호출→"검토중" 전환, revision_status 상태 배지 표시, 빨간불 표시(revision_status≠null), review_result를 "개정필요"/"개정불필요" 2가지만 선택 가능, "검토중"일 때만 검토의견 작성 가능 (`frontend/src/pages/OrdinanceDetail.tsx`)

**Checkpoint**: 담당자가 "검토 시작"→"검토중"→검토의견 작성 플로우 동작

---

## Phase 6: US5 — 관리자 검토의견 승인/반려 (P1)

**Goal**: 관리자가 검토의견을 승인/반려하면 조례 상태가 자동 처리됨

**Independent Test**: 개정필요 승인→개정확정, 개정불필요 승인→null, 반려→검토대기

- [ ] T019 [US5] review_service 승인/반려 후 자동 상태 처리 — 개정필요+승인→revision_status="개정확정" (FR-012), 개정불필요+승인→revision_status=null (FR-013), 반려→revision_status="검토대기" (FR-014), 관리자만 승인/반려 가능 (FR-016) (`backend/services/review_service.py`)
- [ ] T020 [US5] 관리자 "개정확정" 수동 해제 — revision_status "개정확정"→null (FR-015), 관리자 전용 (`backend/services/ordinance_service.py`)
- [ ] T021 [US5] reviews API 승인/반려 업데이트 — 승인 시 review_service 통해 ordinance.revision_status 자동 처리, 관리자 권한 체크, 응답에 변경된 ordinance 상태 포함, 건별 처리 (`backend/api/v1/reviews.py`)
- [ ] T022 [US5] clear-revision API 엔드포인트 — POST /api/v1/ordinances/{id}/clear-revision, 관리자 전용, "개정확정" 상태만 해제 가능 (`backend/api/v1/ordinances.py`)
- [ ] T023 [US5] ReviewList 페이지 수정 — 승인/반려 UI 건별 처리, 승인 시 결과 미리보기(개정필요→"개정확정 처리됩니다", 개정불필요→"정상 상태로 전환됩니다"), 반려 시 "검토대기로 되돌립니다" 안내, 관리자만 승인/반려 버튼 표시 (`frontend/src/pages/ReviewList.tsx`)

**Checkpoint**: 승인/반려 후 조례 상태 자동 처리 100% 정확

---

## Phase 7: US6 — Excel 내보내기 (P2)

**Goal**: 필터 조건에 맞는 법령 변경 기록을 Excel로 내보내기

**Independent Test**: 필터 적용 → 내보내기 → Excel 내용이 화면 목록과 일치

- [ ] T024 [US6] 엑셀 내보내기 서비스 — 필터 조건 반영 쿼리, 대량 데이터 스트리밍 처리, 법령명/변경항목/전후값/소관부처/동기화일자 컬럼 포함 (`backend/services/law_sync_service.py`)
- [ ] T025 [US6] 엑셀 내보내기 API 및 프론트 — GET /api/v1/law-changes/export 엔드포인트, LawChangeList에 "엑셀 다운로드" 버튼 추가 (`backend/api/v1/law_changes.py`, `frontend/src/pages/LawChangeList.tsx`)

**Checkpoint**: 필터 적용 상태에서 Excel 다운로드, 내용 일치 확인

---

## Phase 8: US7 — 변경이력 통계 (P2)

**Goal**: 소관부처별/API상태별 변경 통계 조회

**Independent Test**: 통계 화면에서 부처별 집계가 실제 데이터와 일치

- [ ] T026 [US7] 통계 집계 서비스 — 부처별/API상태별 변경 건수 집계, 기간 필터 지원 (`backend/services/law_sync_service.py`)
- [ ] T027 [US7] 통계 API 및 프론트 카드 — GET /api/v1/law-changes/stats 엔드포인트, LawChangeList 상단에 Ant Design Statistic 카드 표시 (`backend/api/v1/law_changes.py`, `frontend/src/pages/LawChangeList.tsx`)

**Checkpoint**: 통계 카드에 정확한 집계 수치 표시

---

## Phase 9: US8 — 법령별 변경 이력 추적 (P3)

**Goal**: 특정 법령의 전체 변경 이력을 시간순으로 조회

**Independent Test**: 특정 법령 선택 → 모든 변경 기록 시간순 표시

- [ ] T028 [US8] 법령별 이력 조회 API — GET /api/v1/law-changes/history/{law_id} (시간순, 페이지네이션), GET /api/v1/law-changes/history-summary (법령별 총 변경 횟수+최근 변경일) (`backend/api/v1/law_changes.py`)
- [ ] T029 [US8] 법령별 이력 필터 UI — 법령 선택 드롭다운/검색 필터, 선택 시 해당 법령 이력만 표시, 해제 시 전체 복귀 (`frontend/src/pages/LawChangeList.tsx`)

**Checkpoint**: 법령별 이력 조회 및 필터링 동작

---

## Phase 10: US9 — 동기화 배치/일자 관리 (P3)

**Goal**: 동기화 배치 정보 및 일자 목록으로 특정 시점 결과 조회

**Independent Test**: 배치 목록 → 특정 배치 선택 → 해당 변경 기록만 필터링

- [ ] T030 [US9] 배치/일자 조회 API — GET /api/v1/law-changes/sync-batches (배치 목록+건수), GET /api/v1/law-changes/sync-dates (일자 목록), GET /api/v1/law-changes/departments (부처 목록), GET /api/v1/law-changes/revision-types (제개정구분 목록) (`backend/api/v1/law_changes.py`)
- [ ] T031 [US9] 배치/일자 필터 UI — 동기화 배치/일자 드롭다운, 선택 시 해당 시점 변경 기록만 필터링 (`frontend/src/pages/LawChangeList.tsx`)

**Checkpoint**: 배치/일자 기반 필터링 동작

---

## Phase 11: Polish

**Purpose**: 엣지케이스 처리 및 크로스커팅 관심사

- [ ] T032 [US3] [US4] [US5] 상태 전환 엣지케이스 — 동시 접근 race condition 방지 (optimistic locking/상태 체크), 중복 "검토 시작" 방지, 승인/반려 시 revision_status 유효성 재확인, 자동 플래깅 시 기존 진행 중 검토 무영향 확인 (`backend/services/ordinance_service.py`, `backend/services/review_service.py`)
- [ ] T033 [US4] RoleProtectedRoute 적용 — 관리자 전용 기능(승인/반려/수동해제)에 프론트엔드 역할 기반 접근 제어 적용 (`frontend/src/components/RoleProtectedRoute.tsx`, 관련 페이지)

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Migration):
  T001, T002 [P], T003 [P] — 병렬 실행 가능

Phase 2 (Models & Schemas) — Phase 1 완료 후:
  T001 → T004 (law_change 모델), T005 (ordinance 모델)
  T002 → T004
  T003 → T006
  T004 → T007 [P]
  T005 → T008 [P]
  T006 → T009 [P]
  T010 [P] — 독립 실행 가능 (프론트엔드)

Phase 3 (US1+US2) — T004, T007 완료 후:
  T011, T012 [P] → T013

Phase 4 (US3) — T005, T008 완료 후:
  T014

Phase 5 (US4) — T005, T008 완료 후:
  T015 → T016
  T017 [P] → T018

Phase 6 (US5) — T006, T009, T015 완료 후:
  T019 → T021
  T020 → T022
  T017 → T023

Phase 7-10 (P2/P3):
  T014 → T024 → T025 [P]
  T004 → T026 → T027 [P]
  T011 → T028 → T029 [P]
  T011 → T030 → T031 [P]

Phase 11 (Polish):
  T014 + T015 + T019 → T032
  T023 → T033
```

### Critical Path

```
T001 → T005 → T008 → T015 → T019 → T021 → T023
```

### Parallel Execution Groups

- **Group A** [P]: T001, T002, T003 (마이그레이션 — 독립 테이블)
- **Group B** [P]: T005, T006, T004 (모델 변경 — Phase 1 후 병렬)
- **Group C** [P]: T007, T008, T009, T010 (스키마/타입 — 각 모델 후 병렬)
- **Group D** [P]: T011, T012 (US1 API — Phase 2 후 병렬)
- **Group E** [P]: T024-T031 (P2/P3 기능 — 각 의존성 후 독립)

---

## Task Count Summary

| Phase                       | Tasks           | Priority     |
| --------------------------- | --------------- | ------------ |
| Phase 1: Migration          | T001-T003 (3)   | Setup        |
| Phase 2: Models & Schemas   | T004-T010 (7)   | Foundational |
| Phase 3: US1+US2 조회       | T011-T013 (3)   | P1           |
| Phase 4: US3 자동 플래깅    | T014 (1)        | P1           |
| Phase 5: US4 검토 시작/의견 | T015-T018 (4)   | P1           |
| Phase 6: US5 승인/반려      | T019-T023 (5)   | P1           |
| Phase 7: US6 Excel          | T024-T025 (2)   | P2           |
| Phase 8: US7 통계           | T026-T027 (2)   | P2           |
| Phase 9: US8 이력           | T028-T029 (2)   | P3           |
| Phase 10: US9 배치          | T030-T031 (2)   | P3           |
| Phase 11: Polish            | T032-T033 (2)   | Polish       |
| **Total**                   | **33 tasks**    |              |
