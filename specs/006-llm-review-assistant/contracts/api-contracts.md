# API Contracts: 006-llm-review-assistant

**Date**: 2026-02-28
**Base Path**: `/api/v1`

## 엔드포인트 목록

| Method | Path | 인증 | 설명 | 상태 |
|--------|------|------|------|------|
| POST | `/ordinances/{id}/ai-summary` | JWT | AI 개정내용 요약 생성 | **신규** |
| POST | `/ordinances/{id}/ai-draft` | JWT | AI 검토의견 초안 생성 | **신규** |
| GET | `/ordinances/{id}/ai-results` | JWT | AI 분석 결과 조회 | **신규** |
| GET | `/admin/ai-analytics` | JWT(Admin) | AI 분석 이력/통계 | **신규** |

---

## POST /ordinances/{id}/ai-summary (신규)

**인증**: Bearer JWT
**설명**: 조례의 상위법령 제개정이유를 LLM이 분석하여 요약을 생성한다.
**1회 실행 원칙**: 이미 결과가 있으면 409 반환. 실패 건은 1회 재시도 허용.

### Request

없음 (경로의 ordinance_id로 자동 판별)

### Response 200

```json
{
  "ordinance_id": 1,
  "law_id": 10,
  "analysis_type": "summary",
  "summary": "### 주요 변경사항\n- 제10조의2: 소아ㆍ청소년환자 상담 업무 추가\n- 제22조의2: 응급의료정보통신망 이용 근거 마련\n\n### 조례 영향\n- 관련 조문: 제5조 (구급활동 지원)\n- 영향도: 조례 개정 검토 필요",
  "model_name": "claude-3-5-sonnet",
  "token_usage": 1250,
  "ai_generated_at": "2026-02-28T10:00:00Z"
}
```

### Error Responses

| 상태 | 조건 | 응답 |
|------|------|------|
| 404 | 조례 미발견 | `{"detail": "조례를 찾을 수 없습니다"}` |
| 409 | 이미 분석 완료 | `{"detail": "이미 AI 요약이 생성되었습니다", "existing_result_id": 5}` |
| 422 | 제개정이유 없음 | `{"detail": "제개정이유 데이터가 없어 AI 분석을 수행할 수 없습니다"}` |
| 502 | LLM API 오류 | `{"detail": "AI 요약을 생성할 수 없습니다. 직접 검토해 주세요"}` |
| 504 | LLM 타임아웃 | `{"detail": "AI 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요"}` |

---

## POST /ordinances/{id}/ai-draft (신규)

**인증**: Bearer JWT
**설명**: LLM이 검토의견 초안(결과+의견)을 생성한다.
**1회 실행 원칙**: 동일.

### Response 200

```json
{
  "ordinance_id": 1,
  "law_id": 10,
  "analysis_type": "review_draft",
  "draft": {
    "review_result": "개정필요",
    "review_content": "「119구조ㆍ구급에 관한 법률」 일부개정(2026.1.15)으로 제10조의2에 소아ㆍ청소년환자 상담 업무가 추가되었습니다. 본 조례 제5조(구급활동 지원)에서 해당 업무를 반영하도록 개정이 필요합니다."
  },
  "model_name": "claude-3-5-sonnet",
  "token_usage": 980,
  "ai_generated_at": "2026-02-28T10:01:00Z"
}
```

### Error Responses

동일 (POST /ai-summary와 같은 에러 코드)

---

## GET /ordinances/{id}/ai-results (신규)

**인증**: Bearer JWT
**설명**: 해당 조례의 AI 분석 결과(요약+초안)를 조회. 없으면 빈 배열.

### Response 200

```json
{
  "ordinance_id": 1,
  "results": [
    {
      "id": 5,
      "law_id": 10,
      "law_name": "119구조ㆍ구급에 관한 법률",
      "analysis_type": "summary",
      "response_text": "...",
      "model_name": "claude-3-5-sonnet",
      "status": "SUCCESS",
      "created_at": "2026-02-28T10:00:00Z"
    },
    {
      "id": 6,
      "law_id": 10,
      "law_name": "119구조ㆍ구급에 관한 법률",
      "analysis_type": "review_draft",
      "response_text": "...",
      "model_name": "claude-3-5-sonnet",
      "status": "SUCCESS",
      "created_at": "2026-02-28T10:01:00Z"
    }
  ]
}
```

---

## GET /admin/ai-analytics (신규)

**인증**: Bearer JWT (관리자 전용)
**설명**: AI 분석 이력 통계 (US4).

### Query Parameters

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| start_date | date | 30일 전 | 시작일 |
| end_date | date | 오늘 | 종료일 |

### Response 200

```json
{
  "period": {"start": "2026-02-01", "end": "2026-02-28"},
  "summary_count": 45,
  "draft_count": 38,
  "draft_adoption_rate": 0.34,
  "draft_modified_rate": 0.55,
  "draft_unused_rate": 0.11,
  "average_token_usage": 1150,
  "model_breakdown": {
    "claude-3-5-sonnet": 83
  }
}
```
