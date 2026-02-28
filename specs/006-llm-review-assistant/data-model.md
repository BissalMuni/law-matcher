# Data Model: 006-llm-review-assistant

**Date**: 2026-02-28
**Input**: spec.md, research.md

## ERD

```
┌──────────────────────┐     ┌──────────────────────────────┐
│     ordinances       │     │    llm_analysis_results       │
├──────────────────────┤     ├──────────────────────────────┤
│ id          PK       │◄────│ ordinance_id    FK            │
│ name                 │     │ law_id          FK            │
│ ...                  │     │ analysis_type   VARCHAR       │
└──────────┬───────────┘     │ input_hash      CHAR(64)     │
           │                 │ prompt          TEXT           │
           │                 │ response_text   TEXT           │
           │                 │ model_name      VARCHAR       │
           │                 │ token_usage     INTEGER       │
           │                 │ created_at      TIMESTAMP     │
           │                 │ UNIQUE(ord, law, type)        │
           │                 └──────────────────────────────┘
           │
           │     ┌──────────────────────────────┐
           └────►│    ordinance_reviews          │
                 ├──────────────────────────────┤
                 │ id              PK            │
                 │ ordinance_id    FK            │
                 │ review_content  TEXT          │
                 │ review_result   VARCHAR       │
                 │ is_ai_generated BOOLEAN  NEW  │
                 │ ai_modified     BOOLEAN  NEW  │
                 │ ai_model        VARCHAR  NEW  │
                 │ ai_generated_at TIMESTAMP NEW │
                 │ ...                           │
                 └──────────────────────────────┘
```

## 신규 테이블

### llm_analysis_results

LLM 분석 결과 저장. 동일 대상에 대해 **1회만 수행** (Constitution VIII).

```sql
CREATE TABLE llm_analysis_results (
    id SERIAL PRIMARY KEY,
    ordinance_id INTEGER NOT NULL REFERENCES ordinances(id) ON DELETE CASCADE,
    law_id INTEGER NOT NULL REFERENCES laws(id) ON DELETE CASCADE,
    analysis_type VARCHAR(50) NOT NULL,    -- 'summary' | 'review_draft'
    input_hash CHAR(64) NOT NULL,          -- SHA-256 of input data (변경 감지용)
    prompt TEXT NOT NULL,                   -- LLM에 전송한 프롬프트 (I. 데이터 무결성)
    response_text TEXT NOT NULL,            -- LLM 응답 원문 (I. 데이터 무결성)
    model_name VARCHAR(100),               -- 사용된 모델명
    token_usage INTEGER,                    -- 토큰 사용량
    status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS', -- 'SUCCESS' | 'FAILED'
    error_message TEXT,                     -- 실패 시 에러 메시지
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (ordinance_id, law_id, analysis_type)
);

CREATE INDEX ix_llm_analysis_ordinance ON llm_analysis_results(ordinance_id);
CREATE INDEX ix_llm_analysis_type ON llm_analysis_results(analysis_type);
```

**설계 근거**:
- UNIQUE(ordinance_id, law_id, analysis_type): 1회 실행 원칙 DB 레벨 보장
- input_hash: 법령 재동기화 시 제개정이유가 변경되면 새 분석 허용 (FR-005a)
- prompt + response_text: AI 입출력 모두 보존 (Constitution I, VIII)
- status: 실패 건은 재시도 1회 허용 (Edge case)

### input_hash 계산

```python
import hashlib
input_data = f"{law.revision_reason}{ordinance.name}{ordinance.enacted_date}"
input_hash = hashlib.sha256(input_data.encode()).hexdigest()
```

법령 재동기화로 revision_reason이 변경되면 hash가 달라져 새 분석 가능.

## 기존 테이블 변경

### ordinance_reviews — AI 메타데이터 필드 추가

```sql
ALTER TABLE ordinance_reviews
    ADD COLUMN is_ai_generated BOOLEAN DEFAULT FALSE,
    ADD COLUMN ai_modified BOOLEAN DEFAULT FALSE,
    ADD COLUMN ai_model VARCHAR(100),
    ADD COLUMN ai_generated_at TIMESTAMP;
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `is_ai_generated` | BOOLEAN | AI가 초안을 생성했는지 여부 |
| `ai_modified` | BOOLEAN | 담당자가 AI 초안을 수정했는지 여부 |
| `ai_model` | VARCHAR | 사용된 모델명 (예: claude-3-5-sonnet) |
| `ai_generated_at` | TIMESTAMP | AI 초안 생성 시점 |

## 마이그레이션 계획

1. `YYYYMMDD_add_llm_analysis_results.py`: llm_analysis_results 테이블 생성
2. `YYYYMMDD_add_ai_fields_to_reviews.py`: ordinance_reviews에 AI 필드 추가
