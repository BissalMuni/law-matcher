# API Contracts: 002-ordinance-management

**Date**: 2026-02-28
**Base Path**: `/api/v1`

## 엔드포인트 목록

### 조회/필터 (구현됨)

| Method | Path | 인증 | 설명 | 상태 |
|--------|------|------|------|------|
| GET | `/ordinances` | JWT | 조례 목록 (필터+페이지네이션) | 구현됨 |
| GET | `/ordinances/{id}` | JWT | 조례 상세 | 구현됨 |
| GET | `/ordinances/departments` | JWT | 부서 목록 (필터 드롭다운용) | 구현됨 |
| GET | `/ordinances/revision-types` | JWT | 제개정구분 목록 | 구현됨 |
| GET | `/ordinances/export` | JWT | 엑셀 내보내기 | 구현됨 |

### 등록/동기화 (구현됨)

| Method | Path | 인증 | 설명 | 상태 |
|--------|------|------|------|------|
| POST | `/ordinances/create` | JWT | 수동 조례 등록 | 구현됨 |
| POST | `/ordinances/search-api` | JWT | 법제처 API 검색 | 구현됨 |
| POST | `/ordinances/register-from-api` | JWT | API 검색결과 등록 | 구현됨 |
| POST | `/ordinances/sync` | JWT+AdminPW | 법제처 일괄 동기화 | 구현됨 |
| POST | `/ordinances/upload` | JWT+AdminPW | 부서 일괄 배정 (엑셀) | 구현됨 |
| POST | `/ordinances/update-all-info` | JWT | 전체 조례 정보 갱신 | 구현됨 |

### 상위법령 관리 (구현됨)

| Method | Path | 인증 | 설명 | 상태 |
|--------|------|------|------|------|
| GET | `/ordinances/{id}/parent-laws` | JWT | 상위법령 목록 | 구현됨 |
| POST | `/ordinances/{id}/parent-laws` | JWT | 상위법령 추가 | 구현됨 |
| PUT | `/ordinances/parent-laws/{id}` | JWT | 상위법령 수정 | 구현됨 |
| DELETE | `/ordinances/parent-laws/{id}` | JWT | 상위법령 삭제 | 구현됨 |
| POST | `/ordinances/{id}/no-parent-law` | JWT | 상위법령 없음 설정 | 구현됨 |
| DELETE | `/ordinances/{id}/no-parent-law` | JWT | 상위법령 없음 해제 | 구현됨 |

### 검토이력 (구현됨)

| Method | Path | 인증 | 설명 | 상태 |
|--------|------|------|------|------|
| GET | `/ordinances/{id}/reviews` | JWT | 검토이력 목록 | 구현됨 |
| POST | `/ordinances/{id}/reviews` | JWT | 검토의견 작성 | 구현됨 |
| PUT | `/ordinances/reviews/{id}` | JWT | 검토의견 수정 | 구현됨 |
| DELETE | `/ordinances/reviews/{id}` | JWT | 검토의견 삭제 | 구현됨 |
| POST | `/ordinances/reviews/{id}/approve` | JWT(Admin) | 검토의견 승인/반려 | 구현됨 |
| GET | `/ordinances/reviews-all` | JWT(Admin) | 전체 검토 대시보드 | 구현됨 |

---

## 변경 사항 (보강 필요)

### GET /ordinances — status 필터 추가

기존 필터 파라미터에 `status` 추가:

```
GET /ordinances?status=ACTIVE&page=1&size=20
```

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| status | string | `ACTIVE` | `ACTIVE` \| `ABOLISHED` \| `EXCLUDED` \| `ALL` |

- 기본값 `ACTIVE`: 폐지/제외 조례를 목록에서 숨김
- `ALL`: 모든 상태 표시 (관리자 전용)

### POST /ordinances/sync — 폐지 감지 반영

동기화 응답에 폐지 건수 추가:

```json
{
  "success": true,
  "total_processed": 500,
  "created": 10,
  "updated": 480,
  "abolished": 3,
  "failed": 7
}
```

---

## 기존 API 계약 (주요 엔드포인트)

### GET /ordinances

**인증**: Bearer JWT
**역할 제어**: 부서 사용자는 소속 부서만, 관리자는 전체

#### Query Parameters

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| page | int | 1 | 페이지 번호 |
| size | int | 20 | 페이지 크기 |
| search | string | - | 조례명 검색 |
| category | string | - | 조례/규칙 |
| department | string | - | 부서명 |
| parent_law_status | string | - | connected/confirmed_none/no_mapping |
| needs_revision | int | - | 0/1 |
| revision_type | string | - | 제개정구분 |
| review_result | string | - | 개정필요/개정불필요/검토중/보류/미검토 |
| exclude_other_law_revision | bool | false | 타법개정 제외 |

#### Response 200

```json
{
  "total": 150,
  "page": 1,
  "size": 20,
  "items": [
    {
      "id": 1,
      "code": "ORD-001",
      "name": "○○시 건축 조례",
      "category": "조례",
      "department": "건축과",
      "enacted_date": "2020-01-01",
      "status": "ACTIVE",
      "needs_revision": 1,
      "revision_type": "일부개정",
      "parent_law_count": 3,
      "latest_review_result": "검토중"
    }
  ]
}
```

### GET /ordinances/{id}

#### Response 200

```json
{
  "id": 1,
  "code": "ORD-001",
  "name": "○○시 건축 조례",
  "category": "조례",
  "department": "건축과",
  "department_id": 5,
  "enacted_date": "2020-01-01",
  "enforced_date": "2020-03-01",
  "status": "ACTIVE",
  "no_parent_law": false,
  "needs_revision": 1,
  "serial_no": "12345",
  "field_name": "건축",
  "revision_type": "일부개정",
  "detail_link": "https://www.law.go.kr/..."
}
```
