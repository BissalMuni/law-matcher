# Data Model: 006-llm-review-assistant

**Date**: 2026-03-02 (updated)
**Input**: spec.md (post-clarification v2), research.md

## ERD

```
┌──────────────────────┐     ┌───────────────────────────────────┐
│     ordinances       │     │       llm_analysis_results         │
├──────────────────────┤     ├───────────────────────────────────┤
│ id          PK       │◄────│ ordinance_id       FK             │
│ name                 │     │ law_id             FK       ──────┼──► laws
│ ...                  │     │ law_proclaimed_date DATE           │
└──────────┬───────────┘     │ status             VARCHAR        │
           │                 │ input_hash         CHAR(64)       │
           │                 │ prompt_text        TEXT            │
           │                 │ summary_text       TEXT            │
           │                 │ review_draft_text  TEXT            │
           │                 │ review_draft_result VARCHAR       │
           │                 │ provider_name      VARCHAR        │
           │                 │ model_name         VARCHAR        │
           │                 │ token_usage        JSONB          │
           │                 │ error_message      TEXT            │
           │                 │ created_at         TIMESTAMP      │
           │                 │ UQ(ord, law, proclaimed_date)     │
           │                 └───────────────────────────────────┘
           │
           │     ┌───────────────────────────────────┐
           └────►│       ordinance_reviews            │
                 ├───────────────────────────────────┤
                 │ id                PK              │
                 │ ordinance_id      FK              │
                 │ review_content    TEXT             │
                 │ review_result     VARCHAR          │
                 │ is_ai_generated   BOOLEAN     NEW  │
                 │ ai_modified       BOOLEAN     NEW  │
                 │ ai_analysis_id    FK          NEW ─┼──► llm_analysis_results
                 │ ...                                │
                 └───────────────────────────────────┘

┌───────────────────────────────────┐
│         llm_providers             │
├───────────────────────────────────┤
│ id               PK               │
│ provider_name    VARCHAR UNIQUE    │
│ display_name     VARCHAR           │
│ model_name       VARCHAR           │
│ api_key_env_name VARCHAR           │
│ is_active        BOOLEAN           │
│ rate_limit_per_minute INTEGER      │
│ created_at       TIMESTAMP         │
│ updated_at       TIMESTAMP         │
└───────────────────────────────────┘
```

## 신규 테이블

### llm_providers

LLM 프로바이더/모델 DB 관리. 관리자가 설정 탭에서 모델 변경, 활성 전환 가능.

```sql
CREATE TABLE llm_providers (
    id SERIAL PRIMARY KEY,
    provider_name VARCHAR(50) NOT NULL UNIQUE,     -- 'claude' | 'chatgpt' | 'gemini'
    display_name VARCHAR(100) NOT NULL,             -- 'Claude' | 'ChatGPT' | 'Gemini'
    model_name VARCHAR(100) NOT NULL,               -- 'claude-sonnet-4-6' 등
    api_key_env_name VARCHAR(100) NOT NULL,          -- 'ANTHROPIC_API_KEY' 등
    is_active BOOLEAN NOT NULL DEFAULT FALSE,        -- 활성 프로바이더 (1개만 active)
    rate_limit_per_minute INTEGER NOT NULL DEFAULT 10,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**초기 데이터**:

```sql
INSERT INTO llm_providers (provider_name, display_name, model_name, api_key_env_name, is_active) VALUES
('claude', 'Claude', 'claude-sonnet-4-6', 'ANTHROPIC_API_KEY', TRUE),
('chatgpt', 'ChatGPT', 'gpt-4o', 'OPENAI_API_KEY', FALSE),
('gemini', 'Gemini', 'gemini-2.0-flash', 'GOOGLE_AI_API_KEY', FALSE);
```

**설계 근거**:
- `provider_name` UNIQUE: 프로바이더별 1 레코드
- `api_key_env_name`: API 키는 환경변수로만 관리 (DB에 키 저장하지 않음, VI. 보안)
- `is_active`: 활성 프로바이더 선택. 동시에 1개만 active 권장 (서비스에서 검증)
- `rate_limit_per_minute`: 시스템 전체 분당 호출 제한 (활성 프로바이더 기준)

### llm_analysis_results

통합 AI 분석 결과 저장. 1회 호출로 요약+초안을 동시 생성하여 단일 레코드에 저장.

```sql
CREATE TABLE llm_analysis_results (
    id SERIAL PRIMARY KEY,
    ordinance_id INTEGER NOT NULL REFERENCES ordinances(id) ON DELETE CASCADE,
    law_id INTEGER NOT NULL REFERENCES laws(id) ON DELETE CASCADE,
    law_proclaimed_date DATE,                        -- 법령 버전 구분 (FR-005a)
    status VARCHAR(20) NOT NULL DEFAULT 'pending',   -- 'pending' | 'success' | 'failed'
    input_hash CHAR(64) NOT NULL,                    -- SHA-256 (입력 데이터만, 프롬프트 제외)
    prompt_text TEXT NOT NULL,                        -- LLM에 전송한 전체 프롬프트 (I. 데이터 무결성)
    summary_text TEXT,                                -- AI 개정내용 요약
    review_draft_text TEXT,                           -- AI 검토의견 초안 내용
    review_draft_result VARCHAR(20),                  -- '개정필요' | '개정불필요'
    provider_name VARCHAR(50) NOT NULL,               -- 사용된 프로바이더 (claude/chatgpt/gemini)
    model_name VARCHAR(100) NOT NULL,                 -- 사용된 모델명
    token_usage JSONB,                                -- {"input_tokens": N, "output_tokens": M}
    error_message TEXT,                               -- 실패 시 에러 메시지
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (ordinance_id, law_id, law_proclaimed_date)
);

CREATE INDEX ix_llm_analysis_ordinance ON llm_analysis_results(ordinance_id);
CREATE INDEX ix_llm_analysis_law ON llm_analysis_results(law_id);
CREATE INDEX ix_llm_analysis_status ON llm_analysis_results(status);
```

**설계 근거**:
- **통합 저장**: `summary_text` + `review_draft_text` + `review_draft_result`를 단일 레코드에 저장 (1회 통합 호출 반영)
- **UNIQUE(ordinance_id, law_id, law_proclaimed_date)**: 법령 버전별 1회 실행 원칙 보장 (Constitution VIII)
- **law_proclaimed_date**: 법령 재동기화로 새 공포일자 감지 시 새 레코드 허용 (FR-005a)
- **input_hash**: 입력 데이터만 해시 (제개정이유 + 개정문 + 조례 텍스트). 프롬프트 변경 시 재분석 허용
- **prompt_text**: AI 입력 보존 (Constitution I, VIII)
- **status**: `pending`(처리 중) → `success`(완료) / `failed`(실패). 실패 건은 1회 재시도 허용
- **token_usage**: JSONB로 유연한 구조 (프로바이더별 차이 수용)

### input_hash 계산

```python
import hashlib

def compute_input_hash(revision_reason: str, amendment_content: str, ordinance_name: str) -> str:
    """입력 데이터만 해시 (프롬프트 제외)"""
    input_data = f"{revision_reason or ''}\n{amendment_content or ''}\n{ordinance_name or ''}"
    return hashlib.sha256(input_data.encode('utf-8')).hexdigest()
```

## 기존 테이블 변경

### ordinance_reviews — AI 메타데이터 필드 추가

```sql
ALTER TABLE ordinance_reviews
    ADD COLUMN is_ai_generated BOOLEAN DEFAULT FALSE,
    ADD COLUMN ai_modified BOOLEAN DEFAULT FALSE,
    ADD COLUMN ai_analysis_id INTEGER REFERENCES llm_analysis_results(id) ON DELETE SET NULL;
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `is_ai_generated` | BOOLEAN | AI 초안을 기반으로 작성되었는지 여부 |
| `ai_modified` | BOOLEAN | 담당자가 AI 초안을 수정했는지 (FALSE=그대로 제출) |
| `ai_analysis_id` | INTEGER FK | 참조한 AI 분석 결과 ID (추적용) |

**추적 로직**:
- AI 초안 기반으로 제출 시: `is_ai_generated=TRUE`
- 내용 수정 없이 그대로 제출: `ai_modified=FALSE` (채택률 측정용)
- 내용 수정 후 제출: `ai_modified=TRUE`
- 수동 작성 (AI 미사용): `is_ai_generated=FALSE`, `ai_modified=FALSE`

## 마이그레이션 계획

1. `YYYYMMDD_add_llm_providers.py`: llm_providers 테이블 생성 + 초기 데이터 삽입
2. `YYYYMMDD_add_llm_analysis_results.py`: llm_analysis_results 테이블 생성
3. `YYYYMMDD_add_ai_fields_to_reviews.py`: ordinance_reviews에 AI 필드 추가
