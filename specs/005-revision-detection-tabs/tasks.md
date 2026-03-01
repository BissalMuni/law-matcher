# 005-revision-detection-tabs: Task Breakdown

## Dependencies & Execution Order

```
Phase 1 (Setup)
  T001 ─────────────────────────────────────────────────┐
                                                         │
Phase 2 (Foundational - Models + Migrations + Client)    │
  T002 [P] ──┐                                          │
  T003 [P] ──┤                                          │
  T004 [P] ──┤                                          │
  T005 [P] ──┤                                          │
  T006       ←┘ (after T002-T005)                       │
  T007       ← (after T006)                             │
                                                         │
Phase 3 (Service Logic)                                  │
  T008       ← (after T007)                             │
  T009       ← (after T007, T008)                       │
                                                         │
Phase 4 (API Endpoints)                                  │
  T010       ← (after T009)                             │
  T011       ← (after T009)                             │
                                                         │
Phase 5 (Frontend - US1 Tab A)                           │
  T012 [P] ──┐                                          │
  T013       ←┘ (after T012)                            │
  T014       ← (after T013)                             │
                                                         │
Phase 6 (Frontend - US2 Tab B)                           │
  T015       ← (after T014)                             │
                                                         │
Phase 7 (Frontend - US3 Tab C)                           │
  T016       ← (after T014)                             │
                                                         │
Phase 8 (Frontend - US4 Compare)                         │
  T017       ← (after T014, T015, T016)                 │
  T018       ← (after T017)                             │
                                                         │
Phase 9 (US5 Notifications)                              │
  T019       ← (after T009)                             │
  T020       ← (after T019)                             │
                                                         │
Phase 10 (Polish & Integration)                          │
  T021       ← (after all)                              │
```

---

## Phase 1: Setup

### T001 - 프론트엔드 타입 정의 추가 [US1][US2][US3][US4]
**File:** `frontend/src/types/api.ts` (수정)
**Work:**
- 탭 관련 타입 추가:
  - `RevisionReasonResponse` (제개정이유 API 응답)
  - `DetectionResult` (판별 결과 단건)
  - `DetectionResultsResponse` (3탭 통합 판별 결과)
  - `DetectionTab` union type: `'proclaimed_date' | 'article_change' | 'revision_reason'`
  - `DetectionSummaryItem` (요약 뷰용)
- 기존 `Ordinance` 타입에 detection 관련 필드 확장

---

## Phase 2: Foundational (Models + Migrations + MolegClient)

### T002 - LawRevisionReason 모델 생성 [P][US3]
**File:** `backend/models/law_revision_reason.py` (신규)
**Work:**
- 신규 모델 `LawRevisionReason`:
  - `id` (PK)
  - `law_mst_id` (FK → law_mst)
  - `revision_reason_content` (Text) - 제개정이유내용
  - `amendment_content` (Text) - 개정문내용
  - `fetched_at` (DateTime) - 캐시 시점
  - 유니크 제약: `law_mst_id` (1:1 캐시)
- `__init__.py`에 모델 등록

### T003 - RevisionDetectionResult 모델 생성 [P][US1][US2][US3]
**File:** `backend/models/revision_detection_result.py` (신규)
**Work:**
- 신규 모델 `RevisionDetectionResult`:
  - `id` (PK)
  - `ordinance_id` (FK → ordinance)
  - `detection_method` (Enum: `proclaimed_date`, `article_change`, `revision_reason`)
  - `is_changed` (Boolean) - 변경 판별 결과
  - `detail` (JSON) - 방식별 상세 결과
  - `detected_at` (DateTime)
  - 유니크 제약: `(ordinance_id, detection_method)`
- `__init__.py`에 모델 등록

### T004 - Article 모델 확장 [P][US2]
**File:** `backend/models/article.py` (수정)
**Work:**
- 필드 추가:
  - `revision_type_detail` (String, nullable) - 조문제개정유형 (예: "신설", "개정", "삭제")
  - `change_flag` (Boolean, nullable) - 변경여부 플래그
- 기존 관계/인덱스에 영향 없도록 nullable 추가

### T005 - 스키마 정의 [P][US1][US2][US3]
**File:** `backend/schemas/revision.py` (신규)
**Work:**
- Pydantic 스키마:
  - `RevisionReasonOut` - 제개정이유 응답
  - `DetectionResultOut` - 판별 결과 단건
  - `DetectionResultsOut` - 3탭 통합 응답
  - `DetectRequest` - 판별 실행 요청
  - `DetectionMethodEnum` - 판별 방식 enum

**File:** `backend/schemas/ordinance.py` (수정)
- detection-results 관련 응답 스키마 추가

### T006 - Alembic 마이그레이션 3건 생성
**Files (신규):**
- `backend/alembic/versions/YYYYMMDD_add_law_revision_reasons.py`
- `backend/alembic/versions/YYYYMMDD_add_revision_detection_results.py`
- `backend/alembic/versions/YYYYMMDD_add_article_revision_fields.py`
**Work:**
- T002 모델 → `law_revision_reasons` 테이블 생성
- T003 모델 → `revision_detection_results` 테이블 생성
- T004 변경 → `articles` 테이블에 `revision_type_detail`, `change_flag` 컬럼 추가
- 마이그레이션 의존 체인 설정 (순서 보장)
**Depends on:** T002, T003, T004

### T007 - MolegClient 확장: 제개정이유/개정문/조문메타 파싱 [US2][US3]
**File:** `backend/external/moleg_client.py` (수정)
**Work:**
- `get_law_detail()` 응답 파싱 확장:
  - `법령.제개정이유.제개정이유내용` (list[list[str]]) 추출
  - `법령.개정문.개정문내용` (list[list[str]]) 추출
  - 텍스트 복원: `"\n".join(data[0])`
  - 조문메타 파싱: `조문제개정유형`, `조문변경여부` 필드 추출
- 반환 딕셔너리에 `revision_reason`, `amendment_text`, 조문별 `revision_type_detail`/`change_flag` 포함
- 파싱 실패 시 graceful fallback (None 반환, 로깅)
**Depends on:** T006

---

## Phase 2.5: 조문 동기화 메타데이터 저장

### T007a - 조문 동기화 시 신규 메타 저장 [US2]

**File:** `backend/services/law_sync_service.py` (수정)
**Work:**

- 법제처 API 조문 동기화 시 `revision_type_detail`, `change_flag` 필드를 Article 레코드에 저장
- MolegClient(T007)에서 파싱된 조문메타(`조문제개정유형`, `조문변경여부`)를 DB에 반영
- 기존 동기화 로직에 메타 필드 업데이트 추가 (신규 조문 생성 시 + 기존 조문 갱신 시)
**Depends on:** T007

### T007b - 조문 응답 스키마/직렬화 보강 [US2]

**File:** `backend/schemas/article.py` (수정 또는 신규)
**Work:**

- 조문 API 응답에 `revision_type_detail`, `change_flag` 필드 포함
- 기존 Article 스키마에 새 필드 추가 (nullable)
- 프론트엔드 TabB에서 사용할 수 있도록 직렬화 보장
**Depends on:** T004, T005

---

## Phase 3: Service Logic

### T008 - 개정문 조문번호 추출 파서 [US3]
**File:** `backend/services/amendment_parser.py` (신규)
**Work:**
- `parse_amendment_articles(amendment_text: str) -> list[str]`:
  - 정규식 `제(\d+조(?:의\d+)?)` 로 조문번호 추출
  - 중복 제거, 정렬 반환
- `match_articles_to_ordinance(article_numbers: list[str], mapped_articles: list[Article]) -> list[dict]`:
  - 추출된 조문번호와 매핑 테이블의 조문 대조
  - 매치 결과 반환 (매치/미매치 구분)
- 엣지 케이스 처리: 빈 개정문, 조문번호 없는 경우
**Depends on:** T007

### T009 - 3탭 판별 통합 서비스 [US1][US2][US3]
**File:** `backend/services/revision_detection_service.py` (신규)
**Work:**
- `RevisionDetectionService` 클래스:
  - `detect_by_proclaimed_date(ordinance_id) -> DetectionResultOut`:
    - 기존 공포일자 비교 로직 재사용/호출
    - 결과를 `RevisionDetectionResult`에 저장
  - `detect_by_article_change(ordinance_id) -> DetectionResultOut`:
    - `ArticleChange` 테이블 조회
    - T004에서 추가한 `revision_type_detail`, `change_flag` 활용
    - 결과 저장
  - `detect_by_revision_reason(ordinance_id) -> DetectionResultOut`:
    - MolegClient로 제개정이유/개정문 조회 (캐시 확인 → 없으면 API 호출 → LawRevisionReason 저장)
    - `amendment_parser`로 조문번호 추출
    - 매핑 테이블 대조 → 영향 여부 판별
    - 결과 저장
  - `detect_all(ordinance_id) -> DetectionResultsOut`:
    - 3방식 모두 실행, 통합 결과 반환
  - `get_cached_results(ordinance_id) -> DetectionResultsOut | None`:
    - 기존 판별 결과 조회 (캐시)
**Depends on:** T007, T008

---

## Phase 4: API Endpoints

### T010 - 법령 제개정이유 엔드포인트 [US3]
**File:** `backend/api/v1/laws.py` (수정)
**Work:**
- `GET /laws/{law_id}/revision-reason`:
  - LawRevisionReason 캐시 확인
  - 캐시 미스 → MolegClient 호출 → 저장 → 반환
  - 응답: `RevisionReasonOut` (제개정이유내용 + 개정문내용)
**Depends on:** T009

### T011 - 자치법규 판별 엔드포인트 [US1][US2][US3]
**File:** `backend/api/v1/ordinances.py` (수정)
**Work:**
- `GET /ordinances/{ordinance_id}/detection-results`:
  - 캐시된 판별 결과 조회
  - 없으면 빈 응답 (404 아님, 빈 배열)
  - 응답: `DetectionResultsOut`
- `POST /ordinances/{ordinance_id}/detect`:
  - body로 `detection_method` 지정 가능 (생략 시 전체)
  - `RevisionDetectionService.detect_all()` 또는 개별 호출
  - 응답: `DetectionResultsOut`
**Depends on:** T009

---

## Phase 5: Frontend - US1 (Tab A: 공포일자 기반)

### T012 - API 서비스 확장 [P][US1][US2][US3]
**File:** `frontend/src/services/api.ts` (수정)
**Work:**
- API 함수 추가:
  - `getRevisionReason(lawId: number)` → GET /laws/{id}/revision-reason
  - `getDetectionResults(ordinanceId: number)` → GET /ordinances/{id}/detection-results
  - `runDetection(ordinanceId: number, method?: string)` → POST /ordinances/{id}/detect
- TanStack Query 훅:
  - `useRevisionReason(lawId)`
  - `useDetectionResults(ordinanceId)`
  - `useRunDetection()` (mutation)

### T013 - TabA_ProclaimedDate 컴포넌트 [US1]
**File:** `frontend/src/components/detection/TabA_ProclaimedDate.tsx` (신규)
**Work:**
- Props: `ordinanceId`, `detectionResult?`
- 공포일자 기반 판별 결과 표시:
  - 상위법령 최신 공포일자 vs 매핑 시점 비교
  - 변경 감지 여부 Badge (Ant Design Tag)
  - 상세: 공포일자 타임라인, 차이 일수
- 로딩/에러 상태 처리
- 결과 없을 시 "판별 실행" 버튼 표시
**Depends on:** T012

### T014 - OrdinanceDetail 탭 구조 재구성 [US1]
**File:** `frontend/src/pages/OrdinanceDetail.tsx` (수정)
**Work:**
- 기존 Card 기반 레이아웃 → Ant Design `Tabs` 구조로 변경
- 탭 구성:
  - 탭A: "공포일자 기반" → `TabA_ProclaimedDate` (lazy)
  - 탭B: "조문 변경 기반" → placeholder (T015에서 구현)
  - 탭C: "제개정이유 기반" → placeholder (T016에서 구현)
- 탭 lazy loading: 선택 시에만 데이터 fetch
- 기존 매핑/조문 정보는 유지 (탭 외부 또는 별도 섹션)
**Depends on:** T013

---

## Phase 6: Frontend - US2 (Tab B: 조문 변경 기반)

### T015 - TabB_ArticleChange 컴포넌트 [US2]
**File:** `frontend/src/components/detection/TabB_ArticleChange.tsx` (신규)
**Work:**
- Props: `ordinanceId`, `detectionResult?`
- 조문 변경 기반 판별 결과 표시:
  - ArticleChange 목록 (조문번호, 변경유형, 변경전/후)
  - `revision_type_detail` 컬럼 표시 (신설/개정/삭제)
  - `change_flag` 기반 하이라이트
  - Ant Design Table 사용
- 변경 없는 조문은 접힌 상태로 표시
- OrdinanceDetail 탭B placeholder 교체
**Depends on:** T014

---

## Phase 7: Frontend - US3 (Tab C: 제개정이유 기반)

### T016 - TabC_RevisionReason 컴포넌트 [US3]
**File:** `frontend/src/components/detection/TabC_RevisionReason.tsx` (신규)
**Work:**
- Props: `ordinanceId`, `lawId`, `detectionResult?`
- 제개정이유 기반 판별 결과 표시:
  - 제개정이유 원문 표시 (Typography.Paragraph, 접기/펼치기)
  - 개정문 원문 표시
  - 추출된 조문번호 목록 (Tag 컴포넌트)
  - 매핑 대조 결과: 매치된 조문 하이라이트, 미매치 조문 별도 표시
  - 영향 판별 결과 Badge
- `useRevisionReason(lawId)` 훅 사용
- OrdinanceDetail 탭C placeholder 교체
**Depends on:** T014

---

## Phase 8: Frontend - US4 (탭 비교 뷰)

### T017 - DetectionSummary 컴포넌트 [US4]
**File:** `frontend/src/components/detection/DetectionSummary.tsx` (신규)
**Work:**
- Props: `detectionResults: DetectionResultsResponse`
- 3탭 판별 결과 요약 카드:
  - 각 방식별 변경 감지 여부 아이콘 (CheckCircle/CloseCircle)
  - 일치/불일치 하이라이트
  - 최종 판별 제안 (다수결 또는 가중치 기반)
- Ant Design Descriptions 또는 카드 그리드 사용
**Depends on:** T014, T015, T016

### T018 - DetectionCompare 페이지 + 메뉴 등록 [US4]
**File:** `frontend/src/pages/DetectionCompare.tsx` (신규)
**Work:**
- 관리자 전용 페이지: 3탭 판별 결과 비교 뷰
- 자치법규 선택 (검색/드롭다운)
- 선택된 자치법규에 대해:
  - `DetectionSummary` 상단 표시
  - 3탭 결과 나란히 비교 (Row + Col 그리드)
  - 각 탭 컴포넌트 재사용 (TabA, TabB, TabC)
- "전체 판별 실행" 버튼 → `useRunDetection` mutation
- 로딩/에러 상태

**File:** `frontend/src/components/layout/MainLayout.tsx` (수정)
- 관리자 메뉴에 "탭 비교" 항목 추가
- 라우트: `/admin/detection-compare`
**Depends on:** T017

---

## Phase 9: US5 (자동 알림)

### T019 - 판별 결과 기반 알림 생성 로직 [US5]
**File:** `backend/services/revision_detection_service.py` (수정)
**Work:**
- `detect_all()` 완료 후 알림 생성 로직 추가:
  - 변경 감지 시 → Notification 레코드 생성
  - 알림 내용: 어떤 방식(들)에서 변경 감지되었는지 요약
  - 기존 Notification 모델/서비스 활용 (있는 경우) 또는 간단한 알림 테이블 활용
- 중복 알림 방지: 동일 ordinance + 동일 결과에 대해 재알림 안 함
**Depends on:** T009

### T020 - 프론트엔드 알림 표시 [US5]
**File:** `frontend/src/pages/OrdinanceDetail.tsx` (수정)
**Work:**
- 판별 결과에 변경 감지가 있을 경우 Alert 배너 표시
- "새로운 변경이 감지되었습니다" 알림 (Ant Design Alert, type=warning)
- 알림 dismiss 가능
**Depends on:** T019

---

## Phase 10: Polish & Integration

### T021 - 통합 점검 및 마무리
**Files:** 전체 관련 파일
**Work:**
- OrdinanceDetail 탭 전환 시 데이터 로딩 최적화 확인
- 탭 간 상태 유지 (탭 전환 시 리렌더 방지)
- API 에러 핸들링 일관성 점검
- 타입 정합성 확인 (백엔드 스키마 ↔ 프론트엔드 타입)
- 로딩 스피너/스켈레톤 일관성
- 관리자 권한 체크 (DetectionCompare 페이지)
**Depends on:** T001-T020

---

## Summary

| Phase | Tasks | Priority | User Stories |
|-------|-------|----------|-------------|
| 1. Setup | T001 | P1 | US1,US2,US3,US4 |
| 2. Foundational | T002-T007 | P1 | US1,US2,US3 |
| 3. Service Logic | T008-T009 | P1 | US1,US2,US3 |
| 4. API Endpoints | T010-T011 | P1 | US1,US2,US3 |
| 5. Frontend US1 | T012-T014 | P1 | US1 |
| 6. Frontend US2 | T015 | P1 | US2 |
| 7. Frontend US3 | T016 | P1 | US3 |
| 8. Frontend US4 | T017-T018 | P2 | US4 |
| 9. US5 Notifications | T019-T020 | P2 | US5 |
| 10. Polish | T021 | P1 | All |

**Total: 21 tasks** (T001-T021)
**Parallel opportunities:** T002-T005 (Phase 2 models), T012 (API service can start with T013)
**Critical path:** T001 → T002-T005 → T006 → T007 → T008 → T009 → T010/T011 → T012 → T013 → T014 → T015/T016 → T017 → T018 → T021
