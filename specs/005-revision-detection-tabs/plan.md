# Implementation Plan: 개정 검토 대상 판별 방식 병렬 탭

**Branch**: `005-revision-detection-tabs` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-revision-detection-tabs/spec.md`

## Summary

개정 검토 대상을 3가지 독립 방식(A: 공포일자 비교, B: 조문 변경 추적, C: 제개정이유 분석)으로 판별하는 병렬 탭 시스템을 구축한다. 탭A/B는 기존 코드에 데이터와 로직이 있어 **UI 구조화 중심**, 탭C는 법제처 API의 제개정이유/개정문 데이터를 **신규 파싱**하여 변경 조문을 자동 추출한다. 실무 평가 후 최적 방식을 선택하여 나머지를 탈락시킨다.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.3 (frontend)
**Primary Dependencies**: FastAPI >=0.104, SQLAlchemy 2.0 (async), React 18, Ant Design 5, TanStack Query 5, Celery 5.3
**Storage**: PostgreSQL 15, Redis 7 (Celery broker)
**Testing**: pytest (backend)
**Target Platform**: Docker (Linux containers), 브라우저 (Chrome/Edge)
**Project Type**: Web application (SPA + REST API)
**Performance Goals**: 3탭 로딩 3초 이내 (SC-003), 조문번호 추출 정확도 90% (SC-002)
**Constraints**: 관공서 보안성 검토 대상, 시큐어코딩 준수, Phase 2 Java eGovFrame 전환 대비
**Scale/Scope**: 법령 수천 건, 조문 수만 건, 조례 수백~수천 건

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | 원칙 | 준수 여부 | 근거 |
|---|------|----------|------|
| I | 데이터 무결성 | PASS | 제개정이유/개정문 원본 DB 캐시 보존. 판별 결과 이력 보존 |
| II | 관심사 분리 | PASS | 탭별 독립 서비스 로직. 파서 모듈 분리 (amendment_parser.py) |
| III | 외부 의존 격리 | WARN | 탭C가 법제처 API 추가 호출. moleg_client에 격리. 장애 시 탭C만 비활성화 |
| IV | 비차단 처리 | PASS | 탭별 lazy loading, API 호출 비동기 |
| V | 환경 재현성 | PASS | Docker Compose, 환경변수 |
| VI | 보안 기본 적용 | PASS | JWT 인증, API 읽기 전용 (사용자 입력 없음) |
| VII | 사용자 중심 설계 | PASS | 3탭 병렬 비교로 사용자 선택권, 한국어 UI |
| VIII | AI 보조 활용 | N/A | 정규식/키워드 기반 파싱, LLM 아님 |

**Gate Result**: ALL PASS (III은 WARN — 격리 설계로 해결)

## Project Structure

### Documentation (this feature)

```text
specs/005-revision-detection-tabs/
├── plan.md              # This file
├── research.md          # Phase 1 output
├── data-model.md        # Phase 2 output
├── contracts/
│   └── api-contracts.md
└── tasks.md             # Phase 3 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── models/
│   ├── law_revision_reason.py       # 신규: 제개정이유/개정문 캐시
│   ├── revision_detection_result.py # 신규: 판별 결과 통합 저장
│   └── article.py                   # 수정: revision_type_detail, change_flag 추가
├── schemas/
│   ├── revision.py                  # 신규: 판별 관련 스키마
│   └── ordinance.py                 # 수정: detection-results 응답 추가
├── services/
│   ├── revision_detection_service.py # 신규: 3탭 판별 통합 서비스
│   └── amendment_parser.py          # 신규: 개정문 조문번호 추출 파서
├── api/v1/
│   ├── laws.py                      # 수정: revision-reason 엔드포인트 추가
│   └── ordinances.py                # 수정: detection-results, detect 엔드포인트 추가
├── external/
│   └── moleg_client.py              # 수정: 제개정이유/개정문/조문메타 파싱 추가
└── alembic/versions/
    ├── YYYYMMDD_add_law_revision_reasons.py        # 신규
    ├── YYYYMMDD_add_revision_detection_results.py  # 신규
    └── YYYYMMDD_add_article_revision_fields.py     # 신규

frontend/src/
├── pages/
│   ├── OrdinanceDetail.tsx          # 수정: Card → Tabs 구조 변경
│   └── DetectionCompare.tsx         # 신규: 3탭 비교 뷰 (관리자)
├── components/
│   ├── detection/
│   │   ├── TabA_ProclaimedDate.tsx  # 신규: 공포일자 비교 탭
│   │   ├── TabB_ArticleChange.tsx   # 신규: 조문 변경 탭
│   │   ├── TabC_RevisionReason.tsx  # 신규: 제개정이유 분석 탭
│   │   └── DetectionSummary.tsx     # 신규: 판별 요약 배지
│   └── layout/
│       └── MainLayout.tsx           # 수정: 탭비교 메뉴 항목 추가 (관리자)
├── services/
│   └── api.ts                       # 수정: revision-reason, detection-results API 추가
└── types/
    └── api.ts                       # 수정: 탭 관련 타입 추가
```

**Structure Decision**: 기존 Web application 구조 유지. 탭 컴포넌트를 `components/detection/`에 분리하여 OrdinanceDetail에서 조합. 판별 로직은 `revision_detection_service.py`에 통합.

## 구현 범위

### 구현 대상

| User Story | 상태 | 작업 |
|------------|------|------|
| US1 탭A 공포일자 | ✅ 데이터/로직 완료 | UI를 Tabs 구조로 재구성 |
| US2 탭B 조문변경 | ⚠️ 부분 구현 | 조문제개정유형/변경여부 필드 추가 + UI 탭 |
| US3 탭C 제개정이유 | ❌ 미구현 | **전면 신규** (API 파싱→모델→서비스→UI) |
| US4 탭 비교 | ❌ 미구현 | 신규 비교 뷰 페이지 |
| US5 자동 알림 | ❌ 미구현 | 알림 생성 로직 (이메일/웹훅은 추후) |

### 핵심 구현 단계

#### Step 1: 백엔드 기반 (모델 + API 파싱)

1. **MolegClient 확장**: `get_law_detail()`에 제개정이유/개정문/조문메타 파싱 추가
2. **신규 모델 생성**: LawRevisionReason, RevisionDetectionResult
3. **Article 모델 확장**: revision_type_detail, change_flag 필드
4. **마이그레이션 3건** 실행

#### Step 2: 서비스 로직

1. **amendment_parser.py**: 개정문에서 조문번호 추출 (`제X조(의X)` 정규식)
2. **revision_detection_service.py**: 3방식 판별 통합
   - `detect_by_proclaimed_date()` (기존 로직 재사용)
   - `detect_by_article_change()` (ArticleChange 조회)
   - `detect_by_revision_reason()` (개정문 파싱 + 매핑 대조)

#### Step 3: API 엔드포인트

1. `GET /laws/{id}/revision-reason`: 제개정이유 조회 (DB 캐시 → API 폴백)
2. `GET /ordinances/{id}/detection-results`: 3탭 결과 통합 조회
3. `POST /ordinances/{id}/detect`: 판별 실행

#### Step 4: 프론트엔드

1. **OrdinanceDetail 재구성**: Card → Ant Design `<Tabs>` (lazy loading)
2. **TabA 컴포넌트**: 기존 상위법령 테이블 + 공포일자 비교 강조
3. **TabB 컴포넌트**: 조문 변경 목록 + 매핑 조문 강조 + 제개정유형 표시
4. **TabC 컴포넌트**: 제개정이유 전문 + 개정문 + 추출 조문 하이라이트
5. **DetectionCompare 페이지**: 관리자용 3탭 나란히 비교

## Complexity Tracking

| WARN | 근거 | 대안 |
|------|------|------|
| III. 외부 의존 격리 | 탭C가 법제처 API 추가 호출 필요 | 결과를 DB 캐시(LawRevisionReason)하여 반복 호출 방지. API 장애 시 탭C만 "데이터를 가져올 수 없습니다" 표시, 탭A/B 정상 동작 |
