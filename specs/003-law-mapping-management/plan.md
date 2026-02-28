# Implementation Plan: 상위법령 연결 관리 기능

**Branch**: `003-law-mapping-management` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-law-mapping-management/spec.md`

## Summary

조례와 상위법령의 N:M 연결 관리, 조문 단위 매핑, Core Rule(공포일자 비교) 기반 개정 필요 판별, 자동 추천 기능을 구현한다. **기존 코드베이스에 전부 구현되어 있으며**, 주요 작업은 (1) 에러 복구 로직 추가, (2) 에러 메시지 한국어화, (3) 조문 매핑 정합성 경고 보강이다.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.3 (frontend)
**Primary Dependencies**: FastAPI >=0.104, SQLAlchemy 2.0 (async), React 18, Ant Design 5, TanStack Query 5, Celery 5.3
**Storage**: PostgreSQL 15, Redis 7 (Celery broker)
**Testing**: pytest (backend)
**Target Platform**: Docker (Linux containers), 브라우저 (Chrome/Edge)
**Project Type**: Web application (SPA + REST API)
**Performance Goals**: 매핑 CRUD 2초 이내 (SC-001), Core Rule 판별 100% 정확 (SC-002)
**Constraints**: 관공서 보안성 검토 대상, 시큐어코딩 준수, Phase 2 Java eGovFrame 전환 대비
**Scale/Scope**: 법령 수천 건, 조문 수만 건, 조례 수백~수천 건

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | 원칙 | 준수 여부 | 근거 |
|---|------|----------|------|
| I | 데이터 무결성 | PASS | 변경 이력(LawChange, ArticleChange) 삭제 안 함. content_hash 기반 재현 가능한 감지 |
| II | 관심사 분리 | PASS | API(laws.py, articles.py) → Service(law_sync_service, article_service) → Model 3계층 |
| III | 외부 의존 격리 | PASS | 법제처 API는 moleg_client.py에 격리. SSE 스트리밍으로 동기화 진행률 표시 |
| IV | 비차단 처리 | PASS | 법령/조문 동기화는 Celery + SSE. 매핑 CRUD는 즉시 응답 |
| V | 환경 재현성 | PASS | Docker Compose, 환경변수, Celery Beat 스케줄 선언 |
| VI | 보안 기본 적용 | PASS | JWT 인증, 관리 API AdminPassword 검증, Pydantic 입력 검증 |
| VII | 사용자 중심 설계 | PASS | 역할별 기능 분리, 한국어 UI, Core Rule 결과 시각적 표시 |
| VIII | AI 보조 활용 | N/A | US6 자동 추천은 키워드 기반 (Jaccard 유사도), LLM 아님 |

**Gate Result**: ALL PASS

## Project Structure

### Documentation (this feature)

```text
specs/003-law-mapping-management/
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
│   ├── law.py                     # 기존: 변경 없음
│   ├── article.py                 # 기존: 변경 없음
│   ├── law_change.py              # 기존: 변경 없음
│   ├── article_change.py          # 기존: 변경 없음
│   ├── ordinance_law_mapping.py   # 기존: 변경 없음
│   └── ordinance_article_mapping.py # 기존: 변경 없음
├── schemas/
│   └── ordinance.py               # 수정: 에러 응답 메시지 한국어화
├── services/
│   ├── law_sync_service.py        # 수정: API 재시도 로직, 에러 메시지
│   ├── article_service.py         # 수정: 조문 삭제 시 매핑 영향 경고
│   └── ordinance_service.py       # 수정: 매핑 에러 메시지 한국어화
├── api/v1/
│   ├── laws.py                    # 수정: 에러 응답 한국어화
│   ├── articles.py                # 수정: 에러 응답 한국어화
│   └── ordinances.py              # 수정: 매핑 관련 에러 한국어화
└── external/
    └── moleg_client.py            # 수정: 재시도 로직 추가 (tenacity 또는 수동)

frontend/src/
├── pages/
│   ├── OrdinanceDetail.tsx        # 수정: 조문 삭제 경고 UI
│   ├── ArticleList.tsx            # 기존: 변경 없음
│   ├── ArticleDetail.tsx          # 기존: 변경 없음
│   └── RevisionNeededList.tsx     # 기존: 변경 없음
└── services/
    └── api.ts                     # 기존: 변경 없음
```

**Structure Decision**: 기존 Web application 구조 유지. 신규 파일 없음 — 기존 파일의 에러 처리/메시지 보강만 수행.

## 구현 범위

### 구현 대상

| User Story | 상태 | 작업 |
|------------|------|------|
| US1 상위법령 연결 추가 | 구현됨 | 에러 메시지 한국어화 |
| US2 연결 목록 조회 | 구현됨 | 변경 없음 |
| US3 연결 수정/삭제 | 구현됨 | 마지막 법령 삭제 시 경고 보강 |
| US4 상위법령 없음 | 구현됨 | 변경 없음 |
| US5 조문 단위 매핑 | 구현됨 | 조문 삭제 시 영향 경고 |
| US6 자동 추천 | 구현됨 | 변경 없음 (SC-003 검증 필요) |

### 핵심 보강 사항

#### 1. API 재시도 로직

법제처 API 호출 실패 시 재시도:
- 최대 2회 재시도, 지수 백오프 (1초 → 2초)
- 타임아웃: 30초
- moleg_client.py 또는 service 계층에서 처리

#### 2. 에러 메시지 한국어화

| 상황 | 현재 | 변경 |
|------|------|------|
| 매핑 중복 | IntegrityError | "이 상위법령은 이미 연결되어 있습니다" |
| 법령 미발견 | 404 | "법제처에서 해당 법령을 찾을 수 없습니다" |
| API 타임아웃 | 500 | "법제처 서버 응답이 지연되고 있습니다" |

#### 3. 조문 매핑 정합성 경고

조문 동기화 시 삭제된 조문에 매핑이 있으면:
- ArticleChange(type='deleted') 생성 시 영향받는 매핑 수 기록
- 프론트엔드에서 "매핑된 조문이 삭제되었습니다" 경고 표시

## Complexity Tracking

> Constitution Check 위반 없음 - 해당 없음
