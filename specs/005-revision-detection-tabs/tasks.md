# 005-revision-detection-tabs: 구현 현황 체크리스트

기준 시점: 2026-03-02 (로컬 코드베이스 스캔 기준)

## 완료 태스크

- 없음

## 미완료 태스크

- [ ] T001 - 프론트엔드 타입 정의 추가 (`frontend/src/types/api.ts`)
- [ ] T002 - `LawRevisionReason` 모델 생성 (`backend/models/law_revision_reason.py`)
- [ ] T003 - `RevisionDetectionResult` 모델 생성 (`backend/models/revision_detection_result.py`)
- [ ] T004 - `Article` 모델 확장 (`revision_type_detail`, `change_flag`)
- [ ] T005 - 판별 관련 스키마 정의 (`backend/schemas/revision.py`, `backend/schemas/ordinance.py`)
- [ ] T006 - Alembic 마이그레이션 3건 생성 (revision reason / detection result / article fields)
- [ ] T007 - `MolegClient` 확장 (제개정이유/개정문/조문메타 파싱)
- [ ] T007a - 조문 동기화 시 메타데이터 저장 (`backend/services/law_sync_service.py`)
- [ ] T007b - 조문 응답 스키마/직렬화 보강 (`backend/schemas/article.py`)
- [ ] T008 - 개정문 조문번호 추출 파서 (`backend/services/amendment_parser.py`)
- [ ] T009 - 3탭 판별 통합 서비스 (`backend/services/revision_detection_service.py`)
- [ ] T010 - 법령 제개정이유 엔드포인트 (`GET /laws/{law_id}/revision-reason`)
- [ ] T011 - 자치법규 판별 엔드포인트 (`GET /ordinances/{id}/detection-results`, `POST /ordinances/{id}/detect`)
- [ ] T012 - 프론트 API 서비스/훅 확장 (`frontend/src/services/api.ts`)
- [ ] T013 - `TabA_ProclaimedDate` 컴포넌트
- [ ] T014 - `OrdinanceDetail` 탭 구조 재구성 (A/B/C 탭 + lazy)
- [ ] T015 - `TabB_ArticleChange` 컴포넌트
- [ ] T016 - `TabC_RevisionReason` 컴포넌트
- [ ] T017 - `DetectionSummary` 컴포넌트
- [ ] T018 - `DetectionCompare` 페이지 + 관리자 메뉴/라우트 등록
- [ ] T019 - 판별 결과 기반 알림 생성 로직 (`revision_detection_service.py`)
- [ ] T020 - 프론트엔드 알림 배너 표시 (`OrdinanceDetail.tsx`)
- [ ] T021 - 통합 점검 및 마무리

## 참고 (이번 점검에서 확인한 사실)

- `backend/models`에 `law_revision_reason.py`, `revision_detection_result.py` 파일이 없음
- `backend/services`에 `revision_detection_service.py`, `amendment_parser.py` 파일이 없음
- `backend/alembic/versions`에 관련 마이그레이션 파일/키워드가 없음
- `backend/api/v1/laws.py`, `backend/api/v1/ordinances.py`에 스펙의 detection/revision-reason 엔드포인트가 없음
- `frontend/src/components/detection/*`, `frontend/src/pages/DetectionCompare.tsx` 파일이 없음
- `frontend/src/pages/OrdinanceDetail.tsx`는 아직 스펙의 3탭 구조로 구성되어 있지 않음
