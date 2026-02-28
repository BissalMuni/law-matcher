# Data Model: 개정법령 변경이력 관리

**Feature**: [spec.md](spec.md) | **Date**: 2026-02-27

## Entity Overview

```
┌──────────────┐     ┌────────────────────┐     ┌────────────────┐
│     laws     │──1:N──│   law_changes      │     │  departments   │
│              │     │  (감지 로그 전용)     │     │                │
└──────┬───────┘     └────────────────────┘     └───────┬────────┘
       │                                                 │
       │ N:M (ordinance_law_mappings)                   │ 1:N
       │                                                 │
┌──────┴───────┐                              ┌─────────┴────────┐
│  ordinances  │──1:N──────────────────────── │     users        │
│ +revision_   │     ┌────────────────────┐   │ (부서 담당자/관리자) │
│  status      │     │ ordinance_reviews  │   └──────────────────┘
│              │──1:N──│ (검토의견+승인)     │
└──────────────┘     └────────────────────┘
```

## Entity Definitions

### law_changes (수정)

감지 로그 전용. 동기화 시 변경 감지 기록만 저장. **승인/반려 워크플로우 없음**.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | INTEGER PK | NO | auto | |
| law_id | INTEGER FK(laws.id) | NO | | 대상 법령 |
| sync_date | DATETIME | NO | | 동기화 실시 일자 |
| sync_batch_id | VARCHAR(50) | YES | | 동기화 배치 ID |
| api_status | VARCHAR(20) | NO | 'success' | API 응답 상태 (success/no_response/not_found) |
| api_message | VARCHAR(500) | YES | | API 메시지 |
| old_values | JSON | YES | | 변경 전 값 |
| new_values | JSON | YES | | 변경 후 값 (API에서 받은 새 값) |
| dept_name | VARCHAR(200) | YES | | 소관부처명 |
| dept_code | INTEGER | YES | | 소관부처코드 |
| created_at | DATETIME | NO | now() | 생성일시 |

**제거 대상 컬럼**: `status`, `processed_at`, `processed_by`, `process_note`, `updated_at`

**Indexes**: law_id, sync_date, sync_batch_id, api_status

**Unique constraint**: (law_id, sync_batch_id) - 동일 배치 내 동일 법령 중복 방지

**JSON schema** (old_values / new_values):
```json
{
  "proclaimed_date": "2024-01-01",
  "enforced_date": "2024-03-01",
  "revision_type": "일부개정",
  "law_id": 123456,
  "dept_name": "법무부"
}
```

---

### ordinances (수정)

`needs_revision: bool` → `revision_status: VARCHAR(20) nullable` 교체.

| Column | Type | Change | Description |
|--------|------|--------|-------------|
| revision_status | VARCHAR(20), nullable, indexed | **NEW** | 검토 상태 |
| needs_revision | bool, nullable | **DROP** | 기존 필드 제거 |

**revision_status values & lifecycle**:

| Value | 의미 | 빨간불 | 전환 조건 |
|-------|------|--------|----------|
| null | 정상 | OFF | 기본 상태 / 개정불필요 승인 / 수동 해제 |
| "검토대기" | 검토 필요 | ON | 동기화 후 자동 플래깅 / 반려 시 원복 |
| "검토중" | 담당자 확인 중 | ON | 담당자 상세 열람 시 자동 전환 |
| "개정확정" | 개정 확정 | ON | 개정필요 승인 시 |

**State transitions**:
```
null ──[sync flagging]──→ "검토대기"
"검토대기" ──[staff view detail]──→ "검토중"
"검토중" ──[개정필요 approved]──→ "개정확정"
"검토중" ──[개정불필요 approved]──→ null
"검토중" ──[rejected]──→ "검토대기"
"개정확정" ──[admin manual clear]──→ null
```

---

### ordinance_reviews (수정)

| Column | Type | Change | Description |
|--------|------|--------|-------------|
| review_result | VARCHAR(50) | **CONSTRAIN** | "개정필요" 또는 "개정불필요" (2가지만) |

**제거 대상 값**: "검토중", "보류" (기존 데이터 마이그레이션 필요)

**기존 유지 컬럼**:
- approval_status: "pending" / "approved" / "rejected"
- approved_by_id, approved_at, approval_note

---

### laws (변경 없음)

참조 테이블. 변경 감지 대상.

---

### ordinance_law_mappings (변경 없음)

조례↔법령 N:M 매핑. 플래깅 시 연계 조례 조회에 사용.

## Migration Plan

### Migration 1: revision_status 도입

```sql
-- Add revision_status column
ALTER TABLE ordinances ADD COLUMN revision_status VARCHAR(20);
CREATE INDEX ix_ordinances_revision_status ON ordinances(revision_status);

-- Migrate existing data
UPDATE ordinances SET revision_status = '검토대기' WHERE needs_revision = TRUE;

-- Drop old column
ALTER TABLE ordinances DROP COLUMN needs_revision;
```

### Migration 2: law_changes 단순화

```sql
-- Remove approval workflow columns
ALTER TABLE law_changes DROP COLUMN status;
ALTER TABLE law_changes DROP COLUMN processed_at;
ALTER TABLE law_changes DROP COLUMN processed_by;
ALTER TABLE law_changes DROP COLUMN process_note;
ALTER TABLE law_changes DROP COLUMN updated_at;

-- Add unique constraint
ALTER TABLE law_changes ADD CONSTRAINT uq_law_changes_law_batch
  UNIQUE (law_id, sync_batch_id);
```

### Migration 3: review_result 정리

```sql
-- Clean up invalid review_result values
UPDATE ordinance_reviews SET review_result = '개정필요'
  WHERE review_result = '검토중';
-- "보류" 데이터는 현재 없으므로 별도 처리 불요
```

## Data Volume Estimates

| Entity | Current Est. | Growth Rate |
|--------|-------------|-------------|
| laws | ~5,000 | 연 수백 건 변경 |
| ordinances | ~1,000-3,000 | 저빈도 추가 |
| law_changes | ~10,000+ | 동기화당 수백~수천 건 |
| ordinance_reviews | ~500 | 검토 건수 비례 |
| ordinance_law_mappings | ~3,000-5,000 | 매핑 설정 비례 |
