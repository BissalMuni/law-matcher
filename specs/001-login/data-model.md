# Data Model: 001-login

**Date**: 2026-02-28
**Input**: spec.md, research.md

## ERD

```
┌──────────────────────────┐       ┌──────────────────────────┐
│        departments       │       │          users           │
├──────────────────────────┤       ├──────────────────────────┤
│ id           PK SERIAL   │◄──┐   │ id           PK SERIAL   │
│ code         UNIQUE      │   │   │ email        UNIQUE      │
│ name         VARCHAR(200)│   │   │ username     UNIQUE      │
│ parent_name  VARCHAR(200)│   └───│ department_id FK NULL     │
│ sort_order   INTEGER     │       │ hashed_password VARCHAR   │
│ created_at   TIMESTAMP   │       │ full_name    VARCHAR(100) │
│ updated_at   TIMESTAMP   │       │ user_type    VARCHAR(20)  │
└──────────────────────────┘       │ is_active    BOOLEAN=true │
                                   │ created_at   TIMESTAMP    │
                                   │ updated_at   TIMESTAMP    │
                                   └──────────────────────────┘
```

## 테이블 스키마 (기존 구현)

### users

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    user_type VARCHAR(20) NOT NULL DEFAULT 'DEPARTMENT',
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX ix_users_email ON users(email);
CREATE UNIQUE INDEX ix_users_username ON users(username);
CREATE INDEX ix_users_user_type ON users(user_type);
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

## user_type 값 매핑

| DB 값 | 의미 | 프론트엔드 표시 | spec 참조 |
|--------|------|----------------|-----------|
| `DEPARTMENT` | 부서 사용자 | `USER` | FR-007 사용자 역할 |
| `GENERAL` | 관리자 | `ADMIN` | FR-007 관리자 역할 |

## Auth Phase A → B 전환 고려사항

현재 스키마는 Phase B 확장에 대비되어 있음:
- `email` 필드 존재 (Phase B에서 개인 로그인 식별자)
- `username` 필드 존재 (Phase B에서 개인 식별)
- `department_id` FK로 부서 소속 관리 (Phase A에서는 로그인 단위, Phase B에서는 사용자 속성)
- `is_active` 필드로 계정 비활성화 지원 (FR-008)

Auth Phase A에서는 users 테이블에 2개의 레코드만 필요:
- `username='admin'`, `user_type='GENERAL'`: 관리자 계정
- `username='user'`, `user_type='DEPARTMENT'`: 부서 공용 계정

## 변경 필요 없음

기존 마이그레이션(`add_users_table`)으로 스키마가 이미 완성되어 있어 추가 마이그레이션 불필요.
