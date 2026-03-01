# 002-ordinance-management Tasks

## Dependencies & Execution Order

```
T001 (Backend Model) ──┐
                        ├──> T003 (Backend Schema) ──> T005 (Backend Service) ──> T006 (Backend API)
T002 (DB Migration) ───┘                                       │
                                                                v
                                                  T007 (Frontend Types) ──> T008 (Frontend API)
                                                                                    │
                                                              ┌─────────────────────┤
                                                              v                     v
                                                  T009 (OrdinanceList)    T010 (OrdinanceDetail)
                                                              │                     │
                                                              └──────────┬──────────┘
                                                                         v
                                                              T011 (Error Messages)
```

**Parallel groups:**
- T001, T002 can run in parallel [P]
- T009, T010 can run in parallel [P]

---

## Phase 1: Foundational (Backend Model & Migration)

### T001 — Backend: ABOLISHED 상태 추가 [US1][US3][US4]
- **File**: `backend/models/ordinance.py`
- **Work**:
  - 조례 status enum/값에 `ABOLISHED` (폐지) 추가
  - 기존 status 값(ACTIVE 등)과 공존하도록 정의
- **Accept**:
  - `ABOLISHED` 상태가 모델에 정의되어 있음
  - 기존 status 값이 유지됨

### T002 — DB Migration: 폐지 상태 마이그레이션 [US3] [P]
- **File**: `backend/alembic/versions/YYYYMMDD_add_abolished_status.py` (신규)
- **Work**:
  - Alembic 마이그레이션 파일 생성
  - status 컬럼에 ABOLISHED 값 허용하도록 변경
  - 기존 폐지 조례 데이터가 있다면 status를 ABOLISHED로 갱신
- **Accept**:
  - 마이그레이션이 정상 실행됨
  - rollback(downgrade)이 가능함
- **Deps**: 없음 (T001과 병렬 가능)

---

## Phase 2: Backend Schema & Service

### T003 — Backend Schema: status 필터 및 동기화 응답 확장 [US1][US3]
- **File**: `backend/schemas/ordinance.py`
- **Work**:
  - 목록 조회 요청에 `status` 필터 파라미터 추가 (optional, 기본값: ACTIVE 조례만)
  - 동기화 응답 스키마에 `abolished` 건수 필드 추가
  - status enum 타입을 스키마에 반영
- **Accept**:
  - status 필터 파라미터가 스키마에 정의됨
  - 동기화 응답에 `abolished` 건수가 포함됨
- **Deps**: T001

### T004 — (Reserved)

### T005 — Backend Service: 폐지 감지 및 status 필터 [US1][US3][US6]
- **File**: `backend/services/ordinance_service.py`
- **Work**:
  - **동기화 로직 (US3)**: 법제처 API 응답과 기존 DB 비교하여 폐지된 조례 감지
    - 법제처 응답에 없는 기존 조례를 `ABOLISHED` 상태로 소프트 삭제 (is_active=False, status=ABOLISHED)
    - FR-004: 하드 삭제 금지, is_active 필드로 소프트 삭제
    - FR-005: code(자치법규ID) 기준 신규/갱신 판별
    - 동기화 결과에 abolished 건수 포함
  - **목록 조회 (US1)**: status 필터 적용, 기본값은 ACTIVE 조례만 반환
  - **엑셀 내보내기 (US6)**: 폐지 조례 기본 제외
- **Accept**:
  - 동기화 시 폐지 조례가 ABOLISHED 상태로 변경됨
  - 하드 삭제가 발생하지 않음
  - 목록 조회 시 status 필터가 동작함
  - 엑셀 내보내기 시 폐지 조례가 기본 제외됨
- **Deps**: T001, T003

---

## Phase 3: Backend API

### T006 — Backend API: status 필터 파라미터 및 에러 메시지 한국어화 [US1][US2][US3]
- **File**: `backend/api/v1/ordinances.py`
- **Work**:
  - 목록 조회 엔드포인트에 `status` 쿼리 파라미터 추가
  - 에러 메시지 한국어화:
    - 중복 조례 등록: `"이미 등록된 조례입니다 (코드: {code})"`
    - API 타임아웃: `"법제처 서버 응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요"`
    - 동기화 실패: `"동기화 중 {n}건의 오류가 발생했습니다"`
  - FR-006: code 중복 검사 시 한국어 에러 반환
- **Accept**:
  - status 필터가 API에서 동작함
  - 에러 응답이 한국어로 반환됨
  - 중복 code 등록 시 적절한 에러 메시지 반환
- **Deps**: T005

---

## Phase 4: Frontend

### T007 — Frontend Types: status 타입 추가 [US1][US4]
- **File**: `frontend/src/types/api.ts`
- **Work**:
  - 조례 status 타입에 `ABOLISHED` 추가
  - 동기화 응답 타입에 `abolished` 건수 필드 추가
- **Accept**:
  - TypeScript 타입이 백엔드 스키마와 일치함
- **Deps**: T003

### T008 — Frontend API: status 파라미터 추가 [US1]
- **File**: `frontend/src/services/api.ts`
- **Work**:
  - 조례 목록 조회 API 호출에 `status` 파라미터 추가
- **Accept**:
  - API 호출 시 status 필터가 전달됨
- **Deps**: T007

### T009 — Frontend: 조례 목록 status 필터 UI [US1] [P]
- **File**: `frontend/src/pages/OrdinanceList.tsx`
- **Work**:
  - status 필터 드롭다운/셀렉트 추가 (전체, 시행중, 폐지)
  - 기본값: 시행중(ACTIVE) 조례만 표시
  - 필터 변경 시 API 재호출
- **Accept**:
  - status 필터 UI가 표시됨
  - 필터 선택에 따라 목록이 갱신됨
- **Deps**: T008

### T010 — Frontend: 조례 상세 폐지 상태 배지 [US4] [P]
- **File**: `frontend/src/pages/OrdinanceDetail.tsx`
- **Work**:
  - 폐지된 조례인 경우 상태 배지(Badge) 표시
  - 배지 스타일: 시각적으로 구분 가능하도록 (예: 빨간색 태그)
- **Accept**:
  - 폐지 조례 상세 페이지에 폐지 배지가 표시됨
  - 시행중 조례에는 폐지 배지가 표시되지 않음
- **Deps**: T008

---

## Phase 5: US5 부서 배정 ABOLISHED 처리 (P2)

### T012 — Backend: 부서 배정 시 ABOLISHED 상태 처리 [US5]
- **File**: `backend/services/ordinance_service.py`
- **Work**:
  - 부서 일괄 배정 로직에서 ABOLISHED 상태 조례 처리 규칙 추가
  - ABOLISHED 조례 선택 시 배정 차단 또는 경고 반환
  - 배정 대상에서 ABOLISHED 조례 자동 제외 옵션
- **Accept**:
  - ABOLISHED 조례에 부서 배정 시 적절한 에러/경고 반환
  - ACTIVE 조례만 정상 배정됨
- **Deps**: T005

### T013 — Frontend: 부서 배정 UI 상태 안내 [US5] [P]
- **File**: `frontend/src/pages/OrdinanceList.tsx`
- **Work**:
  - 일괄 배정 선택 시 ABOLISHED 조례가 포함된 경우 경고 메시지 표시
  - "폐지된 조례 N건은 배정에서 제외됩니다" 안내
  - ABOLISHED 조례는 체크박스 비활성화 또는 시각적 구분
- **Accept**:
  - 사용자가 ABOLISHED 조례의 배정 불가를 명확히 인지
- **Deps**: T012

---

## Phase 6: Polish

### T014 — 에러 메시지 및 UX 일관성 점검 [US2][US3]
- **Files**:
  - `backend/api/v1/ordinances.py`
  - `frontend/src/pages/OrdinanceList.tsx`
- **Work**:
  - 모든 에러 경로에서 한국어 메시지가 반환되는지 확인
  - 동기화 결과 화면에 abolished 건수 표시 확인
  - 전체 흐름 점검: 동기화 -> 폐지 감지 -> 목록 필터 -> 상세 배지
- **Accept**:
  - 에러 메시지가 전부 한국어로 표시됨
  - 동기화 결과에 폐지 건수가 표시됨
- **Deps**: T006, T009, T010

---

## Summary

| Task | Description | Phase | Deps |
|------|------------|-------|------|
| T001 | Backend: ABOLISHED 상태 추가 | 1. Foundational | - |
| T002 | DB Migration: 폐지 상태 마이그레이션 | 1. Foundational | - |
| T003 | Backend Schema: status 필터 및 동기화 응답 확장 | 2. Schema & Service | T001 |
| T005 | Backend Service: 폐지 감지 및 status 필터 | 2. Schema & Service | T001, T003 |
| T006 | Backend API: status 필터 및 에러 메시지 한국어화 | 3. Backend API | T005 |
| T007 | Frontend Types: status 타입 추가 | 4. Frontend | T003 |
| T008 | Frontend API: status 파라미터 추가 | 4. Frontend | T007 |
| T009 | Frontend: 조례 목록 status 필터 UI | 4. Frontend | T008 |
| T010 | Frontend: 조례 상세 폐지 상태 배지 | 4. Frontend | T008 |
| T011 | 에러 메시지 및 UX 일관성 점검 | 5. US5 부서 배정 | T005 |
| T012 | Backend: 부서 배정 ABOLISHED 처리 | 5. US5 부서 배정 | T005 |
| T013 | Frontend: 부서 배정 UI 상태 안내 | 5. US5 부서 배정 | T012 |
| T014 | 에러 메시지 및 UX 일관성 점검 | 6. Polish | T006, T009, T010, T013 |
