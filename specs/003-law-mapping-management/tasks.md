# Tasks: 상위법령 연결 관리 기능

**Input**: Design documents from `/specs/003-law-mapping-management/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 매핑 기능 보강 작업 준비

- [ ] T001 매핑 API/서비스 진입점 점검 in /home/jinkui/law-matcher/backend/api/v1/ordinances.py
- [ ] T002 법제처 동기화 연계 경로 점검 in /home/jinkui/law-matcher/backend/services/law_sync_service.py
- [ ] T003 [P] 매핑 화면 경고/오류 표시 위치 점검 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 공통 재시도/에러 처리 기반 구축

- [ ] T004 법제처 API 재시도 정책 반영 in /home/jinkui/law-matcher/backend/external/moleg_client.py
- [ ] T005 [P] 매핑 공통 한국어 에러 상수 정리 in /home/jinkui/law-matcher/backend/schemas/ordinance.py
- [ ] T006 [P] 프론트 API 에러 변환 공통 처리 정리 in /home/jinkui/law-matcher/frontend/src/services/api.ts
- [ ] T007 매핑 정합성 경고 공통 포맷 정리 in /home/jinkui/law-matcher/backend/services/article_service.py

---

## Phase 3: User Story 1 - 상위법령 연결 추가 (Priority: P1)

**Goal**: 중복 검증과 함께 상위법령 연결을 추가한다

**Independent Test**: 신규 연결 성공, 중복 연결 시 한국어 오류 반환

- [ ] T008 [US1] 연결 생성 중복 검증 로직 보강 in /home/jinkui/law-matcher/backend/services/ordinance_service.py
- [ ] T009 [US1] 연결 추가 API 예외 응답 정리 in /home/jinkui/law-matcher/backend/api/v1/ordinances.py
- [ ] T010 [P] [US1] 연결 추가 실패 메시지 UI 보강 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx

---

## Phase 4: User Story 2 - 상위법령 연결 목록 조회 (Priority: P1)

**Goal**: 연결 목록 조회 실패 복구와 상태 안내를 제공한다

**Independent Test**: 조회 실패 시 안내, 재조회 성공 시 목록 정상 표시

- [ ] T011 [US2] 목록 조회 예외 분기 보강 in /home/jinkui/law-matcher/backend/services/ordinance_service.py
- [ ] T012 [US2] 목록 API 오류 응답 한국어화 in /home/jinkui/law-matcher/backend/api/v1/ordinances.py
- [ ] T013 [P] [US2] 목록 로딩/오류 상태 UI 정리 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx

---

## Phase 5: User Story 3 - 상위법령 연결 수정/삭제 (Priority: P1)

**Goal**: 위험 삭제 작업에 경고를 제공한다

**Independent Test**: 마지막 연결 삭제 시 경고 확인 절차 동작

- [ ] T014 [US3] 마지막 연결 삭제 경고 검증 로직 추가 in /home/jinkui/law-matcher/backend/services/ordinance_service.py
- [ ] T015 [US3] 연결 수정/삭제 API 예외 응답 보강 in /home/jinkui/law-matcher/backend/api/v1/ordinances.py
- [ ] T016 [P] [US3] 연결 삭제 확인 모달 경고 문구 보강 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx

---

## Phase 6: User Story 4 - 상위법령 없음 표시 (Priority: P2)

**Goal**: 연결 0건 상태를 명확히 표시한다

**Independent Test**: 상위법령 없음 상태에서 안내 배너 노출

- [ ] T017 [US4] 무연결 상태 응답 필드 정리 in /home/jinkui/law-matcher/backend/schemas/ordinance.py
- [ ] T018 [US4] 무연결 상태 안내 UI 보강 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx

---

## Phase 7: User Story 5 - 조문 단위 매핑 (Priority: P2)

**Goal**: 조문 삭제/변경 시 매핑 영향 경고를 제공한다

**Independent Test**: 매핑된 조문 삭제 시 영향 경고 표시

- [ ] T019 [US5] 조문 삭제 영향 계산 로직 보강 in /home/jinkui/law-matcher/backend/services/article_service.py
- [ ] T020 [US5] 조문 매핑 API 영향 경고 필드 반영 in /home/jinkui/law-matcher/backend/api/v1/articles.py
- [ ] T021 [P] [US5] 조문 매핑 경고 UI 보강 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx

---

## Phase 8: User Story 6 - 조문 매핑 자동 추천 (Priority: P3)

**Goal**: 추천 기능 실패 복구와 안내를 보강한다

**Independent Test**: 추천 실패 시 안내, 성공 시 추천 목록 표시

- [ ] T022 [US6] 추천 계산 실패 복구 로직 보강 in /home/jinkui/law-matcher/backend/services/article_service.py
- [ ] T023 [US6] 추천 API 오류 응답 한국어화 in /home/jinkui/law-matcher/backend/api/v1/articles.py

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 매핑 기능 전반 품질 정리

- [ ] T024 [P] 재시도/장애 로깅 보강 in /home/jinkui/law-matcher/backend/external/moleg_client.py
- [ ] T025 매핑 경고 문구/툴팁 일관성 정리 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx
- [ ] T026 추천 결과/실패 상태 UI 정리 in /home/jinkui/law-matcher/frontend/src/pages/OrdinanceDetail.tsx
- [ ] T027 매핑 관련 API 문서 정리 in /home/jinkui/law-matcher/backend/api/v1/ordinances.py
- [ ] T028 상위법령 연결 관리 문서 업데이트 in /home/jinkui/law-matcher/docs/law-mapping-management.md

---

## Dependencies & Execution Order

- Setup → Foundational 완료 후 US1~US6 진행
- P1(US1~US3) 우선 후 P2/P3 진행
- Polish는 전체 완료 후 진행

## Parallel Opportunities

- T003, T005, T006
- T010, T013, T016
- T021, T024

## Implementation Strategy

1. MVP: US1~US3
2. 확장: US4~US6
3. 마무리: Polish
