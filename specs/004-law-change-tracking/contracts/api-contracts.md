# API Contracts: 개정법령 변경이력 관리

**Feature**: [spec.md](../spec.md) | **Date**: 2026-02-27

## Base URL

`/api/v1`

---

## 1. Law Changes (법령 변경 기록) - 읽기 전용

> law_changes는 감지 로그 전용. approve/reject 엔드포인트 **제거**.

### GET /law-changes

법령 변경 기록 목록 조회 (페이지네이션, 필터링).

**Query Parameters**:
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| page | int | N (default: 1) | 페이지 번호 |
| size | int | N (default: 20) | 페이지 크기 (max: 100) |
| api_status | string | N | success / no_response / not_found |
| dept_name | string | N | 소관부처명 (부분 일치) |
| sync_batch_id | string | N | 동기화 배치 ID |
| sync_date | string | N | YYYY-MM-DD 동기화 일자 |
| search | string | N | 법령명 검색 (부분 일치) |
| revision_type | string | N | 제개정구분 필터 |

**Response** `200`:
```json
{
  "total": 150,
  "page": 1,
  "size": 20,
  "items": [
    {
      "id": 1,
      "law_id": 100,
      "law_name": "국가공무원법",
      "law_type": "법률",
      "revision_type": "일부개정",
      "sync_date": "2026-02-27T09:00:00",
      "sync_batch_id": "SYNC-20260227-001",
      "api_status": "success",
      "api_message": null,
      "old_values": {
        "proclaimed_date": "2025-01-01",
        "enforced_date": "2025-04-01"
      },
      "new_values": {
        "proclaimed_date": "2026-02-15",
        "enforced_date": "2026-08-15"
      },
      "dept_name": "인사혁신처",
      "dept_code": 1740000,
      "created_at": "2026-02-27T09:05:00"
    }
  ]
}
```

---

### GET /law-changes/{change_id}

법령 변경 상세 조회.

**Response** `200`: 단일 LawChange 객체 (위와 동일 구조)

**Response** `404`: `{"detail": "변경 이력을 찾을 수 없습니다."}`

---

### GET /law-changes/stats

법령 변경 통계.

**Query Parameters**:
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| sync_date | string | N | YYYY-MM-DD 필터 |

**Response** `200`:
```json
{
  "total": 500,
  "by_api_status": {
    "success": 450,
    "no_response": 30,
    "not_found": 20
  },
  "by_dept": [
    {"dept_name": "법무부", "total": 45},
    {"dept_name": "행정안전부", "total": 38}
  ]
}
```

---

### GET /law-changes/export

Excel 내보내기. 현재 필터 조건 적용.

**Query Parameters**: GET /law-changes와 동일 (page/size 제외)

**Response** `200`: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

---

### GET /law-changes/departments

변경 이력이 있는 부서 목록.

**Response** `200`:
```json
[{"dept_name": "법무부", "total": 45}]
```

---

### GET /law-changes/sync-batches

동기화 배치 목록.

**Response** `200`:
```json
[
  {
    "sync_batch_id": "SYNC-20260227-001",
    "sync_date": "2026-02-27T09:00:00",
    "total": 150,
    "success": 140,
    "no_response": 5,
    "not_found": 5
  }
]
```

---

### GET /law-changes/sync-dates

동기화 일자 목록 (드롭다운용).

**Response** `200`:
```json
[{"sync_date": "2026-02-27", "total": 150, "success": 140}]
```

---

### GET /law-changes/revision-types

제개정구분 목록 (드롭다운용).

**Response** `200`:
```json
[{"revision_type": "일부개정", "count": 80}]
```

---

### GET /law-changes/history/{law_id}

특정 법령의 변경 연혁 (페이지네이션).

**Response** `200`: GET /law-changes와 동일 구조

---

### GET /law-changes/history-summary

법령별 변경 요약.

**Response** `200`:
```json
[
  {
    "law_id": 100,
    "law_name": "국가공무원법",
    "law_type": "법률",
    "dept_name": "인사혁신처",
    "total_changes": 5,
    "last_sync_date": "2026-02-27T09:00:00"
  }
]
```

---

## 2. Ordinances - revision_status 관련 변경

### GET /ordinances/{ordinance_id}

조례 상세 조회. **부서 담당자가 "검토대기" 조례를 열람하면 자동으로 "검토중" 전환.**

**Side effect** (FR-010):
- 조건: `revision_status == "검토대기"` AND 요청자가 해당 부서 소속 담당자
- 결과: `revision_status → "검토중"`
- 응답에 변경된 상태 반영

**Response** `200`:
```json
{
  "id": 1,
  "code": "ORD-001",
  "name": "서울특별시 자치법규",
  "revision_status": "검토중",
  "...": "기존 필드 유지"
}
```

---

### POST /ordinances/{ordinance_id}/clear-revision

**신규** - 관리자 전용. "개정확정" → null (빨간불 수동 해제).

**Authorization**: 관리자만 가능

**Request**: 없음 (body 불필요)

**Response** `200`:
```json
{"success": true, "message": "개정확정 상태가 해제되었습니다."}
```

**Response** `400`:
```json
{"detail": "개정확정 상태의 조례만 해제할 수 있습니다."}
```

---

## 3. Ordinance Reviews - 승인 후 데이터 처리

### POST /ordinances/{ordinance_id}/reviews

검토의견 생성 (부서 담당자).

**Request**:
```json
{
  "review_content": "해당 조례 제5조가 상위법령 개정 내용에 영향을 받습니다.",
  "review_result": "개정필요"
}
```

**Validation**: `review_result`는 `"개정필요"` 또는 `"개정불필요"` 만 허용.

**Response** `201`:
```json
{
  "id": 1,
  "ordinance_id": 100,
  "review_content": "...",
  "review_result": "개정필요",
  "approval_status": "pending",
  "created_at": "2026-02-27T10:00:00"
}
```

---

### POST /ordinances/reviews/{review_id}/approve

검토의견 승인 (관리자). **승인 시 ordinance.revision_status 자동 변경.**

**Authorization**: 관리자만 가능

**Request**:
```json
{
  "approval_note": "검토 결과를 확인했습니다."
}
```

**Side effects** (FR-012, FR-013):
| review_result | revision_status 변경 |
|---------------|---------------------|
| 개정필요 | → "개정확정" |
| 개정불필요 | → null |

**Response** `200`:
```json
{
  "success": true,
  "message": "검토의견이 승인되었습니다.",
  "ordinance_revision_status": "개정확정"
}
```

---

### POST /ordinances/reviews/{review_id}/reject

검토의견 반려 (관리자). **반려 시 ordinance.revision_status → "검토대기".**

**Authorization**: 관리자만 가능

**Request**:
```json
{
  "approval_note": "검토 근거가 부족합니다. 재검토 바랍니다."
}
```

**Side effect** (FR-014):
- ordinance.revision_status → "검토대기"

**Response** `200`:
```json
{
  "success": true,
  "message": "검토의견이 반려되었습니다.",
  "ordinance_revision_status": "검토대기"
}
```

---

## 4. Removed Endpoints

> 다음 엔드포인트는 spec 변경에 따라 **제거** 대상:

| Method | Path | Reason |
|--------|------|--------|
| POST | /law-changes/{change_id}/approve | law_changes 승인 워크플로우 제거 |
| POST | /law-changes/{change_id}/reject | law_changes 반려 워크플로우 제거 |
| POST | /law-changes/bulk-approve | law_changes 일괄 승인 제거 |
| POST | /law-changes/bulk-reject | law_changes 일괄 반려 제거 |

---

## 5. Error Responses (공통)

| Status | Body | Description |
|--------|------|-------------|
| 400 | `{"detail": "..."}` | 유효성 검증 실패 |
| 401 | `{"detail": "인증이 필요합니다."}` | 미인증 |
| 403 | `{"detail": "권한이 없습니다."}` | 권한 부족 |
| 404 | `{"detail": "...을 찾을 수 없습니다."}` | 리소스 없음 |
| 500 | `{"detail": "서버 오류가 발생했습니다."}` | 서버 에러 |
