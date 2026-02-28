# Tasks: 로그인 기능

**Input**: Design documents from `/specs/001-login/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 인증 기능 보강 작업 준비

- [ ] T001 인증 라우트/서비스 진입점 점검 in /home/jinkui/law-matcher/backend/api/v1/auth.py
- [ ] T002 비밀번호 변경 화면 라우팅 위치 점검 in /home/jinkui/law-matcher/frontend/src/App.tsx
- [ ] T003 [P] 인증 타입 정의 점검 in /home/jinkui/law-matcher/frontend/src/types/auth.ts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 공통 인증/에러 처리 기반 정비

- [ ] T004 인증 예외 코드 표준화 in /home/jinkui/law-matcher/backend/core/exceptions.py
- [ ] T005 [P] 인증 스키마 공통 메시지 정리 in /home/jinkui/law-matcher/backend/schemas/auth.py
- [ ] T006 [P] 프론트 공통 인증 에러 핸들러 정리 in /home/jinkui/law-matcher/frontend/src/services/api.ts
- [ ] T007 권한별 메뉴 표시 규칙 정비 in /home/jinkui/law-matcher/frontend/src/components/layout/MainLayout.tsx

---

## Phase 3: User Story 1 - 부서 로그인 (Priority: P1)

**Goal**: 부서 사용자가 명확한 오류와 함께 안정적으로 로그인한다

**Independent Test**: 정상 계정 로그인 성공, 잘못된 입력 시 한국어 오류 표시

- [ ] T008 [US1] 부서 로그인 실패 분기 로직 보강 in /home/jinkui/law-matcher/backend/services/auth_service.py
- [ ] T009 [US1] 로그인 API 예외 응답 매핑 보강 in /home/jinkui/law-matcher/backend/api/v1/auth.py
- [ ] T010 [P] [US1] 로그인 입력 검증/오류 UI 보강 in /home/jinkui/law-matcher/frontend/src/pages/Login.tsx
- [ ] T011 [US1] 로그인 성공 후 기본 이동 경로 정리 in /home/jinkui/law-matcher/frontend/src/contexts/AuthContext.tsx

---

## Phase 4: User Story 2 - 관리자 로그인 (Priority: P1)

**Goal**: 관리자 인증과 관리자 전용 접근 제어를 보장한다

**Independent Test**: 관리자 로그인 성공 시 관리자 메뉴 노출, 일반 사용자 차단

- [ ] T012 [US2] 관리자 로그인 검증 로직 보강 in /home/jinkui/law-matcher/backend/services/auth_service.py
- [ ] T013 [US2] 관리자 전용 의존성 검증 보강 in /home/jinkui/law-matcher/backend/api/deps.py
- [ ] T014 [P] [US2] 관리자 메뉴 렌더링 조건 보강 in /home/jinkui/law-matcher/frontend/src/components/layout/MainLayout.tsx
- [ ] T015 [US2] 보호 라우트 권한 체크 보강 in /home/jinkui/law-matcher/frontend/src/components/ProtectedRoute.tsx

---

## Phase 5: User Story 3 - 로그아웃 (Priority: P1)

**Goal**: 로그아웃 시 인증 상태와 토큰이 즉시 해제된다

**Independent Test**: 로그아웃 직후 보호 페이지 접근 시 로그인 페이지로 이동

- [ ] T016 [US3] 로그아웃 API 호출/응답 처리 점검 in /home/jinkui/law-matcher/backend/api/v1/auth.py
- [ ] T017 [US3] 클라이언트 토큰 제거/상태 초기화 보강 in /home/jinkui/law-matcher/frontend/src/contexts/AuthContext.tsx
- [ ] T018 [US3] 로그아웃 후 라우팅 전환 정비 in /home/jinkui/law-matcher/frontend/src/components/layout/MainLayout.tsx

---

## Phase 6: User Story 4 - 비밀번호 변경 (Priority: P2)

**Goal**: 현재 비밀번호 검증 후 새 비밀번호로 변경한다

**Independent Test**: 비밀번호 변경 성공 후 재로그인 가능, 현재 비밀번호 오류 시 실패

- [ ] T019 [US4] change-password 엔드포인트 구현 in /home/jinkui/law-matcher/backend/api/v1/auth.py
- [ ] T020 [US4] 비밀번호 변경 서비스 검증/저장 로직 보강 in /home/jinkui/law-matcher/backend/services/auth_service.py
- [ ] T021 [P] [US4] 비밀번호 변경 요청/응답 스키마 보강 in /home/jinkui/law-matcher/backend/schemas/auth.py
- [ ] T022 [P] [US4] 비밀번호 변경 API 함수 추가 in /home/jinkui/law-matcher/frontend/src/services/api.ts
- [ ] T023 [US4] 비밀번호 변경 페이지 구현 in /home/jinkui/law-matcher/frontend/src/pages/ChangePassword.tsx
- [ ] T024 [US4] 비밀번호 변경 라우트/메뉴 연결 in /home/jinkui/law-matcher/frontend/src/App.tsx

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 인증 기능 전반 품질 정리

- [ ] T025 [P] 인증 한국어 문구 일관성 정리 in /home/jinkui/law-matcher/frontend/src/pages/Login.tsx
- [ ] T026 비밀번호 정책 안내 문구 정리 in /home/jinkui/law-matcher/frontend/src/pages/ChangePassword.tsx
- [ ] T027 인증 로깅/감사 항목 보강 in /home/jinkui/law-matcher/backend/services/auth_service.py
- [ ] T028 인증 기능 문서 업데이트 in /home/jinkui/law-matcher/docs/auth-login.md

---

## Dependencies & Execution Order

- Setup → Foundational 완료 후 US1~US4 진행
- US1~US3 완료 후 US4 진행 권장
- Polish는 모든 스토리 완료 후 진행

## Parallel Opportunities

- T003, T005, T006
- T010, T014
- T021, T022
- T025

## Implementation Strategy

1. MVP: US1~US3
2. 확장: US4
3. 마무리: Polish
