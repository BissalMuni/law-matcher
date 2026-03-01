# Tasks: 로그인 기능

**Input**: Design documents from `/specs/001-login/`
**Prerequisites**: plan.md (required), spec.md (required)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

> 기존 프로젝트에 이미 구조가 갖춰져 있으므로 별도 셋업 불필요.

_(no tasks)_

---

## Phase 2: Foundational (Blocking Prerequisites)

> 기존 코드(security, config, models, deps)가 이미 존재하므로 별도 기반 작업 불필요.

_(no tasks)_

---

## Phase 3: US1/US2 에러 처리 보강 (부서 로그인 / 관리자 로그인)

| ID | Par | Story | Description |
|----|-----|-------|-------------|
| T001 | [P] | US1/US2 | `backend/api/v1/auth.py` - 로그인 엔드포인트 에러 처리 보강. 잘못된 자격 증명, 빈 필드, 존재하지 않는 사용자 등에 대해 명확한 HTTP 에러 응답(400/401/422) 반환. 에러 메시지에 민감 정보 노출 방지. |
| T002 | [P] | US1/US2 | `backend/services/auth_service.py` - 인증 서비스 에러 처리 보강. 예외 상황(DB 연결 실패 등)에 대한 적절한 예외 래핑 및 로깅 추가. |
| T003 | [P] | US1/US2 | `frontend/src/pages/Login.tsx` - 로그인 페이지 에러 처리 보강. 네트워크 에러, 서버 에러, 잘못된 자격 증명 등 각 케이스별 사용자 친화적 에러 메시지 표시. |
| T004 | [P] | US1/US2 | `frontend/src/contexts/AuthContext.tsx` - 인증 컨텍스트 에러 처리 보강. 토큰 만료, 리프레시 실패 시 적절한 에러 상태 관리 및 로그아웃 처리. |

---

## Phase 4: US4 비밀번호 변경 - 백엔드

| ID | Par | Story | Description |
|----|-----|-------|-------------|
| T005 | | US4 | `backend/schemas/auth.py` - 비밀번호 변경 요청/응답 스키마 확인. `ChangePasswordRequest` 스키마에 `current_password`, `new_password` 필드가 있는지 확인하고 없으면 추가. 비밀번호 유효성 검증(최소 길이 등) 포함. |
| T006 | | US4 | `backend/api/v1/auth.py` - `PUT /auth/change-password` 엔드포인트 추가. 인증된 사용자(`get_current_user` 의존성)만 접근 가능. 현재 비밀번호 확인 후 새 비밀번호로 변경. 기존 `auth_service.change_password()` 호출. 에러 응답: 현재 비밀번호 불일치(400), 미인증(401). |

> T006은 T005의 스키마에 의존하므로 순차 실행.

---

## Phase 5: US4 비밀번호 변경 - 프론트엔드

| ID | Par | Story | Description |
|----|-----|-------|-------------|
| T007 | [P] | US4 | `frontend/src/services/api.ts` - `changePassword(currentPassword, newPassword)` API 호출 함수 추가. `PUT /auth/change-password` 엔드포인트 호출. 에러 응답 처리 포함. |
| T008 | | US4 | `frontend/src/pages/ChangePassword.tsx` - 비밀번호 변경 페이지 신규 생성. Ant Design Form 사용. 필드: 현재 비밀번호, 새 비밀번호, 새 비밀번호 확인. 클라이언트 사이드 유효성 검증(빈 값, 비밀번호 일치, 최소 길이). 성공 시 알림 표시 후 이전 페이지로 이동. 에러 시(현재 비밀번호 불일치 등) 사용자 친화적 메시지 표시. |
| T009 | | US4 | `frontend/src/App.tsx` - `/change-password` 라우트 추가. `ProtectedRoute`로 감싸서 인증된 사용자만 접근 가능. USER/ADMIN 모두 접근 허용. |
| T010 | | US4 | `frontend/src/components/layout/MainLayout.tsx` - 사용자 메뉴(헤더 드롭다운 등)에 "비밀번호 변경" 메뉴 항목 추가. 클릭 시 `/change-password`로 이동. |

> T008은 T007의 API 함수에 의존. T009/T010은 T008의 컴포넌트에 의존.

---

## Phase 6: FR-007 역할별 메뉴 확인

| ID | Par | Story | Description |
|----|-----|-------|-------------|
| T011 | [P] | FR-007 | `frontend/src/components/layout/MainLayout.tsx` - 역할별 메뉴 표시 확인. USER(`user_type=USER`)는 자치법규 관련 메뉴만 표시, ADMIN(`user_type=ADMIN`)은 전체 메뉴 표시. 메뉴 숨김 처리가 올바르게 동작하는지 확인하고 누락 시 수정. |
| T012 | [P] | FR-007 | `backend/api/deps.py` - 백엔드 역할 기반 접근 차단 확인. ADMIN 전용 엔드포인트에 역할 검증이 적용되어 있는지 확인하고 누락 시 보강. USER가 ADMIN 전용 API 호출 시 403 반환. |

---

## Dependencies & Execution Order

```
Phase 3 (T001~T004): 모두 병렬 실행 가능
    │
Phase 4 (T005 → T006): 순차 실행, Phase 3과는 병렬 가능
    │
Phase 5 (T007 [P with T005~T006] → T008 → T009, T010): T007은 Phase 4와 병렬 가능, T008~T010은 순차
    │
Phase 6 (T011, T012): 병렬 실행 가능, Phase 5 이후 실행 권장
```

**요약**:
- 총 12개 태스크
- US1/US2: T001~T004 (에러 처리 보강, 기존 코드 수정)
- US3: 변경 없음 (태스크 없음)
- US4: T005~T010 (비밀번호 변경, 백엔드 1개 수정 + 프론트엔드 3개 수정/1개 신규)
- US5: Phase B 제외 (태스크 없음)
- FR-007: T011~T012 (역할별 메뉴/차단 확인)
