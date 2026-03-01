# Tasks 통합 보고서

**Date**: 2026-03-02
**작업**: Codex 생성 tasks.md와 로컬(clarify 반영) tasks.md 비교 후 누락 항목 통합

## 배경

| 버전 | 출처 | 커밋 | 특성 |
|------|------|------|------|
| Codex | 리모트 `55ad899` | Codex가 spec/plan 기반으로 자동 생성 | US별 균일 28개 구조, 리눅스 절대경로 |
| 로컬 | `d75237b` | `/speckit.tasks`로 생성 (clarify 반영) | 기술 레이어별 구조, 상대경로, FR 참조 포함 |

Git merge 시 6개 tasks.md 충돌 발생 → 로컬 버전으로 resolve (`git checkout --ours`) → 이후 비교 분석하여 Codex에만 있는 HIGH/MEDIUM 항목을 로컬에 통합.

## 비교 방법

1. `git show 55ad899:specs/{feature}/tasks.md`로 Codex 버전 추출
2. 현재 로컬 tasks.md와 태스크 단위로 대조
3. Codex에만 있는 항목을 우선순위로 분류 (HIGH / MEDIUM / LOW)
4. HIGH + MEDIUM 항목을 로컬 tasks.md에 통합

## 통합 결과

### 001-login (12 → 17, +5)

| 추가 ID | 내용 | 출처 | 우선순위 |
|---------|------|------|----------|
| T013 | ProtectedRoute 권한 체크 보강 (ADMIN 전용 라우트 레벨 검증) | Codex T015 | MEDIUM |
| T014 | 로그아웃 API 호출/응답 처리 점검 | Codex T016 | MEDIUM |
| T015 | 클라이언트 토큰 제거/인증 상태 초기화 | Codex T017 | MEDIUM |
| T016 | 로그아웃 후 라우팅 전환 (→ /login) | Codex T018 | MEDIUM |
| T017 | 로그인 성공 후 역할별 기본 랜딩 페이지 분기 | Codex T011 | MEDIUM |

**판단 근거**: 로컬 버전은 US3(로그아웃)을 "변경 없음"으로 분류했으나, 토큰 제거/상태 초기화/리다이렉트는 보안상 중요. 로그인 후 네비게이션 목적지도 UX 핵심.

### 002-ordinance-management (11 → 14, +3)

| 추가 ID | 내용 | 출처 | 우선순위 |
|---------|------|------|----------|
| T012 | 부서 배정 시 ABOLISHED 조례 처리 규칙 (차단/경고) | Codex T020 | MEDIUM |
| T013 | 부서 배정 UI에서 ABOLISHED 조례 경고 메시지 | Codex T021 | MEDIUM |
| T014 | 기존 T011(Polish) 번호 변경, 의존성에 T013 추가 | 리넘버링 | - |

**판단 근거**: ABOLISHED 상태 도입 시 부서 배정 로직에서 폐지 조례를 어떻게 처리할지 미정의. 사용자가 폐지 조례를 선택하여 배정하면 혼란 발생.

### 003-law-mapping-management (10 → 12, +2)

| 추가 ID | 내용 | 출처 | 우선순위 |
|---------|------|------|----------|
| T011 | 자동추천 계산 실패 복구 (예외 catch, partial results, 로깅) | Codex T022 | MEDIUM |
| T012 | 자동추천 API 에러 응답 한국어화 | Codex T023 | MEDIUM |

**판단 근거**: 자동추천 기능이 구현되어 있다면 실패 시 복구 로직과 한국어 에러 메시지가 필요. 로컬 버전은 이 영역을 커버하지 않음.

### 004-law-change-tracking (18 → 27, +9)

| 추가 ID | 내용 | 출처 | 우선순위 |
|---------|------|------|----------|
| T019 | 엑셀 내보내기 서비스 쿼리 (필터 반영, 스트리밍) | Codex T018 | HIGH |
| T020 | 엑셀 내보내기 API + 프론트 다운로드 버튼 | Codex T019 | HIGH |
| T021 | 통계 집계 서비스 (기간/상태별 변경 건수) | Codex T020 | HIGH |
| T022 | 통계 API + 프론트 Statistic 카드 | Codex T021 | HIGH |
| T023 | 법령별 이력 조회 API (시간순, 페이지네이션) | Codex T022 | MEDIUM |
| T024 | 법령별 이력 필터 UI (드롭다운/검색) | Codex T023 | MEDIUM |
| T025 | 배치 실행 이력 기록 로직 | Codex T024 | MEDIUM |
| T026 | 배치 상태 조회 API + 프론트 표시 | Codex T025 | MEDIUM |
| T027 | 기존 T018(Polish) 번호 변경 | 리넘버링 | - |

**판단 근거**: 로컬 버전은 US1-US5(P1)만 포함. Codex는 US6-US9(P2/P3)도 포함. spec.md에 9개 US가 정의되어 있으므로 4개 US 누락은 커버리지 gap.

### 005-revision-detection-tabs (21 → 23, +2)

| 추가 ID | 내용 | 출처 | 우선순위 |
|---------|------|------|----------|
| T007a | 조문 동기화 시 revision_type_detail/change_flag 메타 저장 | Codex T014 | MEDIUM |
| T007b | 조문 API 응답 스키마에 새 필드 직렬화 | Codex T015 | MEDIUM |

**판단 근거**: T004에서 Article 모델에 필드를 추가하지만, 동기화 시 실제로 DB에 저장하는 태스크와 API 응답에 포함하는 태스크가 없으면 TabB에서 데이터가 비어있게 됨.

### 006-llm-review-assistant (30 → 31, +1)

| 추가 ID | 내용 | 출처 | 우선순위 |
|---------|------|------|----------|
| T031 | 보안 전송 정책 점검 (공공데이터만 LLM 전송 검증) | Codex T027 | MEDIUM |

**판단 근거**: Constitution VI(보안 기본 적용). LLM에 전송되는 데이터가 공공데이터(제개정이유, 조례 원문)만 포함하는지 명시적 검증 태스크가 필요. 관공서 보안성 검토 대상 프로젝트.

## 통합하지 않은 항목 (LOW)

| 카테고리 | 내용 | 사유 |
|---------|------|------|
| Setup 점검 태스크 | 각 피처 T001-T003 (진입점 점검, 영향 파일 점검) | 코드 리뷰 성격, 별도 태스크 불필요 |
| Polish: 문서화 | docs/*.md 업데이트 | 구현 완료 후 별도 진행 |
| Polish: 로깅/감사 | 상태 전환 로깅 보강 | 로컬의 엣지케이스 태스크에서 부분 커버 |
| Polish: 문구 일관성 | 전체 문구/배지 통일 | 로컬의 Polish 태스크에서 부분 커버 |
| 006: 스키마 일관성 | API 응답 타입 일관성 점검 | 구현 시 자연스럽게 해결 |

## 수치 요약

| 피처 | 통합 전 | 통합 후 | 증감 |
|------|---------|---------|------|
| 001-login | 12 | 17 | +5 |
| 002-ordinance-management | 11 | 14 | +3 |
| 003-law-mapping-management | 10 | 12 | +2 |
| 004-law-change-tracking | 18 | 27 | +9 |
| 005-revision-detection-tabs | 21 | 23 | +2 |
| 006-llm-review-assistant | 30 | 31 | +1 |
| **합계** | **101** | **124** | **+22** |

## 로컬 버전 유지 사유

- FR/NFR 참조가 태스크에 직접 연결 (예: FR-009, FR-012)
- 구체적 구현 파라미터 (retry 횟수, 타임아웃, 정규식 패턴, 한국어 에러 메시지 원문)
- 의존성 DAG 시각화 (ASCII 그래프)
- 엣지케이스 처리 명시 (동시 접근, 중복 방지, race condition)
- 상대경로 사용 (`backend/...` vs `/home/jinkui/law-matcher/...`)
- clarify 세션에서 확정된 요구사항 반영 (FR-005a, FR-006a 등)
