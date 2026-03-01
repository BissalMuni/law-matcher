# 004-law-change-tracking Tasks

## Phase 1: Setup & Configuration

### T001: Alembic 마이그레이션 준비 [US3]
- **File**: `backend/alembic/versions/YYYYMMDD_revision_status.py` (신규)
- **Work**:
  - `ordinances` 테이블에 `revision_status` 컬럼 추가 (nullable VARCHAR, default null)
  - 기존 `needs_revision` 컬럼 데이터를 `revision_status`로 마이그레이션 (needs_revision=true → revision_status="검토대기")
  - `needs_revision` 컬럼 제거
  - `law_changes` 테이블에서 `ChangeStatus` 관련 컬럼 제거 (승인/반려 상태)
  - `ordinance_reviews` 테이블의 `review_result` 제약 조건 업데이트 (2가지 값만 허용)
  - downgrade 함수 작성
- **Dependencies**: None

---

## Phase 2: Foundational - Model & Schema Changes

### T002: law_change 모델 단순화 [US1] [US2]
- **File**: `backend/models/law_change.py` (수정)
- **Work**:
  - `ChangeStatus` enum 제거 (승인/반려 상태 불필요)
  - 감지 로그 전용으로 모델 단순화
  - 승인/반려 관련 필드 제거
  - 변경 감지 일시, 법령 정보, 변경 유형 등 핵심 필드만 유지
- **Dependencies**: T001

### T003: ordinance 모델 revision_status 도입 [US3] [P]
- **File**: `backend/models/ordinance.py` (수정)
- **Work**:
  - `needs_revision` (Boolean) → `revision_status` (nullable String) 전환
  - revision_status 허용 값: null, "검토대기", "검토중", "개정확정"
  - revision_status 생명주기: null → "검토대기" → "검토중" → "개정확정"/null/"검토대기"
  - 빨간불 판별 프로퍼티: revision_status가 null이 아니면 빨간불 ON (단, "개정불필요" 승인 시 null로 해제)
- **Dependencies**: T001

### T004: ordinance_review 모델 review_result 제한 [US4] [P]
- **File**: `backend/models/ordinance_review.py` (수정)
- **Work**:
  - `review_result` 값을 2가지로 제한: "개정필요", "개정불필요"
  - 기존 다른 값들 제거
  - 관련 enum/상수 정리
- **Dependencies**: T001

### T005: ordinance 스키마 업데이트 [US1] [US3] [P]
- **File**: `backend/schemas/ordinance.py` (수정)
- **Work**:
  - `needs_revision` → `revision_status` 필드 전환
  - revision_status 응답에 포함 (null | "검토대기" | "검토중" | "개정확정")
  - 빨간불 상태 표시를 위한 computed 필드 또는 직접 노출
- **Dependencies**: T003

### T006: review 스키마 업데이트 [US4] [US5] [P]
- **File**: `backend/schemas/review.py` (수정)
- **Work**:
  - `review_result` enum을 "개정필요", "개정불필요" 2가지로 정리
  - 승인/반려 요청/응답 스키마 정리
  - 검토의견 작성 요청 스키마 유지
- **Dependencies**: T004

### T007: API 타입 정의 업데이트 (Frontend) [US1] [US4] [P]
- **File**: `frontend/src/types/api.ts` (수정)
- **Work**:
  - `Ordinance` 타입에 `revision_status` 추가 (null | "검토대기" | "검토중" | "개정확정")
  - `needs_revision` 제거
  - `LawChange` 타입에서 승인/반려 상태 필드 제거
  - `ReviewResult` 타입을 "개정필요" | "개정불필요"로 제한
- **Dependencies**: None

---

## Phase 3: Service Layer - Core Business Logic

### T008: 동기화 후 자동 플래깅 로직 [US3]
- **File**: `backend/services/law_sync_service.py` (수정)
- **Work**:
  - 법제처 API 동기화 완료 후 검토대상 조례 자동 판별 로직 추가
  - 상위법 변경 감지 시 관련 조례의 `revision_status`를 "검토대기"로 설정 (FR-009)
  - 이미 "검토중" 또는 "개정확정" 상태인 조례는 덮어쓰지 않음
  - null 상태인 조례만 "검토대기"로 전환
- **Dependencies**: T002, T003

### T009: ordinance_service revision_status 전환 로직 [US4] [US5]
- **File**: `backend/services/ordinance_service.py` (수정)
- **Work**:
  - "검토 시작" 기능: revision_status를 "검토대기" → "검토중"으로 전환 (FR-010)
  - 열람만으로는 자동 전환하지 않음 (명시적 버튼 클릭 필요)
  - 관리자의 "개정확정" 수동 해제 기능: revision_status → null (FR-015)
  - 부서 담당자는 본인 부서 소관 조례만 접근 가능 (FR-017)
  - 상태 전환 유효성 검증 (올바른 생명주기 순서 확인)
- **Dependencies**: T003, T005

### T010: review_service 승인 후 자동 상태 처리 [US5]
- **File**: `backend/services/review_service.py` (수정)
- **Work**:
  - 승인 시 review_result에 따른 자동 상태 처리:
    - 개정필요 + 승인 → ordinance.revision_status = "개정확정" (FR-012)
    - 개정불필요 + 승인 → ordinance.revision_status = null (빨간불 해제) (FR-013)
  - 반려 시 → ordinance.revision_status = "검토대기" (FR-014)
  - 관리자만 승인/반려 가능하도록 권한 체크 (FR-016)
  - 건별 승인/반려만 구현 (일괄 처리는 추후)
- **Dependencies**: T004, T006, T009

---

## Phase 4: API Endpoints

### T011: law_changes API 정리 [US1] [US2]
- **File**: `backend/api/v1/law_changes.py` (수정)
- **Work**:
  - approve/reject 엔드포인트 제거 (law_changes는 감지 로그 전용)
  - 목록 조회 엔드포인트 유지 (필터링/페이지네이션)
  - 상세 조회 엔드포인트 유지
  - 불필요한 상태 변경 API 모두 제거
- **Dependencies**: T002

### T012: ordinances API "검토 시작" 엔드포인트 추가 [US4]
- **File**: `backend/api/v1/ordinances.py` (수정)
- **Work**:
  - `POST /api/v1/ordinances/{id}/start-review` 엔드포인트 신규 추가
  - revision_status가 "검토대기"인 경우만 "검토중"으로 전환 허용
  - 부서 담당자 본인 소관 조례만 가능 (FR-017)
  - 관리자의 "개정확정" 수동 해제 API 추가 (FR-015)
  - 조례 목록/상세 조회에 revision_status 포함
- **Dependencies**: T005, T009

### T013: reviews API 승인/반려 로직 업데이트 [US5]
- **File**: `backend/api/v1/reviews.py` (수정)
- **Work**:
  - 승인/반려 시 review_service를 통해 ordinance.revision_status 자동 처리
  - 관리자 권한 체크 (FR-016)
  - 응답에 변경된 ordinance 상태 포함
  - 건별 승인/반려 엔드포인트 유지
- **Dependencies**: T006, T010

---

## Phase 5: Frontend - API Service & Pages

### T014: API 호출 함수 업데이트 [US1] [US4] [US5]
- **File**: `frontend/src/services/api.ts` (수정)
- **Work**:
  - law_changes 관련: approve/reject API 호출 제거
  - ordinances 관련: `startReview(id)` 함수 추가 (POST /ordinances/{id}/start-review)
  - ordinances 관련: `clearRevisionStatus(id)` 함수 추가 (관리자 수동 해제)
  - reviews 관련: 승인/반려 API 호출 함수 유지 및 응답 타입 업데이트
- **Dependencies**: T007

### T015: LawChangeList 페이지 수정 [US1]
- **File**: `frontend/src/pages/LawChangeList.tsx` (수정)
- **Work**:
  - 승인/반려 UI 완전 제거 (law_changes는 감지 로그 전용)
  - 변경사항 목록 조회 및 필터링 UI 유지
  - revision_status 대신 law_change 고유 정보만 표시
  - 법령명, 변경유형, 감지일시 등 조회용 컬럼만 유지
- **Dependencies**: T014

### T016: OrdinanceDetail 페이지 수정 [US4] [US3]
- **File**: `frontend/src/pages/OrdinanceDetail.tsx` (수정)
- **Work**:
  - "검토 시작" 버튼 추가 (revision_status = "검토대기"일 때만 표시)
  - 버튼 클릭 시 startReview API 호출 → "검토중" 전환
  - revision_status 상태 배지 표시 (검토대기/검토중/개정확정)
  - 빨간불 표시 (revision_status가 null이 아닌 경우)
  - 검토의견 작성 UI: review_result를 "개정필요"/"개정불필요" 2가지만 선택 가능
  - revision_status가 "검토중"일 때만 검토의견 작성 가능
- **Dependencies**: T014

### T017: ReviewList 페이지 수정 [US5]
- **File**: `frontend/src/pages/ReviewList.tsx` (수정)
- **Work**:
  - 승인/반려 UI 업데이트 (건별 처리)
  - 승인 시 review_result에 따른 결과 미리보기 표시
    - 개정필요 → "승인 시 개정확정 처리됩니다"
    - 개정불필요 → "승인 시 정상 상태로 전환됩니다"
  - 반려 시 "검토대기 상태로 되돌립니다" 안내
  - 관리자만 승인/반려 버튼 표시
  - 처리 후 ordinance revision_status 변경 결과 반영
- **Dependencies**: T014

---

## Phase 6: Polish & Integration

### T018: 상태 전환 엣지케이스 처리 [US3] [US4] [US5]
- **File**: `backend/services/ordinance_service.py`, `backend/services/review_service.py` (수정)
- **Work**:
  - 동시 접근 시 race condition 방지 (optimistic locking 또는 상태 체크)
  - 이미 "검토중"인 조례에 대한 중복 "검토 시작" 방지
  - 승인/반려 시 현재 revision_status 유효성 재확인
  - 자동 플래깅 시 기존 진행 중 검토에 영향 없음 확인
- **Dependencies**: T008, T009, T010

---

## Dependencies & Execution Order

```
Phase 1 (Setup):
  T001 (마이그레이션)

Phase 2 (Models & Schemas) - 병렬 가능:
  T001 → T002 (law_change 모델)
  T001 → T003 (ordinance 모델) [P]
  T001 → T004 (review 모델) [P]
  T003 → T005 (ordinance 스키마) [P]
  T004 → T006 (review 스키마) [P]
  T007 (frontend 타입) [P] - 독립 실행 가능

Phase 3 (Services):
  T002 + T003 → T008 (동기화 자동 플래깅)
  T003 + T005 → T009 (ordinance 상태 전환)
  T004 + T006 + T009 → T010 (승인 후 자동 처리)

Phase 4 (APIs):
  T002 → T011 (law_changes API) [P]
  T005 + T009 → T012 (ordinances API) [P]
  T006 + T010 → T013 (reviews API)

Phase 5 (Frontend) - T007 + Phase 4 완료 후:
  T014 (API 함수) → T015 (LawChangeList) [P]
  T014 → T016 (OrdinanceDetail) [P]
  T014 → T017 (ReviewList) [P]

Phase 6 (Polish):
  T008 + T009 + T010 → T018 (엣지케이스)
```

### Critical Path
```
T001 → T003 → T005 → T009 → T010 → T013 → T014 → T016
```

### Parallel Execution Groups
- **Group A** [P]: T002, T003, T004 (모델 변경 - T001 완료 후 병렬)
- **Group B** [P]: T005, T006, T007 (스키마/타입 - 각 모델 완료 후 병렬)
- **Group C** [P]: T011, T012 (API - 각 서비스 완료 후 병렬)
- **Group D** [P]: T015, T016, T017 (프론트엔드 페이지 - T014 완료 후 병렬)

### Task Count Summary
- Total: 18 tasks
- Phase 1 (Setup): 1 task
- Phase 2 (Models & Schemas): 6 tasks
- Phase 3 (Services): 3 tasks
- Phase 4 (APIs): 3 tasks
- Phase 5 (Frontend): 4 tasks
- Phase 6 (Polish): 1 task
