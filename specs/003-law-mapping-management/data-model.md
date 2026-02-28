# Data Model: 003-law-mapping-management

**Date**: 2026-02-28
**Input**: spec.md, research.md

## ERD

```
┌──────────────────────┐     ┌──────────────────────────┐     ┌──────────────────────┐
│     ordinances       │     │  ordinance_law_mappings   │     │        laws          │
├──────────────────────┤     ├──────────────────────────┤     ├──────────────────────┤
│ id          PK       │◄────│ ordinance_id  FK         │     │ id          PK       │
│ code        UNIQUE   │     │ law_id        FK         │────►│ law_serial_no UNIQUE │
│ name                 │     │ related_articles VARCHAR  │     │ law_id       VARCHAR │
│ enacted_date DATE    │     │ created_at               │     │ law_name     VARCHAR │
│ no_parent_law BOOL   │     │ updated_at               │     │ proclaimed_date DATE │
│ needs_revision INT   │     │ UNIQUE(ord_id, law_id)   │     │ enforced_date  DATE  │
│ ...                  │     └──────────────────────────┘     │ revision_type VARCHAR│
└──────────┬───────────┘                                      │ last_synced_at       │
           │                                                  └──────────┬───────────┘
           │                                                             │
           │     ┌────────────────────────────┐     ┌───────────────────┤
           │     │ ordinance_article_mappings  │     │                   │
           │     ├────────────────────────────┤     │    ┌──────────────▼──────┐
           └────►│ ordinance_id  FK           │     │    │      articles       │
                 │ article_id    FK           │◄────┘    ├─────────────────────┤
                 │ mapping_reason TEXT        │          │ id          PK      │
                 │ related_article_nos VARCHAR│          │ law_id      FK      │
                 │ created_by    FK(users)    │          │ article_no  VARCHAR │
                 │ UNIQUE(ord_id, art_id)     │          │ article_content TEXT│
                 └────────────────────────────┘          │ content_hash  CHAR  │
                                                         │ paragraphs   JSON  │
                                                         │ last_synced_at     │
                                                         └─────────────────────┘
```

## 테이블 스키마 (기존 구현)

### ordinance_law_mappings

```sql
CREATE TABLE ordinance_law_mappings (
    id SERIAL PRIMARY KEY,
    ordinance_id INTEGER NOT NULL REFERENCES ordinances(id) ON DELETE CASCADE,
    law_id INTEGER NOT NULL REFERENCES laws(id) ON DELETE CASCADE,
    related_articles VARCHAR(500),  -- 관련 조문 텍스트 (예: "제3조, 제5조~제8조")
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (ordinance_id, law_id)
);
```

### ordinance_article_mappings

```sql
CREATE TABLE ordinance_article_mappings (
    id SERIAL PRIMARY KEY,
    ordinance_id INTEGER NOT NULL REFERENCES ordinances(id) ON DELETE CASCADE,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    mapping_reason TEXT,              -- 매핑 사유
    related_article_nos VARCHAR(500), -- 관련 조문 번호
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (ordinance_id, article_id)
);
```

### laws

```sql
CREATE TABLE laws (
    id SERIAL PRIMARY KEY,
    law_serial_no VARCHAR(100) UNIQUE,  -- 법령일련번호
    law_id VARCHAR(100),                 -- 법령ID
    law_name VARCHAR(500) NOT NULL,
    law_abbr VARCHAR(200),               -- 약칭
    law_type VARCHAR(100),               -- 법률/대통령령/부령
    proclaimed_date DATE,                -- 공포일자
    enforced_date DATE,                  -- 시행일자
    revision_type VARCHAR(50),           -- 제정/일부개정/전부개정
    dept_name VARCHAR(200),              -- 소관부처
    dept_code VARCHAR(50),
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### articles

```sql
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    law_id INTEGER NOT NULL REFERENCES laws(id) ON DELETE CASCADE,
    article_no VARCHAR(50) NOT NULL,     -- 조문번호
    article_title VARCHAR(500),          -- 조문제목
    article_content TEXT,                -- 조문내용
    content_hash CHAR(64),              -- SHA-256 (변경 감지용)
    paragraphs JSONB,                    -- 항/호/목 구조
    mst_seq VARCHAR(100),               -- API 식별자
    jo_seq VARCHAR(50),
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (law_id, article_no)
);
```

## Core Rule 구현

**개정대상 판별**: `law.proclaimed_date > ordinance.enacted_date` 이면 개정 검토 대상.

이 로직은 두 곳에서 적용:
1. `ordinance_service.get_list()`: 필터링 시 서브쿼리로 비교
2. `law_sync_service.sync_all_laws_with_progress()`: 동기화 후 needs_revision 플래그 설정

## 변경 필요 없음

기존 스키마로 모든 spec 요구사항이 충족됨. 추가 마이그레이션 불필요.
