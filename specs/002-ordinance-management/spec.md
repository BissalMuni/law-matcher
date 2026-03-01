# Feature Specification: 조례 관리 기능

**Feature Branch**: `002-ordinance-management`
**Created**: 2026-02-27
**Status**: Draft
**Constitution Ref**: I. 데이터 무결성, IV. 관심사 분리, VII. 사용자 중심 설계

## User Scenarios & Testing

### User Story 1 - 조례 목록 조회 (Priority: P1)

담당자가 자신의 부서에 배정된 조례 목록을 조회하고, 조건별로 필터링한다.
관리자는 전체 부서의 조례를 조회할 수 있다.

**Why this priority**: 모든 업무의 시작점. 조례를 찾아야 검토/관리가 가능.

**Independent Test**: 로그인 → 조례 목록 표시 → 필터 적용 → 결과 확인

**Acceptance Scenarios**:

1. **Given** 부서 사용자로 로그인,
   **When** 조례 목록 페이지 접근,
   **Then** 소속 부서의 조례만 페이지네이션으로 표시
2. **Given** 관리자로 로그인,
   **When** 조례 목록 페이지 접근,
   **Then** 전체 부서의 조례 표시, 부서 필터 사용 가능
3. **Given** 조례 목록에서 검색어 입력,
   **When** 검색 실행,
   **Then** 조례명에 해당 검색어가 포함된 결과만 표시
4. **Given** 필터 조건(분류, 부서, 상위법령 유무, 개정 필요 여부) 설정,
   **When** 필터 적용,
   **Then** 조건에 맞는 조례만 표시

---

### User Story 2 - 조례 등록 (Priority: P1)

관리자가 새로운 조례를 시스템에 등록한다.
법제처 API 검색을 통해 등록하거나, 수동으로 입력할 수 있다.

**Why this priority**: 시스템에 조례가 없으면 업무가 불가능.

**Independent Test**: 조례 등록 → 목록에서 확인 → 상세 페이지 접근

**Acceptance Scenarios**:

1. **Given** 관리자가 법제처 API에서 조례를 검색,
   **When** 검색 결과에서 조례 선택 후 등록,
   **Then** `ordinances` 테이블에 저장, 법제처 메타데이터(일련번호, 분야 등) 자동 입력
2. **Given** 관리자가 수동 등록 선택,
   **When** 조례명, 분류, 부서, 공포일자 입력 후 저장,
   **Then** 새 조례 생성, 목록에서 확인 가능
3. **Given** 이미 등록된 조례코드로 등록 시도,
   **When** 저장,
   **Then** 중복 오류 메시지 표시

---

### User Story 3 - 법제처 일괄 동기화 (Priority: P1)

관리자가 법제처 API로부터 자치법규 목록을 일괄 동기화한다.
기존 조례는 갱신하고, 신규 조례는 추가한다.
동기화는 관리자가 수동으로만 실행하며, 자동 스케줄링은 지원하지 않는다.

**Why this priority**: 초기 데이터 구축 및 정기 갱신에 필수.

**Independent Test**: 동기화 실행 → 신규/갱신 건수 확인 → 목록에 반영

**Acceptance Scenarios**:

1. **Given** 관리자가 조례 동기화 실행,
   **When** 법제처 API 호출 완료,
   **Then** 신규 조례 추가, 기존 조례 메타데이터 갱신, 결과 건수 표시
2. **Given** 동기화 중 법제처 API 오류 발생,
   **When** 일부 요청 실패,
   **Then** 성공 건은 저장, 실패 건 오류 메시지 표시
3. **Given** 동기화 완료 후,
   **When** 조례 목록 새로고침,
   **Then** 최신 데이터 반영

---

### User Story 4 - 조례 상세 조회 (Priority: P1)

담당자가 특정 조례의 상세 정보를 확인한다.
조례 기본 정보, 연결된 상위법령, 검토 이력을 한 화면에서 본다.

**Why this priority**: 개정 검토 업무의 핵심 화면.

**Independent Test**: 조례 클릭 → 상세 정보 + 상위법령 목록 + 검토 이력 표시

**Acceptance Scenarios**:

1. **Given** 조례 목록에서 조례 클릭,
   **When** 상세 페이지 로드,
   **Then** 조례명, 분류, 부서, 공포일자, 제개정구분 등 기본 정보 표시
2. **Given** 상세 페이지에서,
   **When** 상위법령 탭 확인,
   **Then** 연결된 상위법령 목록과 개정 여부 표시
3. **Given** 상세 페이지에서,
   **When** 검토 이력 탭 확인,
   **Then** 해당 조례의 검토 목록(작성자, 결과, 승인 상태) 표시

---

### User Story 5 - 부서 일괄 배정 (Priority: P2)

관리자가 엑셀 파일을 업로드하여 조례의 담당 부서를 일괄 배정한다.

**Why this priority**: 초기 구축 시 수백 건의 부서 배정을 수동으로 할 수 없음.

**Independent Test**: 엑셀 업로드 → 부서 매핑 갱신 → 목록에서 부서 표시 확인

**Acceptance Scenarios**:

1. **Given** 조례코드-부서명 매핑이 담긴 엑셀 파일,
   **When** 업로드 실행,
   **Then** 각 조례의 `department_id` 갱신, 결과 건수 표시
2. **Given** 엑셀에 존재하지 않는 부서명,
   **When** 업로드 실행,
   **Then** 해당 행 건너뛰고 경고 메시지 표시

---

### User Story 6 - 조례 목록 엑셀 내보내기 (Priority: P2)

관리자가 현재 필터 조건에 맞는 조례 목록을 엑셀로 다운로드한다.

**Why this priority**: 보고서 작성 및 오프라인 검토에 필요.

**Independent Test**: 필터 설정 → 엑셀 내보내기 → 파일 열어서 내용 확인

**Acceptance Scenarios**:

1. **Given** 조례 목록에 필터 적용된 상태,
   **When** 엑셀 내보내기 클릭,
   **Then** 필터된 조례 목록이 .xlsx 파일로 다운로드

---

### Edge Cases

- 부서가 배정되지 않은 조례의 표시 및 필터링
- 법제처 API 응답이 느릴 때 타임아웃 처리
- 동기화 중 동일 조례를 동시에 수동 등록하는 경우
- `no_parent_law=True` 조례의 개정 검토 대상 제외 처리

## Requirements

### Functional Requirements

- **FR-001**: 조례 목록은 페이지네이션(기본 20건)으로 제공해야 한다
- **FR-002**: 필터 조건: 분류(조례/규칙), 부서, 검색어, 상위법령 유무, 개정 필요 여부, 제개정구분
- **FR-003**: 부서 사용자는 소속 부서의 조례만 조회할 수 있다
- **FR-004**: 관리자는 전체 조례를 조회하고 등록/동기화/비활성화할 수 있다. 조례는 하드 삭제하지 않으며, `is_active` 필드로 소프트 삭제(비활성화)한다 (Constitution I. 데이터 무결성 준수)
- **FR-005**: 법제처 API 동기화 시 `code`(자치법규ID) 기준으로 신규/갱신을 판별한다
- **FR-006**: 조례 등록 시 `code` 중복을 검사한다
- **FR-007**: 엑셀 업로드로 부서 일괄 배정이 가능하다
- **FR-008**: 엑셀 내보내기는 현재 필터 조건을 반영한다

### Key Entities

- **Ordinance**: 자치법규. code(PK역할), name, category, department_id, enacted_date, is_active, status 등
- **Department**: 담당 부서. 조례와 N:1 관계

## Success Criteria

### Measurable Outcomes

- **SC-001**: 조례 목록 로딩 2초 이내 (1000건 기준)
- **SC-002**: 법제처 동기화 완료 후 누락 조례 0건
- **SC-003**: 부서 사용자가 타 부서 조례에 접근 불가 (100% 차단)
- **SC-004**: 엑셀 업로드 시 매핑 성공률 95% 이상 (부서명 일치 기준)

## Clarifications

### Session 2026-03-01

- Q: 조례 동기화 실행 방식은? → A: **관리자 수동 실행만** 지원 (버튼 클릭). 자동 스케줄링(Celery Beat 등) 미지원
- Q: 조례 삭제 정책은? → A: **소프트 삭제** (`is_active` 필드). Constitution I. 데이터 무결성 원칙에 따라 하드 삭제 금지. 비활성화된 조례는 목록에서 기본 제외, 관리자 필터로 확인 가능
