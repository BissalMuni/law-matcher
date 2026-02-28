# API Contracts: 005-revision-detection-tabs

**Date**: 2026-02-28
**Base Path**: `/api/v1`

## 엔드포인트 목록

### 기존 (변경 없음)

| Method | Path | 인증 | 설명 | 상태 |
|--------|------|------|------|------|
| GET | `/ordinances/{id}/parent-laws` | JWT | 탭A용 상위법령 목록 | 구현됨 |
| GET | `/articles` | JWT | 탭B용 조문 목록 | 구현됨 |
| GET | `/articles/{id}/history` | JWT | 탭B용 조문 변경 이력 | 구현됨 |
| GET | `/articles/revision-needed` | JWT | 탭B용 개정 필요 목록 | 구현됨 |

### 신규

| Method | Path | 인증 | 설명 | 상태 |
|--------|------|------|------|------|
| GET | `/laws/{id}/revision-reason` | JWT | 탭C용 제개정이유/개정문 조회 | **신규** |
| GET | `/ordinances/{id}/detection-results` | JWT | 3탭 판별 결과 조회 | **신규** |
| POST | `/ordinances/{id}/detect` | JWT | 판별 실행 (3방식 동시) | **신규** |

---

## GET /laws/{id}/revision-reason (신규)

**인증**: Bearer JWT
**설명**: 법령의 제개정이유내용과 개정문내용을 조회. DB 캐시 우선, 없으면 법제처 API 호출.

### Response 200

```json
{
  "law_id": 1,
  "law_name": "119구조ㆍ구급에 관한 법률",
  "revision_reason": "[일부개정]\n\n◇ 개정이유 및 주요내용\n\n전국 어디서든...",
  "amendment_content": "119구조ㆍ구급에 관한 법률 일부를 다음과 같이 개정한다.\n\n제10조의2제1항 중...",
  "extracted_articles": ["제10조의2", "제22조의2", "제30조"],
  "fetched_at": "2026-02-28T10:00:00Z"
}
```

### Error Responses

| 상태 | 조건 | 응답 |
|------|------|------|
| 404 | 법령 미발견 | `{"detail": "법령을 찾을 수 없습니다"}` |
| 502 | 법제처 API 오류 | `{"detail": "법제처 서버에서 제개정이유를 가져올 수 없습니다"}` |
| 204 | 제개정이유 없음 | `{"detail": "제개정이유 데이터가 없습니다 (제정 법령 등)"}` |

---

## GET /ordinances/{id}/detection-results (신규)

**인증**: Bearer JWT
**설명**: 조례에 대한 3탭 판별 결과를 한번에 조회.

### Response 200

```json
{
  "ordinance_id": 1,
  "ordinance_name": "○○시 건축 조례",
  "results": [
    {
      "law_id": 10,
      "law_name": "건축법",
      "tab_a": {
        "needs_revision": true,
        "law_proclaimed_date": "2026-01-15",
        "ordinance_enacted_date": "2024-03-01",
        "days_diff": 685
      },
      "tab_b": {
        "needs_revision": true,
        "changed_articles": ["제3조", "제5조"],
        "mapped_overlap": ["제3조"]
      },
      "tab_c": {
        "needs_revision": true,
        "extracted_articles": ["제3조", "제5조", "제10조"],
        "mapped_overlap": ["제3조"],
        "has_revision_reason": true
      }
    }
  ]
}
```

---

## POST /ordinances/{id}/detect (신규)

**인증**: Bearer JWT
**설명**: 3가지 방식으로 판별을 실행하고 결과를 DB에 저장.

### Request

```json
{
  "methods": ["A", "B", "C"]    // 선택적. 생략 시 전체
}
```

### Response 200

```json
{
  "ordinance_id": 1,
  "results_saved": 3,
  "message": "판별 완료"
}
```
