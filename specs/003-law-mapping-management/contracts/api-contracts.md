# API Contracts: 003-law-mapping-management

**Date**: 2026-02-28
**Base Path**: `/api/v1`

## 엔드포인트 목록

### 상위법령 매핑 (조례 기준) — 구현됨

| Method | Path | 인증 | 설명 | 상태 |
|--------|------|------|------|------|
| GET | `/ordinances/{id}/parent-laws` | JWT | 상위법령 연결 목록 | 구현됨 |
| POST | `/ordinances/{id}/parent-laws` | JWT | 상위법령 연결 추가 | 구현됨 |
| PUT | `/ordinances/parent-laws/{id}` | JWT | 상위법령 연결 수정 | 구현됨 |
| DELETE | `/ordinances/parent-laws/{id}` | JWT | 상위법령 연결 삭제 | 구현됨 |
| POST | `/ordinances/{id}/no-parent-law` | JWT | 상위법령 없음 설정 | 구현됨 |
| DELETE | `/ordinances/{id}/no-parent-law` | JWT | 상위법령 없음 해제 | 구현됨 |

### 조문 매핑 — 구현됨

| Method | Path | 인증 | 설명 | 상태 |
|--------|------|------|------|------|
| GET | `/ordinances/{id}/mapped-articles` | JWT | 매핑된 조문 목록 | 구현됨 |
| GET | `/ordinances/{id}/available-articles` | JWT | 매핑 가능한 조문 목록 | 구현됨 |
| POST | `/ordinances/{id}/mapped-articles/bulk` | JWT | 조문 일괄 매핑 | 구현됨 |

### 법령 관리 — 구현됨

| Method | Path | 인증 | 설명 | 상태 |
|--------|------|------|------|------|
| GET | `/laws` | JWT | 법령 목록 (페이지네이션) | 구현됨 |
| GET | `/laws/{id}` | JWT | 법령 상세 | 구현됨 |
| GET | `/laws/{id}/ordinances` | JWT | 법령에 연결된 조례 목록 | 구현됨 |
| GET | `/laws/{id}/articles` | JWT | 법령 조문 목록 | 구현됨 |
| POST | `/laws/sync` | JWT+AdminPW | lnkOrg 동기화 | 구현됨 |
| GET | `/laws/sync-stream` | JWT | SSE 스트리밍 동기화 | 구현됨 |
| POST | `/laws/search` | JWT | 법제처 API 법령 검색 | 구현됨 |
| DELETE | `/laws/{id}` | JWT(Admin) | 법령 삭제 | 구현됨 |

### 조문 관리 — 구현됨

| Method | Path | 인증 | 설명 | 상태 |
|--------|------|------|------|------|
| GET | `/articles` | JWT | 조문 목록 | 구현됨 |
| GET | `/articles/{id}` | JWT | 조문 상세 | 구현됨 |
| GET | `/articles/{id}/ordinances` | JWT | 조문에 연결된 조례 | 구현됨 |
| GET | `/articles/{id}/history` | JWT | 조문 변경 이력 | 구현됨 |
| POST | `/articles/sync` | JWT+AdminPW | 조문 동기화 | 구현됨 |
| GET | `/articles/auto-recommendations` | JWT | 자동 추천 (Jaccard) | 구현됨 |
| GET | `/articles/revision-needed` | JWT | 개정 필요 조례 목록 | 구현됨 |

---

## 변경 사항

신규 엔드포인트 없음. 기존 API 계약으로 spec 요구사항 충족.

보강 사항:
- 에러 응답 한국어화 (매핑 중복, 법령 미발견 등)
- 조문 삭제 시 영향받는 매핑 경고 응답 추가
