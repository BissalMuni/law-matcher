# Implementation Plan: 조례 관리 기능

**Branch**: `002-ordinance-management` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-ordinance-management/spec.md`

## Summary

조례의 CRUD, 법제처 API 동기화, 부서 배정, 엑셀 내보내기/가져오기, 상세 조회를 구현한다. **기존 코드베이스에 대부분 구현되어 있으며**, 주요 작업은 (1) 조례 상태 생명주기 확장(ABOLISHED 추가), (2) 동기화 시 폐지 감지 로직, (3) 에러 처리 및 한국어 메시지 보강이다.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.3 (frontend)
**Primary Dependencies**: FastAPI >=0.104, SQLAlchemy 2.0 (async), React 18, Ant Design 5, TanStack Query 5, Celery 5.3
**Storage**: PostgreSQL 15, Redis 7 (Celery broker)
**Testing**: pytest (backend)
**Target Platform**: Docker (Linux containers), 브라우저 (Chrome/Edge)
**Project Type**: Web application (SPA + REST API)
**Performance Goals**: 조례 목록 로딩 2초 이내 (SC-001, 1000건 기준)
**Constraints**: 관공서 보안성 검토 대상, 시큐어코딩 준수, Phase 2 Java eGovFrame 전환 대비
**Scale/Scope**: 지자체 단위 (조례 수백~수천 건, 사용자 수십~수백 명)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | 원칙 | 준수 여부 | 근거 |
|---|------|----------|------|
| I | 데이터 무결성 | PASS | 폐지 조례 삭제 대신 status='ABOLISHED' 전환. 검토이력/법령연결 보존 |
| II | 관심사 분리 | PASS | API(ordinances.py) → Service(ordinance_service.py) → Model(ordinance.py) 3계층 |
| III | 외부 의존 격리 | PASS | 법제처 API는 external/moleg_client.py에 격리 |
| IV | 비차단 처리 | PASS | 일괄 동기화는 Celery 백그라운드 처리 |
| V | 환경 재현성 | PASS | Docker Compose, 환경변수 관리 |
| VI | 보안 기본 적용 | PASS | JWT 인증, 관리 API는 AdminPassword 추가 검증, Pydantic 입력 검증 |
| VII | 사용자 중심 설계 | PASS | 부서별 접근 제어(FR-003), 역할별 UI 분리, 한국어 메시지 |
| VIII | AI 보조 활용 | N/A | 이 기능에 AI 없음 |

**Gate Result**: ALL PASS

## Project Structure

### Documentation (this feature)

```text
specs/002-ordinance-management/
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
│   ├── ordinance.py           # 수정: status 값에 ABOLISHED 추가
│   ├── department.py          # 기존: 변경 없음
│   ├── ordinance_law_mapping.py   # 기존: 변경 없음
│   └── ordinance_review.py    # 기존: 변경 없음
├── schemas/
│   └── ordinance.py           # 수정: status 필터 파라미터 추가, 동기화 응답에 abolished 건수
├── services/
│   └── ordinance_service.py   # 수정: sync 시 폐지 감지, 목록 조회 시 status 기본 필터
├── api/v1/
│   └── ordinances.py          # 수정: status 필터 파라미터, 에러 메시지 한국어화
├── external/
│   └── moleg_client.py        # 기존: 변경 없음
└── alembic/versions/
    └── YYYYMMDD_add_abolished_status.py  # 신규: 기존 폐지 조례 status 갱신

frontend/src/
├── pages/
│   ├── OrdinanceList.tsx      # 수정: status 필터 UI 추가
│   └── OrdinanceDetail.tsx    # 수정: 폐지 상태 배지 표시
├── services/
│   └── api.ts                 # 수정: status 파라미터 추가
└── types/
    └── api.ts                 # 수정: status 타입 추가
```

**Structure Decision**: 기존 Web application 구조 (backend/ + frontend/) 유지. 신규 파일 최소화 — 마이그레이션 1개만 신규, 나머지는 기존 파일 수정.

## 구현 범위

### 구현 대상

| User Story | 상태 | 작업 |
|------------|------|------|
| US1 조례 목록 조회 | 구현됨 | status 필터 추가, 기본값 ACTIVE |
| US2 조례 등록 | 구현됨 | 에러 메시지 한국어화 |
| US3 법제처 동기화 | 구현됨 | 폐지 감지 로직 + 응답에 abolished 건수 추가 |
| US4 조례 상세 조회 | 구현됨 | 폐지 상태 배지 표시 |
| US5 부서 일괄 배정 | 구현됨 | 변경 없음 |
| US6 엑셀 내보내기 | 구현됨 | 폐지 조례 기본 제외 |

### 핵심 보강 사항

#### 1. 조례 상태 생명주기 (ABOLISHED)

- `status` 필드에 `ABOLISHED` 값 추가
- 동기화 시 `revision_type='폐지'`인 조례 자동 전환
- 폐지 조례는 목록 기본 필터에서 제외 (관리자가 옵션으로 표시 가능)
- 폐지 조례의 기존 데이터(검토이력, 상위법령) 보존 (I. 데이터 무결성)
- 폐지 조례는 개정 검토 대상에서 자동 제외

#### 2. 에러 처리 한국어화

- 중복 조례 등록: "이미 등록된 조례입니다 (코드: {code})"
- API 타임아웃: "법제처 서버 응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요"
- 동기화 실패: "동기화 중 {n}건의 오류가 발생했습니다"

#### 3. 데이터 마이그레이션

- 기존 `revision_type='폐지'`인 조례를 `status='ABOLISHED'`로 일괄 갱신
- 데이터 백업 후 마이그레이션 실행

## Complexity Tracking

> Constitution Check 위반 없음 - 해당 없음
