# Data Model: 002-ordinance-management

**Date**: 2026-02-28
**Input**: spec.md, research.md

## ERD

```
┌──────────────────────────┐       ┌──────────────────────────┐
│      departments         │       │       ordinances          │
├──────────────────────────┤       ├──────────────────────────┤
│ id           PK SERIAL   │◄──┐   │ id           PK SERIAL   │
│ code         UNIQUE      │   │   │ code         UNIQUE      │
│ name         VARCHAR(200)│   │   │ name         VARCHAR(500)│
│ parent_name  VARCHAR(200)│   └───│ department_id FK NULL     │
│ sort_order   INTEGER     │       │ department   VARCHAR(200)│
│ created_at   TIMESTAMP   │       │ category     VARCHAR(50) │
│ updated_at   TIMESTAMP   │       │ enacted_date DATE        │
└──────────────────────────┘       │ enforced_date DATE       │
                                   │ revision_date DATE       │
                                   │ status       VARCHAR(20) │
                                   │ no_parent_law BOOLEAN    │
                                   │ needs_revision INTEGER   │
                                   │ serial_no    VARCHAR     │
                                   │ field_name   VARCHAR     │
                                   │ revision_type VARCHAR    │
                                   │ detail_link  VARCHAR     │
                                   │ created_at   TIMESTAMP   │
                                   │ updated_at   TIMESTAMP   │
                                   └──────────┬───────────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          │                   │                   │
              ┌───────────▼──────┐ ┌─────────▼────────┐ ┌───────▼──────────┐
              │ ordinance_law_   │ │ ordinance_       │ │ ordinance_       │
              │ mappings         │ │ reviews          │ │ article_mappings │
              ├──────────────────┤ ├──────────────────┤ ├──────────────────┤
              │ ordinance_id FK  │ │ ordinance_id FK  │ │ ordinance_id FK  │
              │ law_id FK        │ │ reviewer_type    │ │ article_id FK    │
              │ related_articles │ │ review_result    │ │ mapping_reason   │
              └──────────────────┘ │ approval_status  │ └──────────────────┘
                                   └──────────────────┘
```

## 테이블 스키마 (기존 구현)

### ordinances

```sql
CREATE TABLE ordinances (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(500) NOT NULL,
    category VARCHAR(50),              -- '조례' | '규칙'
    department VARCHAR(200),           -- 소관부서명 (텍스트)
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    enacted_date DATE,                 -- 공포일자
    enforced_date DATE,                -- 시행일자
    revision_date DATE,                -- 개정일자
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',  -- 'ACTIVE' | 'ABOLISHED' | 'EXCLUDED'
    no_parent_law BOOLEAN DEFAULT FALSE,
    needs_revision INTEGER,            -- NULL: 미확인, 0: 해당없음, 1: 개정대상
    -- 법제처 API 메타데이터
    serial_no VARCHAR(100),
    field_name VARCHAR(200),
    org_name VARCHAR(200),
    promulgation_no VARCHAR(100),
    revision_type VARCHAR(50),         -- 제개정구분 (제정/일부개정/전부개정/폐지 등)
    detail_link VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### departments

```sql
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    parent_name VARCHAR(200),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## status 값 매핑 (변경사항)

| DB 값 | 의미 | 설명 |
|--------|------|------|
| `ACTIVE` | 현행 | 시행 중인 조례 (기본값) |
| `ABOLISHED` | 폐지 | **신규**. 법적으로 소멸. 데이터 보존, 검토 대상 제외 |
| `EXCLUDED` | 관리 제외 | 시스템 운영상 관리 대상에서 제외 (예: 의회사무국) |

### 폐지 감지 로직

법제처 동기화 시 `revision_type`이 `'폐지'`인 조례는 `status='ABOLISHED'`로 자동 전환.
- 폐지된 조례는 목록에서 기본 필터로 제외 (필터 옵션으로 표시 가능)
- 폐지된 조례의 기존 검토 이력, 상위법령 연결은 보존 (I. 데이터 무결성)
- 폐지된 조례는 개정 검토 대상에서 자동 제외 (needs_revision 업데이트 중단)

## 변경 필요 사항

### 마이그레이션 필요

1. `status` 필드의 유효 값에 `ABOLISHED` 추가 (CHECK constraint 또는 애플리케이션 레벨 검증)
2. 기존 데이터 중 `revision_type='폐지'`인 조례의 `status`를 `ABOLISHED`로 갱신

### 서비스 로직 변경

1. `sync_from_moleg()`: 동기화 시 `revision_type` 확인하여 `status` 자동 설정
2. `get_list()`: 기본 필터에 `status != 'ABOLISHED'` 조건 추가 (옵션으로 포함 가능)
3. 개정 대상 판별 시 `status='ABOLISHED'` 조례 제외
