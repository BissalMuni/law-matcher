# Tasks: 개정 검토 대상 판별 방식 병렬 탭

**Input**: Design documents from `/specs/005-revision-detection-tabs/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api-contracts.md

## Phase 1: Setup

**Purpose**: 프론트엔드 타입 정의 및 프로젝트 구조 준비

<<<<<<< HEAD
- [x] T001 [P] [US1] [US2] [US3] [US4] 프론트엔드 타입 정의 — RevisionReasonResponse, DetectionResult, DetectionResultsResponse, DetectionMethodType union, DetectionSummaryItem 타입 추가. 기존 Ordinance 타입에 detection 관련 필드 확장 (`frontend/src/types/api.ts`)
=======
- [ ] T001 [P] [US1] [US2] [US3] [US4] 프론트엔드 타입 정의 — RevisionReasonResponse, DetectionResult, DetectionResultsResponse, DetectionMethodType union, DetectionSummaryItem 타입 추가. 기존 Ordinance 타입에 detection 관련 필드 확장 (`frontend/src/types/api.ts`)
>>>>>>> origin/main

---

## Phase 2: Foundational — Models, Migrations, Client

**Purpose**: 신규 테이블, 모델, 마이그레이션, 외부 클라이언트 확장. 모든 US에 필요한 공통 인프라

**⚠️ CRITICAL**: Phase 2 완료 전까지 서비스/API 레이어 작업 불가

<<<<<<< HEAD
- [x] T002 [P] [US3] LawRevisionReason 모델 생성 — law_id FK(laws.id) UNIQUE, law_mst VARCHAR, revision_reason TEXT, amendment_content TEXT, extracted_articles JSONB, fetched_at TIMESTAMP, created_at, updated_at. `__init__.py`에 등록 (`backend/models/law_revision_reason.py` 신규)
- [x] T003 [P] [US1] [US2] [US3] RevisionDetectionResult 모델 생성 — ordinance_id FK, law_id FK, detection_method VARCHAR(30), needs_revision BOOLEAN, detail JSONB, detected_at. UNIQUE(ordinance_id, law_id, detection_method). 인덱스: ordinance_id, detection_method. `__init__.py`에 등록 (`backend/models/revision_detection_result.py` 신규)
- [x] T004 [P] [US2] Article 모델 확장 — revision_type_detail VARCHAR(50) nullable (조문제개정유형: 신설/일부개정/전부개정), change_flag VARCHAR(5) nullable (조문변경여부: Y/N) 추가 (`backend/models/article.py`)
- [x] T005 [P] [US1] [US2] [US3] Pydantic 스키마 정의 — RevisionReasonOut, DetectionResultOut, DetectionResultsOut, DetectRequest, DetectionMethodEnum. ordinance.py에 detection-results 응답 추가 (`backend/schemas/revision.py` 신규, `backend/schemas/ordinance.py` 수정)
- [x] T006 [US1] [US2] [US3] Alembic 마이그레이션 3건 — law_revision_reasons 테이블 생성, revision_detection_results 테이블 생성, articles에 revision_type_detail+change_flag 추가. 마이그레이션 의존 체인 설정 (`backend/alembic/versions/` 3건 신규)
- [x] T007 [US2] [US3] MolegClient 확장 — get_law_detail() 응답에서 `법령.제개정이유.제개정이유내용` (list[list[str]]) + `법령.개정문.개정문내용` (list[list[str]]) 파싱, `"\n".join(data[0])`으로 텍스트 복원, 조문메타(조문제개정유형/조문변경여부) 파싱, JSON 기본+XML 폴백, 파싱 실패 시 None+로깅 (`backend/external/moleg_client.py`)
- [x] T008 [US2] 조문 동기화 시 메타 저장 — 법제처 API 조문 동기화 시 T007에서 파싱된 revision_type_detail, change_flag를 Article 레코드에 저장 (신규+갱신 모두) (`backend/services/law_sync_service.py`)
- [x] T009 [P] [US2] 조문 응답 스키마 보강 — Article 스키마에 revision_type_detail, change_flag 필드 추가 (nullable), 프론트엔드에서 사용 가능하도록 직렬화 보장 (`backend/schemas/article.py`)
=======
- [ ] T002 [P] [US3] LawRevisionReason 모델 생성 — law_id FK(laws.id) UNIQUE, law_mst VARCHAR, revision_reason TEXT, amendment_content TEXT, extracted_articles JSONB, fetched_at TIMESTAMP, created_at, updated_at. `__init__.py`에 등록 (`backend/models/law_revision_reason.py` 신규)
- [ ] T003 [P] [US1] [US2] [US3] RevisionDetectionResult 모델 생성 — ordinance_id FK, law_id FK, detection_method VARCHAR(30), needs_revision BOOLEAN, detail JSONB, detected_at. UNIQUE(ordinance_id, law_id, detection_method). 인덱스: ordinance_id, detection_method. `__init__.py`에 등록 (`backend/models/revision_detection_result.py` 신규)
- [ ] T004 [P] [US2] Article 모델 확장 — revision_type_detail VARCHAR(50) nullable (조문제개정유형: 신설/일부개정/전부개정), change_flag VARCHAR(5) nullable (조문변경여부: Y/N) 추가 (`backend/models/article.py`)
- [ ] T005 [P] [US1] [US2] [US3] Pydantic 스키마 정의 — RevisionReasonOut, DetectionResultOut, DetectionResultsOut, DetectRequest, DetectionMethodEnum. ordinance.py에 detection-results 응답 추가 (`backend/schemas/revision.py` 신규, `backend/schemas/ordinance.py` 수정)
- [ ] T006 [US1] [US2] [US3] Alembic 마이그레이션 3건 — law_revision_reasons 테이블 생성, revision_detection_results 테이블 생성, articles에 revision_type_detail+change_flag 추가. 마이그레이션 의존 체인 설정 (`backend/alembic/versions/` 3건 신규)
- [ ] T007 [US2] [US3] MolegClient 확장 — get_law_detail() 응답에서 `법령.제개정이유.제개정이유내용` (list[list[str]]) + `법령.개정문.개정문내용` (list[list[str]]) 파싱, `"\n".join(data[0])`으로 텍스트 복원, 조문메타(조문제개정유형/조문변경여부) 파싱, JSON 기본+XML 폴백, 파싱 실패 시 None+로깅 (`backend/external/moleg_client.py`)
- [ ] T008 [US2] 조문 동기화 시 메타 저장 — 법제처 API 조문 동기화 시 T007에서 파싱된 revision_type_detail, change_flag를 Article 레코드에 저장 (신규+갱신 모두) (`backend/services/law_sync_service.py`)
- [ ] T009 [P] [US2] 조문 응답 스키마 보강 — Article 스키마에 revision_type_detail, change_flag 필드 추가 (nullable), 프론트엔드에서 사용 가능하도록 직렬화 보장 (`backend/schemas/article.py`)
>>>>>>> origin/main

**Checkpoint**: 모델/마이그레이션/클라이언트 확장 완료 — 서비스 레이어 구현 가능

---

## Phase 3: Service Logic

**Purpose**: 개정문 파서 및 3탭 판별 통합 서비스

<<<<<<< HEAD
- [x] T010 [US3] 개정문 조문번호 추출 파서 — `parse_amendment_articles(text) → list[str]`: 정규식 `제(\d+조(?:의\d+)?)` 패턴으로 변경 조문번호 추출 (중복 제거, 정렬). `match_articles_to_ordinance(articles, mapped)`: 매핑 대조 결과 반환. 엣지케이스: 빈 개정문, 비정형 패턴(별표/서식) (`backend/services/amendment_parser.py` 신규)
- [x] T011 [US1] [US2] [US3] 3탭 판별 통합 서비스 — detect_by_proclaimed_date(): 공포일자 비교, detect_by_article_change(): 조문 변경 추적 (revision_type_detail/change_flag 활용), detect_by_revision_reason(): 제개정이유 조회(DB캐시→API)→개정문 파싱→매핑 대조, detect_all(): 3방식 동시 실행+결과 DB 저장, get_cached_results(): 기존 결과 조회 (`backend/services/revision_detection_service.py` 신규)
=======
- [ ] T010 [US3] 개정문 조문번호 추출 파서 — `parse_amendment_articles(text) → list[str]`: 정규식 `제(\d+조(?:의\d+)?)` 패턴으로 변경 조문번호 추출 (중복 제거, 정렬). `match_articles_to_ordinance(articles, mapped)`: 매핑 대조 결과 반환. 엣지케이스: 빈 개정문, 비정형 패턴(별표/서식) (`backend/services/amendment_parser.py` 신규)
- [ ] T011 [US1] [US2] [US3] 3탭 판별 통합 서비스 — detect_by_proclaimed_date(): 공포일자 비교, detect_by_article_change(): 조문 변경 추적 (revision_type_detail/change_flag 활용), detect_by_revision_reason(): 제개정이유 조회(DB캐시→API)→개정문 파싱→매핑 대조, detect_all(): 3방식 동시 실행+결과 DB 저장, get_cached_results(): 기존 결과 조회 (`backend/services/revision_detection_service.py` 신규)
>>>>>>> origin/main

**Checkpoint**: 3가지 판별 방식 서비스 로직 완료

---

## Phase 4: API Endpoints

**Purpose**: 제개정이유 조회, 판별 결과 조회, 판별 실행 API

<<<<<<< HEAD
- [x] T012 [US3] 법령 제개정이유 API — GET /api/v1/laws/{id}/revision-reason: DB 캐시(LawRevisionReason) 확인→미스 시 MolegClient 호출→저장→반환. 에러: 404 법령 미발견, 502 API 오류, 204 데이터 없음 (`backend/api/v1/laws.py`)
- [x] T013 [P] [US1] [US2] [US3] 판별 결과 조회/실행 API — GET /api/v1/ordinances/{id}/detection-results: 3탭 결과 통합 조회 (캐시). POST /api/v1/ordinances/{id}/detect: 판별 실행 (methods 파라미터로 선택적), 결과 DB 저장 (`backend/api/v1/ordinances.py`)
=======
- [ ] T012 [US3] 법령 제개정이유 API — GET /api/v1/laws/{id}/revision-reason: DB 캐시(LawRevisionReason) 확인→미스 시 MolegClient 호출→저장→반환. 에러: 404 법령 미발견, 502 API 오류, 204 데이터 없음 (`backend/api/v1/laws.py`)
- [ ] T013 [P] [US1] [US2] [US3] 판별 결과 조회/실행 API — GET /api/v1/ordinances/{id}/detection-results: 3탭 결과 통합 조회 (캐시). POST /api/v1/ordinances/{id}/detect: 판별 실행 (methods 파라미터로 선택적), 결과 DB 저장 (`backend/api/v1/ordinances.py`)
>>>>>>> origin/main

**Checkpoint**: 3개 신규 API 엔드포인트 동작 확인

---

## Phase 5: US1 — 탭A 법령비교 서브탭 (P1) 🎯 MVP

**Goal**: 조례 상세 → 개정검토 탭 → 법령비교 서브탭에서 공포일자 비교 결과 표시

**Independent Test**: 공포일자가 이후인 법령은 "개정 검토 필요" 표시, 이전이면 "최신 상태"

<<<<<<< HEAD
- [x] T014 [P] [US1] [US2] [US3] 프론트엔드 API 서비스 확장 — getRevisionReason(lawId), getDetectionResults(ordinanceId), runDetection(ordinanceId, methods?) 함수 추가. TanStack Query 훅: useRevisionReason, useDetectionResults, useRunDetection (`frontend/src/services/api.ts`)
- [x] T015 [US1] TabA_LawCompare 컴포넌트 — 공포일자 기반 판별 결과 표시: 상위법령 목록+공포일자 비교, 변경 감지 Badge (Ant Design Tag), 차이 일수 표시, 가장 최근 개정 법령 상단 정렬. 로딩/에러 상태, 결과 없을 시 "판별 실행" 버튼 (`frontend/src/components/detection/TabA_LawCompare.tsx` 신규)
- [x] T016 [US1] OrdinanceDetail 개정검토 탭에 서브탭 구조 추가 — Ant Design Tabs로 법령비교/조문비교/개정이유비교 3개 서브탭 구성, lazy loading (탭 클릭 시 최초 1회 fetch), TabA_LawCompare 연결, TabB/TabC는 placeholder (`frontend/src/pages/OrdinanceDetail.tsx`)
=======
- [ ] T014 [P] [US1] [US2] [US3] 프론트엔드 API 서비스 확장 — getRevisionReason(lawId), getDetectionResults(ordinanceId), runDetection(ordinanceId, methods?) 함수 추가. TanStack Query 훅: useRevisionReason, useDetectionResults, useRunDetection (`frontend/src/services/api.ts`)
- [ ] T015 [US1] TabA_LawCompare 컴포넌트 — 공포일자 기반 판별 결과 표시: 상위법령 목록+공포일자 비교, 변경 감지 Badge (Ant Design Tag), 차이 일수 표시, 가장 최근 개정 법령 상단 정렬. 로딩/에러 상태, 결과 없을 시 "판별 실행" 버튼 (`frontend/src/components/detection/TabA_LawCompare.tsx` 신규)
- [ ] T016 [US1] OrdinanceDetail 개정검토 탭에 서브탭 구조 추가 — Ant Design Tabs로 법령비교/조문비교/개정이유비교 3개 서브탭 구성, lazy loading (탭 클릭 시 최초 1회 fetch), TabA_LawCompare 연결, TabB/TabC는 placeholder (`frontend/src/pages/OrdinanceDetail.tsx`)
>>>>>>> origin/main

**Checkpoint**: 법령비교 서브탭에서 공포일자 비교 결과 정상 표시

---

## Phase 6: US2 — 탭B 조문비교 서브탭 (P1)

**Goal**: 조문비교 서브탭에서 변경된 조문 목록 + 제개정유형 표시

**Independent Test**: 변경된 조문(change_flag=Y) 목록 표시, 매핑 조문 중 변경된 것 강조

<<<<<<< HEAD
- [x] T017 [US2] TabB_ArticleCompare 컴포넌트 — 조문 변경 기반 판별 결과: 변경된 조문 목록 (조문번호/제개정유형/변경여부), revision_type_detail 표시 (신설/일부개정/전부개정), change_flag 기반 하이라이트, 매핑 조문 변경 감지 강조, 신설 조문 별도 섹션. OrdinanceDetail 탭B placeholder 교체 (`frontend/src/components/detection/TabB_ArticleCompare.tsx` 신규)
=======
- [ ] T017 [US2] TabB_ArticleCompare 컴포넌트 — 조문 변경 기반 판별 결과: 변경된 조문 목록 (조문번호/제개정유형/변경여부), revision_type_detail 표시 (신설/일부개정/전부개정), change_flag 기반 하이라이트, 매핑 조문 변경 감지 강조, 신설 조문 별도 섹션. OrdinanceDetail 탭B placeholder 교체 (`frontend/src/components/detection/TabB_ArticleCompare.tsx` 신규)
>>>>>>> origin/main

**Checkpoint**: 조문비교 서브탭에서 변경 조문 목록 및 제개정유형 표시

---

## Phase 7: US3 — 탭C 개정이유비교 서브탭 (P1)

**Goal**: 개정이유분석 서브탭에서 제개정이유 전문 + 개정문 + 추출 조문 표시

**Independent Test**: 개정문에서 조문번호 자동 추출 → 매핑 대조 → 검토 필요/참고 분류

<<<<<<< HEAD
- [x] T018 [US3] TabC_ReasonCompare 컴포넌트 — 제개정이유 원문 (Typography.Paragraph, 접기/펼치기), 개정문 원문, 추출된 조문번호 목록 (Tag), 매핑 대조 결과: 매핑 조문="검토 필요" 하이라이트+비매핑="참고(매핑 검토)" (FR-011), 타법개정 시 "상세 확인 필요" 안내, useRevisionReason 훅 사용. OrdinanceDetail 탭C placeholder 교체 (`frontend/src/components/detection/TabC_ReasonCompare.tsx` 신규)
=======
- [ ] T018 [US3] TabC_ReasonCompare 컴포넌트 — 제개정이유 원문 (Typography.Paragraph, 접기/펼치기), 개정문 원문, 추출된 조문번호 목록 (Tag), 매핑 대조 결과: 매핑 조문="검토 필요" 하이라이트+비매핑="참고(매핑 검토)" (FR-011), 타법개정 시 "상세 확인 필요" 안내, useRevisionReason 훅 사용. OrdinanceDetail 탭C placeholder 교체 (`frontend/src/components/detection/TabC_ReasonCompare.tsx` 신규)
>>>>>>> origin/main

**Checkpoint**: 개정이유비교 서브탭에서 제개정이유+개정문+조문추출 표시, 매핑 대조 정상

---

## Phase 8: US4 — 서브탭 비교 뷰 (P2)

**Goal**: 관리자가 3개 서브탭 판별 결과를 나란히 비교하여 최적 방식 평가

**Independent Test**: 동일 조례에 대해 3탭 결과 비교 → 일치/불일치 분석

<<<<<<< HEAD
- [x] T019 [US4] DetectionSummary 컴포넌트 — 3탭 판별 결과 요약 카드: 방식별 needs_revision 아이콘 (CheckCircle/CloseCircle), 일치/불일치 하이라이트, Ant Design Descriptions/카드 그리드 (`frontend/src/components/detection/DetectionSummary.tsx` 신규)
- [x] T020 [US4] DetectionCompare 페이지 + 메뉴 등록 — 관리자 전용 3탭 비교 뷰 페이지. 조례 선택(검색/드롭다운), DetectionSummary 상단, 3탭 결과 나란히 비교 (Row+Col 그리드), TabA/B/C 컴포넌트 재사용, "전체 판별 실행" 버튼. MainLayout 관리자 메뉴에 "탭 비교" 추가, 라우트 /admin/detection-compare (`frontend/src/pages/DetectionCompare.tsx` 신규, `frontend/src/components/layout/MainLayout.tsx` 수정)
=======
- [ ] T019 [US4] DetectionSummary 컴포넌트 — 3탭 판별 결과 요약 카드: 방식별 needs_revision 아이콘 (CheckCircle/CloseCircle), 일치/불일치 하이라이트, Ant Design Descriptions/카드 그리드 (`frontend/src/components/detection/DetectionSummary.tsx` 신규)
- [ ] T020 [US4] DetectionCompare 페이지 + 메뉴 등록 — 관리자 전용 3탭 비교 뷰 페이지. 조례 선택(검색/드롭다운), DetectionSummary 상단, 3탭 결과 나란히 비교 (Row+Col 그리드), TabA/B/C 컴포넌트 재사용, "전체 판별 실행" 버튼. MainLayout 관리자 메뉴에 "탭 비교" 추가, 라우트 /admin/detection-compare (`frontend/src/pages/DetectionCompare.tsx` 신규, `frontend/src/components/layout/MainLayout.tsx` 수정)
>>>>>>> origin/main

**Checkpoint**: 관리자 비교 뷰에서 3탭 나란히 비교 가능

---

## Phase 9: US5 — 주간 요약 리포트 알림 (P2)

**Goal**: 주 1회 검토 요약 리포트를 인앱 알림함에 생성

**Independent Test**: 한 주간 감지 건 누적 → 주간 리포트 생성 → 인앱 알림함 확인

<<<<<<< HEAD
- [x] T021 [US5] 판별 결과 기반 알림 생성 로직 — detect_all() 완료 후 변경 감지 시 Notification 생성, 알림 내용: 어떤 방식에서 변경 감지되었는지 요약, 중복 알림 방지 (동일 ordinance+동일 결과), 주간 집계를 위한 기반 로직 (`backend/services/revision_detection_service.py` 수정)
- [x] T022 [US5] 프론트엔드 알림 표시 — 판별 결과에 변경 감지 시 Alert 배너 표시 (Ant Design Alert type=warning "새로운 변경이 감지되었습니다"), dismiss 가능 (`frontend/src/pages/OrdinanceDetail.tsx` 수정)
=======
- [ ] T021 [US5] 판별 결과 기반 알림 생성 로직 — detect_all() 완료 후 변경 감지 시 Notification 생성, 알림 내용: 어떤 방식에서 변경 감지되었는지 요약, 중복 알림 방지 (동일 ordinance+동일 결과), 주간 집계를 위한 기반 로직 (`backend/services/revision_detection_service.py` 수정)
- [ ] T022 [US5] 프론트엔드 알림 표시 — 판별 결과에 변경 감지 시 Alert 배너 표시 (Ant Design Alert type=warning "새로운 변경이 감지되었습니다"), dismiss 가능 (`frontend/src/pages/OrdinanceDetail.tsx` 수정)
>>>>>>> origin/main

**Checkpoint**: 판별 결과 변경 감지 시 알림 생성 및 프론트 표시

---

## Phase 10: Polish

**Purpose**: 통합 점검 및 최적화

<<<<<<< HEAD
- [x] T023 탭 전환 최적화 — lazy loading 동작 확인, 탭 간 상태 유지 (리렌더 방지), 로딩 스피너/스켈레톤 일관성, 3탭 로딩 3초 이내 (SC-003) (`frontend/src/pages/OrdinanceDetail.tsx`, 관련 컴포넌트)
- [x] T024 타입 정합성 및 에러 핸들링 — 백엔드 스키마↔프론트엔드 타입 일치 확인, API 에러 핸들링 일관성, 탭C API 장애 시 탭C만 비활성화+탭A/B 정상 동작 보장 (Constitution III)
=======
- [ ] T023 탭 전환 최적화 — lazy loading 동작 확인, 탭 간 상태 유지 (리렌더 방지), 로딩 스피너/스켈레톤 일관성, 3탭 로딩 3초 이내 (SC-003) (`frontend/src/pages/OrdinanceDetail.tsx`, 관련 컴포넌트)
- [ ] T024 타입 정합성 및 에러 핸들링 — 백엔드 스키마↔프론트엔드 타입 일치 확인, API 에러 핸들링 일관성, 탭C API 장애 시 탭C만 비활성화+탭A/B 정상 동작 보장 (Constitution III)
>>>>>>> origin/main

---

## Dependencies & Execution Order

```text
Phase 1 (Setup):
  T001 — 독립 실행 가능

Phase 2 (Foundational) — 모델 병렬, 마이그레이션/클라이언트 순차:
  T002 [P], T003 [P], T004 [P], T005 [P], T009 [P] — 병렬 가능
  T002 + T003 + T004 → T006 (마이그레이션)
  T006 → T007 (MolegClient 확장)
  T007 → T008 (조문 동기화 메타 저장)

Phase 3 (Services) — Phase 2 완료 후:
  T007 → T010 (개정문 파서)
  T007 + T010 → T011 (판별 통합 서비스)

Phase 4 (API) — Phase 3 완료 후:
  T011 → T012 (제개정이유 API)
  T011 → T013 [P] (판별 조회/실행 API)

Phase 5 (US1) — Phase 4 완료 후:
  T014 [P] (API 서비스) → T015 (TabA) → T016 (OrdinanceDetail 서브탭)

Phase 6 (US2) — T016 완료 후:
  T016 → T017 (TabB)

Phase 7 (US3) — T016 완료 후:
  T016 → T018 (TabC)

Phase 8 (US4) — T016 + T017 + T018 완료 후:
  T019 (DetectionSummary) → T020 (DetectionCompare 페이지)

Phase 9 (US5) — T011 완료 후:
  T011 → T021 (알림 로직) → T022 (프론트 알림)

Phase 10 (Polish) — 전체 완료 후:
  T023, T024
```

### Critical Path

```text
T002-T004 → T006 → T007 → T010 → T011 → T013 → T014 → T015 → T016 → T017/T018 → T019 → T020
```

### Parallel Execution Groups

- **Group A** [P]: T001, T002, T003, T004, T005, T009 (타입/모델/스키마 — 독립 파일)
- **Group B** [P]: T012, T013 (API 엔드포인트 — 다른 파일)
- **Group C** [P]: T017, T018 (TabB, TabC — T016 완료 후 병렬)
- **Group D** [P]: T021-T022 (US5 알림 — T011 완료 후 독립)

---

## Task Count Summary

| Phase                          | Tasks          | Priority |
| ------------------------------ | -------------- | -------- |
| Phase 1: Setup                 | T001 (1)       | Setup    |
| Phase 2: Foundational          | T002-T009 (8)  | P1       |
| Phase 3: Service Logic         | T010-T011 (2)  | P1       |
| Phase 4: API Endpoints         | T012-T013 (2)  | P1       |
| Phase 5: US1 TabA 법령비교     | T014-T016 (3)  | P1       |
| Phase 6: US2 TabB 조문비교     | T017 (1)       | P1       |
| Phase 7: US3 TabC 개정이유비교 | T018 (1)       | P1       |
| Phase 8: US4 서브탭 비교       | T019-T020 (2)  | P2       |
| Phase 9: US5 알림              | T021-T022 (2)  | P2       |
| Phase 10: Polish               | T023-T024 (2)  | Polish   |
| **Total**                      | **24 tasks**   |          |
