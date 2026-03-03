# API Contracts: 006-llm-review-assistant

**Date**: 2026-03-02 (updated)
**Base Path**: `/api/v1`

## Endpoint Summary

| Method | Path | Auth | Description | Status |
|--------|------|------|-------------|--------|
| POST | `/ordinances/{id}/ai-analyze` | JWT | AI 통합 분석 (요약+초안 동시 생성) | **NEW** |
| GET | `/ordinances/{id}/ai-results` | JWT | AI 분석 결과 조회 | **NEW** |
| GET | `/admin/llm-providers` | JWT(Admin) | LLM 프로바이더 목록 조회 | **NEW** |
| PATCH | `/admin/llm-providers/{provider_id}` | JWT(Admin) | LLM 프로바이더 설정 변경 | **NEW** |
| GET | `/admin/ai-analytics` | JWT(Admin) | AI 분석 이력/통계 | **NEW** |

---

## POST /ordinances/{id}/ai-analyze (NEW)

**Auth**: Bearer JWT
**Description**: 1회 통합 호출로 개정내용 요약과 검토의견 초안을 동시에 생성한다.
**Processing**: 동기 처리 + 30초 타임아웃. 클라이언트에서 로딩 스피너 표시.
**1회 실행 원칙**: 이미 성공한 결과가 있으면 409 반환. 실패(`status=failed`)한 건은 1회 재시도 허용.

### Request Body

```json
{
  "law_id": 10
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| law_id | integer | YES | 분석 대상 상위법령 ID |

### Response 200

```json
{
  "id": 5,
  "ordinance_id": 1,
  "law_id": 10,
  "law_proclaimed_date": "2026-01-15",
  "status": "success",
  "summary_text": "### 주요 변경사항\n- 제10조의2: 소아ㆍ청소년환자 상담 업무 추가\n- 제22조의2: 응급의료정보통신망 이용 근거 마련\n\n### 조례 영향\n- 관련 조문: 제5조 (구급활동 지원)\n- 영향도: 조례 개정 검토 필요",
  "review_draft_text": "「119구조ㆍ구급에 관한 법률」 일부개정(2026.1.15)으로 제10조의2에 소아ㆍ청소년환자 상담 업무가 추가되었습니다. 본 조례 제5조(구급활동 지원)에서 해당 업무를 반영하도록 개정이 필요합니다.",
  "review_draft_result": "개정필요",
  "provider_name": "claude",
  "model_name": "claude-sonnet-4-6",
  "token_usage": {"input_tokens": 2500, "output_tokens": 800},
  "created_at": "2026-03-02T10:00:00Z"
}
```

### Error Responses

| Status | Condition | Response |
|--------|-----------|----------|
| 400 | law_id 미전송 또는 매핑 미존재 | `{"detail": "해당 법령과 조례의 연결 정보를 찾을 수 없습니다"}` |
| 404 | 조례 미발견 | `{"detail": "조례를 찾을 수 없습니다"}` |
| 409 | 이미 분석 성공 완료 | `{"detail": "이미 AI 분석이 완료되었습니다", "existing_result_id": 5}` |
| 422 | 제개정이유 데이터 없음 | `{"detail": "제개정이유 데이터가 없어 AI 분석을 수행할 수 없습니다"}` |
| 429 | Rate Limit 초과 | `{"detail": "AI 분석 요청이 제한을 초과했습니다. 잠시 후 다시 시도해 주세요"}` |
| 502 | LLM API 오류 | `{"detail": "AI 분석을 수행할 수 없습니다. 직접 검토해 주세요"}` |
| 503 | 활성 프로바이더 없음/API 키 미설정 | `{"detail": "LLM API가 설정되지 않았습니다. 관리자에게 문의하세요"}` |
| 504 | LLM 타임아웃 (30초 초과) | `{"detail": "AI 분석 시간이 초과되었습니다. 다시 시도해 주세요"}` |

---

## GET /ordinances/{id}/ai-results (NEW)

**Auth**: Bearer JWT
**Description**: 해당 조례의 AI 분석 결과를 법령별로 조회. 결과 없으면 빈 배열.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| law_id | integer | (all) | 특정 법령의 결과만 조회 |

### Response 200

```json
{
  "ordinance_id": 1,
  "results": [
    {
      "id": 5,
      "law_id": 10,
      "law_name": "119구조ㆍ구급에 관한 법률",
      "law_proclaimed_date": "2026-01-15",
      "status": "success",
      "summary_text": "...",
      "review_draft_text": "...",
      "review_draft_result": "개정필요",
      "provider_name": "claude",
      "model_name": "claude-sonnet-4-6",
      "created_at": "2026-03-02T10:00:00Z"
    }
  ]
}
```

---

## GET /admin/llm-providers (NEW)

**Auth**: Bearer JWT (Admin)
**Description**: 등록된 LLM 프로바이더 목록. API 키 존재 여부만 마스킹 표시.

### Response 200

```json
{
  "providers": [
    {
      "id": 1,
      "provider_name": "claude",
      "display_name": "Claude",
      "model_name": "claude-sonnet-4-6",
      "api_key_env_name": "ANTHROPIC_API_KEY",
      "api_key_configured": true,
      "is_active": true,
      "rate_limit_per_minute": 10,
      "updated_at": "2026-03-01T00:00:00Z"
    },
    {
      "id": 2,
      "provider_name": "chatgpt",
      "display_name": "ChatGPT",
      "model_name": "gpt-4o",
      "api_key_env_name": "OPENAI_API_KEY",
      "api_key_configured": false,
      "is_active": false,
      "rate_limit_per_minute": 10,
      "updated_at": "2026-03-01T00:00:00Z"
    }
  ]
}
```

**Note**: `api_key_configured` is computed at runtime by checking `os.getenv(api_key_env_name)`. The actual key is never exposed.

---

## PATCH /admin/llm-providers/{provider_id} (NEW)

**Auth**: Bearer JWT (Admin)
**Description**: 프로바이더 모델명, 활성 상태, Rate Limit 변경.

### Request Body

```json
{
  "model_name": "claude-opus-4-6",
  "is_active": true,
  "rate_limit_per_minute": 20
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| model_name | string | NO | 변경할 모델명 |
| is_active | boolean | NO | 활성 상태 전환 |
| rate_limit_per_minute | integer | NO | 분당 호출 제한 |

### Response 200

Updated provider object (same as GET response item).

### Validation

- `is_active=true` 설정 시, 해당 프로바이더의 API 키가 환경변수에 설정되어 있어야 함
- 기존 활성 프로바이더가 있으면 자동 비활성화 (동시 1개만 active)

---

## GET /admin/ai-analytics (NEW)

**Auth**: Bearer JWT (Admin)
**Description**: AI 분석 이력 통계 (US3 P3).

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| start_date | date | 30일 전 | 시작일 |
| end_date | date | 오늘 | 종료일 |

### Response 200

```json
{
  "period": {"start": "2026-02-01", "end": "2026-03-02"},
  "total_analyses": 45,
  "success_count": 42,
  "failed_count": 3,
  "draft_adoption_rate": 0.34,
  "draft_modified_rate": 0.55,
  "draft_unused_rate": 0.11,
  "average_token_usage": {"input_tokens": 2200, "output_tokens": 750},
  "by_provider": {
    "claude": {"count": 40, "model": "claude-sonnet-4-6"},
    "chatgpt": {"count": 5, "model": "gpt-4o"}
  }
}
```

### Computation

- `draft_adoption_rate`: AI 초안 그대로 제출 비율 (`is_ai_generated=TRUE AND ai_modified=FALSE`)
- `draft_modified_rate`: AI 초안 수정 후 제출 비율 (`is_ai_generated=TRUE AND ai_modified=TRUE`)
- `draft_unused_rate`: AI 분석 후 수동 작성 비율 (분석은 했으나 review에 AI 미사용)
