# Feature Specification: 상위법령 연결 관리 기능

**Feature Branch**: `003-law-mapping-management`
**Created**: 2026-02-27
**Status**: Draft
**Constitution Ref**: Core Rule(개정대상 판별), I. 데이터 무결성, II. 외부 의존 격리

## User Scenarios & Testing

### User Story 1 - 상위법령 연결 추가 (Priority: P1)

담당자가 조례 상세 페이지에서 해당 조례의 근거가 되는 상위법령을 연결한다.
시스템에 등록된 법령 중에서 선택하거나, 법제처 API로 검색하여 추가한다.

**Why this priority**: 상위법령이 연결되어야 개정 감지가 동작한다. 시스템의 핵심 기능.

**Independent Test**: 조례 상세 → 상위법령 추가 → 연결 목록에 표시 → 개정 감지 대상 포함

**Acceptance Scenarios**:

1. **Given** 조례 상세 페이지에서 상위법령 추가 클릭,
   **When** 시스템에 등록된 법령 목록에서 선택 후 저장,
   **Then** `ordinance_law_mappings`에 레코드 생성, 관련 조문 입력 가능
2. **Given** 시스템에 없는 법령을 연결하려 할 때,
   **When** 법제처 API로 법령 검색 후 선택,
   **Then** `laws` 테이블에 법령 등록 후 매핑 생성
3. **Given** 이미 연결된 법령을 중복 추가 시도,
   **When** 저장,
   **Then** 중복 오류 메시지 표시 (unique constraint: ordinance_id + law_id)

---

### User Story 2 - 상위법령 연결 목록 조회 (Priority: P1)

담당자가 특정 조례에 연결된 상위법령 목록을 확인한다.
각 법령의 공포일자와 조례 공포일자를 비교하여 개정 필요 여부를 표시한다.

**Why this priority**: 개정 검토의 기본 화면. Core Rule 적용 결과를 보여주는 곳.

**Independent Test**: 조례 상세 → 상위법령 탭 → 법령별 개정 필요 여부 표시 확인

**Acceptance Scenarios**:

1. **Given** 상위법령이 연결된 조례의 상세 페이지,
   **When** 상위법령 탭 클릭,
   **Then** 연결된 법령 목록(법령명, 법령유형, 공포일자, 관련조문) 표시
2. **Given** 상위법령의 공포일자가 조례의 공포일자보다 이후인 경우,
   **When** 목록 표시,
   **Then** 해당 법령에 "개정 검토 필요" 표시
3. **Given** 상위법령이 없는 조례,
   **When** 상위법령 탭 확인,
   **Then** "연결된 상위법령이 없습니다" 안내 표시

---

### User Story 3 - 상위법령 연결 수정/삭제 (Priority: P1)

담당자가 잘못 연결된 상위법령을 수정하거나 삭제한다.

**Why this priority**: 오연결 수정은 데이터 정확성에 직결.

**Independent Test**: 연결 수정(관련조문 변경) → 저장 → 반영 확인 / 연결 삭제 → 목록에서 제거

**Acceptance Scenarios**:

1. **Given** 상위법령 연결의 관련조문 정보를 수정,
   **When** 저장,
   **Then** `ordinance_law_mappings.related_articles` 갱신
2. **Given** 상위법령 연결 삭제 클릭,
   **When** 확인 후 삭제,
   **Then** 매핑 레코드 삭제, 관련 조문 매핑(`ordinance_article_mappings`)도 함께 정리
3. **Given** 유일한 상위법령 연결을 삭제하려 할 때,
   **When** 삭제 시도,
   **Then** "상위법령이 모두 제거됩니다" 경고 표시 후 사용자 확인

---

### User Story 4 - 상위법령 없음 표시 (Priority: P2)

담당자가 상위법령이 존재하지 않는 조례를 명시적으로 표시한다.
표시된 조례는 개정 감지 대상에서 제외된다.

**Why this priority**: 자치조례 등 상위법령이 없는 조례를 구분하여 불필요한 검토 방지.

**Independent Test**: "상위법령 없음" 표시 → 개정 감지 대상에서 제외 확인

**Acceptance Scenarios**:

1. **Given** 상위법령이 없는 조례의 상세 페이지,
   **When** "상위법령 없음" 체크,
   **Then** `ordinances.no_parent_law = True` 설정
2. **Given** "상위법령 없음"으로 표시된 조례,
   **When** 개정 필요 목록 조회,
   **Then** 해당 조례 제외
3. **Given** "상위법령 없음" 해제,
   **When** 해제 후 저장,
   **Then** 다시 개정 감지 대상에 포함

---

### User Story 5 - 조문 단위 매핑 (Priority: P2)

담당자가 상위법령의 특정 조문과 조례를 연결한다.
조문 단위로 변경을 감지하여 정밀한 개정 검토가 가능해진다.

**Why this priority**: 법령 전체가 아닌 관련 조문만 추적하면 검토 효율 향상.

**Independent Test**: 조문 매핑 → 해당 조문 변경 시 조례에 알림

**Acceptance Scenarios**:

1. **Given** 상위법령이 연결된 조례의 상세 페이지에서 조문 매핑 탭,
   **When** 연결된 법령의 조문 목록 표시,
   **Then** 각 조문의 매핑 여부(`is_mapped`) 표시
2. **Given** 매핑할 조문 선택 후 일괄 저장,
   **When** 저장,
   **Then** `ordinance_article_mappings` 갱신 (기존 매핑 교체)
3. **Given** 매핑된 조문에 변경(`article_changes`)이 감지된 경우,
   **When** 조례 목록/상세에서 확인,
   **Then** `needs_revision = True` 표시

---

### User Story 6 - 조문 매핑 자동 추천 (Priority: P3)

시스템이 조례 내용과 법령 조문을 비교하여 관련 가능성이 높은 조문을 추천한다.

**Why this priority**: 수백 개 조문을 수동으로 검토하는 부담 경감. 편의 기능.

**Independent Test**: 자동 추천 실행 → 추천 조문 목록 → 담당자 확인 후 매핑

**Acceptance Scenarios**:

1. **Given** 조례에 상위법령이 연결된 상태에서 자동 추천 요청,
   **When** 키워드 기반 분석 실행,
   **Then** 관련 가능성 점수와 함께 추천 조문 목록 표시
2. **Given** 추천 결과에서 조문 선택,
   **When** 매핑 확인,
   **Then** `ordinance_article_mappings`에 저장

---

### Edge Cases

- 상위법령이 시스템에서 삭제된 경우 기존 매핑 처리
- 법령 동기화로 조문 번호가 변경된 경우 기존 매핑 정합성
- 하나의 조례에 연결 가능한 상위법령 수 제한 여부
- 법제처 API에서 법령을 찾을 수 없을 때 수동 등록 방법

## Requirements

### Functional Requirements

- **FR-001**: 조례와 상위법령은 N:M 관계로 `ordinance_law_mappings`를 통해 연결한다
- **FR-002**: 매핑 생성 시 `(ordinance_id, law_id)` 중복을 검사한다
- **FR-003**: 매핑에 관련 조문 정보(`related_articles`)를 기록할 수 있다
- **FR-004**: 조문 단위 매핑은 `ordinance_article_mappings`를 통해 관리한다
- **FR-005**: 상위법령의 공포일자가 조례의 공포일자 이후이면 개정 검토 대상으로 표시한다 (Core Rule)
- **FR-006**: `no_parent_law = True`인 조례는 개정 감지 대상에서 제외한다
- **FR-006a**: 상위법령 매핑이 추가되면 `no_parent_law`를 자동으로 `False`로 해제한다
- **FR-007**: 상위법령 연결 삭제 시 관련 조문 매핑도 cascade 삭제한다
- **FR-008**: 법제처 API 검색을 통해 신규 법령을 등록하면서 동시에 매핑을 생성할 수 있다

### Key Entities

- **OrdinanceLawMapping**: 조례-법령 연결. ordinance_id, law_id, related_articles
- **OrdinanceArticleMapping**: 조례-조문 연결. ordinance_id, article_id, mapping_reason
- **Law**: 상위법령. law_serial_no, law_name, proclaimed_date 등
- **Article**: 법령 조문. law_id, article_no, article_content, content_hash

## Success Criteria

### Measurable Outcomes

- **SC-001**: 상위법령 연결 추가/수정/삭제 각 작업이 2초 이내 완료
- **SC-002**: 개정 필요 판별(Core Rule)이 100% 정확 (공포일자 비교 기준)
- **SC-003**: 조문 매핑 자동 추천의 적합율 70% 이상
- **SC-004**: 상위법령이 연결된 조례 비율 90% 이상 달성 목표

## Clarifications

### Session 2026-03-01

- Q: `no_parent_law=True` 조례에 상위법령 매핑 추가 시 처리는? → A: **자동 해제**. 상위법령 매핑이 추가되면 `no_parent_law`를 자동으로 `False`로 변경하여 개정 감지 대상에 포함시킨다
