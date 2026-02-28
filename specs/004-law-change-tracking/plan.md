# Implementation Plan: 개정법령 변경이력 관리

**Branch**: `004-law-change-tracking` | **Date**: 2026-02-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-law-change-tracking/spec.md`

## Summary

법제처 API 동기화 후 감지된 법령 변경 기록을 관리하고, 검토대상 조례를 자동 플래깅하여 부서 담당자의 검토 → 관리자 승인 워크플로우를 구현한다. 핵심은 (1) law_changes를 감지 로그 전용으로 단순화, (2) ordinances.revision_status 생명주기 도입, (3) 검토의견 승인 후 자동 상태 처리이다.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.3 (frontend)
**Primary Dependencies**: FastAPI >=0.104, SQLAlchemy 2.0 (async), React 18, Ant Design 5, TanStack Query 5, Celery 5.3
**Storage**: PostgreSQL 15, Redis 7 (session/broker)
**Testing**: pytest (backend), 프론트엔드 테스트 미구성
**Target Platform**: Docker (Linux containers), 브라우저(Chrome/Edge)
**Project Type**: Web application (SPA + REST API)
**Performance Goals**: 목록 조회 3초 이내 (SC-001), 상태 자동 전환 1초 이내 (SC-003)
**Constraints**: 관공서 보안성 검토 대상, 시큐어코딩 준수, Phase 2 Java eGovFrame 전환 대비 표준 SQL
**Scale/Scope**: 지자체 단위 사용 (수십~수백 사용자), 법령 수천 건, 조례 수백~수천 건

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | 원칙 | 준수 여부 | 근거 |
|---|------|----------|------|
| I | 데이터 무결성 | PASS | law_changes는 감지 로그로 삭제하지 않음. old_values/new_values로 원본+변경 보존 |
| II | 관심사 분리 | PASS | API(api/v1/) → Service(services/) → Model(models/) 3계층. 프론트엔드는 API 계약 통해 통신 |
| III | 외부 의존 격리 | PASS | 법제처 API 호출은 external/moleg_client.py에 격리. 동기화 로직은 services/에서 처리 |
| IV | 비차단 처리 | PASS | 동기화는 Celery 비동기 처리. 상태 전환은 API 호출 시 즉시 처리 |
| V | 환경 재현성 | PASS | Docker Compose로 전체 환경 선언. 환경 변수로 설정 관리 |
| VI | 보안 기본 적용 | PASS | JWT 인증, 역할 기반 접근 제어 (FR-016, FR-017). 사용자 입력 검증 (Pydantic) |
| VII | 사용자 중심 설계 | PASS | 역할별 기능 분리 (관리자: 승인/반려, 담당자: 검토의견 작성). 한국어 UI |

**Gate Result**: ALL PASS - Phase 0 진행 가능

## Project Structure

### Documentation (this feature)

```text
specs/004-law-change-tracking/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api-contracts.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── models/
│   ├── law_change.py          # 수정: ChangeStatus 제거, 감지 로그 전용
│   ├── ordinance.py           # 수정: needs_revision → revision_status 전환
│   └── ordinance_review.py    # 수정: review_result 값 제한 (2가지만)
├── schemas/
│   ├── ordinance.py           # 수정: LawChange 관련 스키마 단순화, revision_status 추가
│   └── review.py              # 수정: review_result enum 정리
├── services/
│   ├── law_sync_service.py    # 수정: 동기화 후 자동 플래깅 로직 추가
│   ├── ordinance_service.py   # 수정: revision_status 자동 전환, 수동 해제
│   └── review_service.py      # 수정: 승인 후 ordinance.revision_status 자동 처리
├── api/v1/
│   ├── law_changes.py         # 수정: approve/reject 엔드포인트 제거
│   ├── ordinances.py          # 수정: 상세 조회 시 자동 "검토중" 전환
│   └── reviews.py             # 수정: 승인 후 데이터 처리 로직
└── alembic/versions/
    └── YYYYMMDD_revision_status.py  # 신규: 마이그레이션

frontend/src/
├── pages/
│   ├── LawChangeList.tsx      # 수정: 승인/반려 UI 제거
│   ├── OrdinanceDetail.tsx    # 수정: 검토의견 작성 UI, 자동 상태 전환
│   └── ReviewList.tsx         # 수정: 승인/반려 UI 업데이트
├── services/
│   └── api.ts                 # 수정: API 호출 함수 업데이트
└── types/
    └── api.ts                 # 수정: 타입 정의 업데이트
```

**Structure Decision**: 기존 Web application 구조 (backend/ + frontend/) 유지. 신규 파일 생성 최소화, 기존 파일 수정 중심.

## Complexity Tracking

> Constitution Check 위반 없음 - 해당 없음
