# Research: 002-ordinance-management

**Date**: 2026-02-28
**Input**: spec.md

## 기존 구현 현황

### 구현 완료 (대부분 완성)

| User Story | 백엔드 | 프론트엔드 | 비고 |
|------------|--------|-----------|------|
| US1 조례 목록 조회 | ✅ 완료 | ✅ 완료 | 10+ 필터, 페이지네이션, 부서 트리 |
| US2 조례 등록 | ✅ 완료 | ✅ 완료 | API 검색 + 수동 입력 모달 |
| US3 법제처 동기화 | ✅ 완료 | ✅ 완료 | 관리자 비밀번호 검증 포함 |
| US4 조례 상세 조회 | ✅ 완료 | ✅ 완료 | 기본정보 + 상위법령 + 검토이력 |
| US5 부서 일괄 배정 | ✅ 완료 | ✅ 완료 | 엑셀 업로드, 이름 정규화 매칭 |
| US6 엑셀 내보내기 | ✅ 완료 | ✅ 완료 | openpyxl, 조건부 서식 |

### 주요 코드 위치

| 구분 | 파일 | 크기 |
|------|------|------|
| ORM 모델 | `backend/models/ordinance.py` | Ordinance 테이블 |
| ORM 모델 | `backend/models/department.py` | Department 테이블 |
| ORM 모델 | `backend/models/ordinance_law_mapping.py` | 조례-법령 N:M |
| ORM 모델 | `backend/models/ordinance_review.py` | 검토이력 |
| Pydantic 스키마 | `backend/schemas/ordinance.py` | 요청/응답 DTO |
| 서비스 | `backend/services/ordinance_service.py` | 1199줄, 핵심 비즈니스 로직 |
| API 라우터 | `backend/api/v1/ordinances.py` | 935줄, 30+ 엔드포인트 |
| 외부 클라이언트 | `backend/external/moleg_client.py` | 310줄, 법제처 API |
| 프론트 목록 | `frontend/src/pages/OrdinanceList.tsx` | 1002줄 |
| 프론트 상세 | `frontend/src/pages/OrdinanceDetail.tsx` | 767줄 |
| 프론트 API | `frontend/src/services/api.ts` | ordinanceApi + ordinanceManagementApi |

### 기존 패턴

- **계층 분리**: API(v1/ordinances.py) → Service(ordinance_service.py) → Model(ordinance.py)
- **페이지네이션**: page(1-indexed) + size, 응답: {total, page, size, items}
- **필터링**: Subquery 기반, Group-by/Having, URL 쿼리 파라미터 동기화
- **인증**: JWT + verify_admin_password (관리 API용)
- **엑셀**: openpyxl(export), pandas(import), 유니코드 정규화
- **비동기 동기화**: Celery Beat (매일 자동), 수동 트리거 가능

## 미비 사항 (보강 필요)

### 1. 조례 상태 생명주기 부재

현재 `status` 필드: `ACTIVE` / `EXCLUDED`만 존재.

**문제**: 조례가 **폐지(ABOLISHED)**될 수 있으나, 이를 추적하는 상태가 없음.
- 법제처 동기화 시 폐지된 조례를 감지해도 상태 반영 불가
- Constitution I(데이터 무결성): 폐지된 조례를 삭제하면 안 되므로 상태 관리 필수

**해결**: status ENUM 확장 → `ACTIVE` / `ABOLISHED` / `EXCLUDED`
- `ACTIVE`: 현행 (시행 중)
- `ABOLISHED`: 폐지 (법적으로 소멸, 이력 보존)
- `EXCLUDED`: 관리 제외 (시스템 운영상 관리 대상에서 제외)

### 2. 에러 처리 보강

- 법제처 API 타임아웃 시 사용자 안내 메시지 미흡
- 동기화 중 동일 조례 수동 등록 시 race condition 처리 없음
- code 중복 검사는 있으나 에러 메시지가 영어

### 3. 필터 조건 누락

spec FR-002에서 요구하는 필터 중 일부 확인 필요:
- `제개정구분` 필터: ✅ 구현됨 (revision_type)
- `개정 필요 여부` 필터: ✅ 구현됨 (needs_revision)
- 검색어 필터: ✅ 구현됨 (조례명 검색)

### 4. 부서 접근 제어

- FR-003(부서 사용자 소속 부서만 조회): 백엔드에서 department_id 기반 필터링 존재
- 프론트엔드에서도 역할별 UI 분리 구현됨 (부서 트리는 관리자만 표시)

## 외부 의존성

| 의존성 | 용도 | 현재 상태 |
|--------|------|-----------|
| 법제처 API (law.go.kr) | 조례 검색/동기화 | ✅ moleg_client.py에 격리 |
| openpyxl | 엑셀 내보내기 | ✅ 도입됨 |
| pandas | 엑셀 가져오기 | ✅ 도입됨 |
| Celery + Redis | 백그라운드 동기화 | ✅ 구성됨 |

## 결론

**조례 관리 기능은 거의 완성 상태**이며, 주요 보강 작업은:

1. **status 확장**: ABOLISHED 상태 추가 + 동기화 시 폐지 감지 로직
2. **에러 처리 한국어화**: 사용자 대면 에러 메시지 보강
3. **Edge case 처리**: race condition, 타임아웃 안내
