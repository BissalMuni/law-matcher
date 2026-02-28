# Data Model: 005-revision-detection-tabs

**Date**: 2026-02-28
**Input**: spec.md, research.md

## ERD (신규/변경 부분)

```
┌──────────────────────┐
│        laws           │
├──────────────────────┤
│ id          PK       │
│ law_serial_no UNIQUE │     ┌─────────────────────────────┐
│ proclaimed_date DATE │     │   law_revision_reasons       │
│ ...                  │     ├─────────────────────────────┤
└──────────┬───────────┘     │ id              PK SERIAL   │
           │                 │ law_id          FK UNIQUE    │
           └────────────────►│ law_mst         VARCHAR      │
                             │ revision_reason TEXT          │
                             │ amendment_content TEXT        │
                             │ extracted_articles JSON       │
                             │ fetched_at      TIMESTAMP    │
                             │ created_at      TIMESTAMP    │
                             │ updated_at      TIMESTAMP    │
                             └─────────────────────────────┘

┌──────────────────────┐
│      articles         │
├──────────────────────┤
│ id          PK       │
│ law_id      FK       │     ┌──────────────────────────────┐
│ article_no  VARCHAR  │     │  revision_detection_results   │
│ content_hash CHAR(64)│     ├──────────────────────────────┤
│ revision_type_detail │ NEW │ id               PK SERIAL   │
│ change_flag  VARCHAR │ NEW │ ordinance_id     FK           │
│ ...                  │     │ law_id           FK           │
└──────────────────────┘     │ detection_method VARCHAR      │
                             │ needs_revision   BOOLEAN      │
                             │ detail           JSON          │
                             │ detected_at      TIMESTAMP    │
                             │ UNIQUE(ord_id, law_id, method)│
                             └──────────────────────────────┘
```

## 신규 테이블

### law_revision_reasons

법령의 제개정이유/개정문 캐시. 법제처 API에서 조회한 원본을 보존한다.

```sql
CREATE TABLE law_revision_reasons (
    id SERIAL PRIMARY KEY,
    law_id INTEGER NOT NULL REFERENCES laws(id) ON DELETE CASCADE,
    law_mst VARCHAR(100),                 -- 법령일련번호 (조회 시점)
    revision_reason TEXT,                 -- 제개정이유내용 (전문)
    amendment_content TEXT,               -- 개정문내용 (전문)
    extracted_articles JSONB,             -- 개정문에서 추출한 조문번호 목록
    fetched_at TIMESTAMP NOT NULL,        -- API 조회 시점
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (law_id)
);

CREATE INDEX ix_law_revision_reasons_law_id ON law_revision_reasons(law_id);
```

**설계 근거**:
- law_id당 1건 (UNIQUE) — 최신 개정 정보만 캐시
- 법령 동기화 시 law_mst가 변경되면 갱신
- extracted_articles 예시: `["제10조의2", "제22조의2", "제30조"]`

### revision_detection_results

3가지 방식의 판별 결과를 통합 저장. 탭 비교 뷰에 사용.

```sql
CREATE TABLE revision_detection_results (
    id SERIAL PRIMARY KEY,
    ordinance_id INTEGER NOT NULL REFERENCES ordinances(id) ON DELETE CASCADE,
    law_id INTEGER NOT NULL REFERENCES laws(id) ON DELETE CASCADE,
    detection_method VARCHAR(30) NOT NULL, -- 'A_PROCLAIMED_DATE' | 'B_ARTICLE_CHANGE' | 'C_REVISION_REASON'
    needs_revision BOOLEAN NOT NULL,
    detail JSONB,                          -- 방법별 상세 정보
    detected_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (ordinance_id, law_id, detection_method)
);

CREATE INDEX ix_rdr_ordinance_id ON revision_detection_results(ordinance_id);
CREATE INDEX ix_rdr_detection_method ON revision_detection_results(detection_method);
```

**detail JSON 예시**:

탭A:
```json
{
  "law_proclaimed_date": "2026-01-15",
  "ordinance_enacted_date": "2024-03-01",
  "days_diff": 685
}
```

탭B:
```json
{
  "changed_articles": ["제3조", "제5조"],
  "mapped_articles": ["제3조"],
  "change_types": {"제3조": "updated", "제5조": "created"}
}
```

탭C:
```json
{
  "extracted_articles": ["제10조의2", "제22조의2"],
  "mapped_overlap": ["제10조의2"],
  "revision_reason_summary": "소아ㆍ청소년환자 의료서비스..."
}
```

## 기존 테이블 변경

### articles — 필드 추가

```sql
ALTER TABLE articles
    ADD COLUMN revision_type_detail VARCHAR(50),  -- 조문제개정유형 (신설/일부개정/전부개정)
    ADD COLUMN change_flag VARCHAR(5);            -- 조문변경여부 (Y/N)
```

## 마이그레이션 계획

1. `YYYYMMDD_add_law_revision_reasons.py`: law_revision_reasons 테이블 생성
2. `YYYYMMDD_add_revision_detection_results.py`: revision_detection_results 테이블 생성
3. `YYYYMMDD_add_article_revision_fields.py`: articles에 revision_type_detail, change_flag 추가
