# Research: 개정법령 변경이력 관리

**Feature**: [spec.md](spec.md) | **Date**: 2026-02-27

## Research Items

### R1: law_changes 테이블 status 필드 제거 방안

**배경**: 현재 law_changes.status는 ChangeStatus enum (PENDING/REVIEWING/APPROVED/REJECTED)을 사용하며, approve/reject API 엔드포인트가 존재. Spec에 따르면 law_changes는 감지 로그 전용이므로 승인/반려 워크플로우를 제거해야 함.

**Decision**: law_changes.status 컬럼 및 ChangeStatus enum 제거. 관련 processed_at, processed_by, process_note 컬럼도 제거.

**Rationale**:
- Spec 명시: "law_changes에 대한 승인/반려 워크플로우 없음"
- 감지 로그는 생성만 되고 상태 변경 없음 → status 필드 불필요
- api_status (SUCCESS/NO_RESPONSE/NOT_FOUND)만 남겨 API 응답 상태 추적

**Alternatives considered**:
- status를 남기되 읽기 전용으로 사용 → 불필요한 복잡성, 혼란 유발
- status를 "logged" 단일 값으로 변경 → 의미 없는 필드 유지

**Migration strategy**:
1. 새 마이그레이션에서 status, processed_at, processed_by, process_note 컬럼 DROP
2. 기존 데이터는 이미 기록 목적이므로 손실 허용 가능 (또는 process_note만 별도 백업)
3. API 엔드포인트에서 approve/reject/bulk-approve/bulk-reject 제거
4. 프론트엔드에서 관련 UI 제거

---

### R2: ordinances.revision_status 필드 도입

**배경**: 현재 ordinances에는 `needs_revision: bool` (nullable) 필드만 존재. Spec 요구사항은 null/검토대기/검토중/개정확정의 4가지 상태를 가진 revision_status 문자열 필드.

**Decision**: `needs_revision` boolean을 `revision_status` String(20) nullable 필드로 교체.

**Rationale**:
- Boolean은 4가지 상태를 표현할 수 없음
- 문자열 필드가 상태 생명주기를 직관적으로 표현
- Phase 2 Java 전환 시 표준 VARCHAR로 호환

**Field design**:
- 타입: `String(20), nullable=True, index=True`
- 값: `null` (정상), `"검토대기"`, `"검토중"`, `"개정확정"`
- 인덱스 필요: 빨간불 조례 필터링 시 `WHERE revision_status IS NOT NULL` 빈번

**Migration strategy**:
1. `revision_status` 컬럼 추가 (nullable)
2. `needs_revision = True`인 기존 데이터 → `revision_status = "검토대기"` 이관
3. `needs_revision` 컬럼 DROP
4. 모델, 스키마, API, 프론트엔드 코드 업데이트

---

### R3: 자동 "검토중" 전환 구현 방식

**배경**: 부서 담당자가 "검토대기" 조례 상세를 열람하면 자동으로 "검토중"으로 전환 (FR-010).

**Decision**: 조례 상세 조회 API (`GET /api/v1/ordinances/{id}`) 내에서 조건부 UPDATE 수행.

**Rationale**:
- 프론트엔드에서 별도 API 호출 불필요 → UX 단순화
- 단일 트랜잭션 내 처리 가능
- 조건: `revision_status == "검토대기"` AND 요청자가 해당 부서 담당자

**Implementation approach**:
```python
# ordinances.py GET /{ordinance_id} 내부
if ordinance.revision_status == "검토대기" and current_user.is_department_user:
    ordinance.revision_status = "검토중"
    await db.commit()
```

**Alternatives considered**:
- 별도 PATCH API → 프론트엔드에서 추가 호출 필요, 누락 위험
- WebSocket 이벤트 → 과도한 복잡성
- 프론트엔드에서 자동 호출 → 네트워크 오류 시 불일치 위험

---

### R4: 승인 후 데이터 처리 로직

**배경**: 관리자가 검토의견을 승인/반려할 때 ordinances.revision_status를 자동으로 변경해야 함 (FR-012~FR-014).

**Decision**: review 승인/반려 API에서 단일 트랜잭션 내 ordinance.revision_status 업데이트.

**Processing rules**:
| review_result | admin_action | revision_status 변경 |
|---------------|-------------|---------------------|
| 개정필요 | 승인 | → "개정확정" |
| 개정불필요 | 승인 | → null |
| (무관) | 반려 | → "검토대기" |

**Implementation approach**:
```python
# review 승인 API 내부
if action == "approve":
    if review.review_result == "개정필요":
        ordinance.revision_status = "개정확정"
    elif review.review_result == "개정불필요":
        ordinance.revision_status = None
elif action == "reject":
    ordinance.revision_status = "검토대기"
```

**Rationale**:
- 단일 트랜잭션: review 승인 + ordinance 상태 변경이 원자적으로 처리
- Service 계층에서 비즈니스 로직 캡슐화
- 실패 시 전체 롤백으로 데이터 정합성 보장

---

### R5: 검토대상 자동 플래깅 로직 (동기화 후)

**배경**: 동기화 완료 후 검토대상 조례를 자동 판별하여 revision_status = "검토대기" 설정 (FR-009).

**Decision**: 동기화 서비스(law_sync_service.py) 완료 단계에서 플래깅 로직 실행.

**Flagging criteria**:
- 법령 변경이 감지된 law_id에 대해
- ordinance_law_mappings로 연계된 조례를 조회
- 해당 조례의 현재 revision_status가 null인 경우만 "검토대기"로 설정
- 이미 "검토대기"/"검토중"/"개정확정"인 조례는 변경하지 않음 (중복 플래깅 방지)

**Implementation approach**:
```python
# law_sync_service.py - 동기화 완료 후
flagged_law_ids = [change.law_id for change in new_changes if change.api_status == ApiStatus.SUCCESS]
ordinances_to_flag = (
    select(Ordinance)
    .join(OrdinanceLawMapping)
    .where(
        OrdinanceLawMapping.law_id.in_(flagged_law_ids),
        Ordinance.revision_status.is_(None)
    )
)
for ordinance in ordinances_to_flag:
    ordinance.revision_status = "검토대기"
```

**Rationale**:
- 동기화 트랜잭션 내에서 원자적 처리
- 상위법령 공포일 > 조례 공포일 비교는 검토대상 판별 시점에 Core Rule로 적용
- null 체크로 중복 플래깅 방지

---

### R6: review_result 값 제한

**배경**: 현재 ordinance_review.review_result는 자유 문자열. Spec에서는 "개정필요"/"개정불필요" 2가지만 허용.

**Decision**: Pydantic schema에서 Literal["개정필요", "개정불필요"]로 검증. DB는 String 유지.

**Rationale**:
- DB에 SQLEnum 사용 시 Phase 2 Java 전환에서 호환성 문제
- 표준 SQL VARCHAR + 애플리케이션 레벨 검증이 전환에 유리
- Pydantic으로 입력 검증, DB constraint는 CHECK로 보강 가능

---

### R7: "개정확정" 수동 해제

**배경**: 조례 개정이 실제 완료된 후 관리자가 수동으로 revision_status를 null로 변경 (FR-015).

**Decision**: 관리자 전용 PATCH 엔드포인트에서 revision_status null 설정.

**Implementation approach**:
- `POST /api/v1/ordinances/{id}/clear-revision` (관리자 전용)
- 조건: revision_status == "개정확정"일 때만 허용
- 결과: revision_status = null (빨간불 OFF)

**Rationale**:
- 명시적 엔드포인트로 의도적 작업 구분
- 관리자 권한 체크 필수
- 감사 로그 남기기 용이
