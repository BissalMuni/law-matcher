# Implementation Plan: 로그인 기능

**Branch**: `001-login` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-login/spec.md`

## Summary

부서 단위 로그인(Auth Phase A)과 관리자 로그인을 구현하며, JWT 기반 인증, 역할별 메뉴 분리, 비밀번호 변경 기능을 제공한다. **기존 코드베이스에 대부분 구현되어 있으며**, 주요 작업은 (1) 비밀번호 변경 API 엔드포인트 노출, (2) 프론트엔드 비밀번호 변경 UI 추가, (3) 누락된 에러 처리 보강이다. Auth Phase B(개인별 로그인)는 설계만 고려하고 구현하지 않는다.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.3 (frontend)
**Primary Dependencies**: FastAPI >=0.104, SQLAlchemy 2.0 (async), React 18, Ant Design 5, TanStack Query 5
**Storage**: PostgreSQL 15, Redis 7 (비밀번호 리셋 토큰)
**Testing**: pytest (backend)
**Target Platform**: Docker (Linux containers), 브라우저 (Chrome/Edge)
**Project Type**: Web application (SPA + REST API)
**Performance Goals**: 로그인 응답 1초 이내 (SC-002)
**Constraints**: 관공서 보안성 검토 대상, 시큐어코딩 준수, Phase 2 Java eGovFrame 전환 대비
**Scale/Scope**: 지자체 단위 (수십~수백 사용자)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | 원칙 | 준수 여부 | 근거 |
|---|------|----------|------|
| I | 데이터 무결성 | PASS | 검토 데이터 Phase B 이관 고려 (SC-003) |
| II | 관심사 분리 | PASS | API(auth.py) → Service(auth_service.py) → Model(user.py) 3계층 |
| III | 외부 의존 격리 | PASS | 인증은 내부 로직, 외부 API 호출 없음 |
| IV | 비차단 처리 | PASS | 로그인/로그아웃 즉시 응답 |
| V | 환경 재현성 | PASS | SECRET_KEY, PASSWORD 환경 변수 관리, Docker Compose 선언 |
| VI | 보안 기본 적용 | PASS | JWT+bcrypt, 개발 환경만 우회 허용, 역할 기반 접근 제어 |
| VII | 사용자 중심 설계 | PASS | 역할별 메뉴 분리 (FR-007), 한국어 UI, 프론트+백엔드 양쪽 권한 강제 |

**Gate Result**: ALL PASS

## Project Structure

### Documentation (this feature)

```text
specs/001-login/
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
├── core/
│   ├── security.py          # 기존: JWT, bcrypt 유틸리티
│   └── config.py            # 기존: 환경변수 설정
├── models/
│   ├── user.py              # 기존: User ORM 모델
│   └── department.py        # 기존: Department ORM 모델
├── schemas/
│   └── auth.py              # 기존: Pydantic 스키마
├── services/
│   └── auth_service.py      # 기존: 인증 비즈니스 로직 (change_password 포함)
├── api/
│   ├── deps.py              # 기존: get_current_user, verify_admin_password
│   └── v1/
│       └── auth.py          # 수정: change-password 엔드포인트 추가
└── alembic/versions/
    └── add_users_table.py   # 기존: 마이그레이션 (변경 없음)

frontend/src/
├── contexts/
│   └── AuthContext.tsx       # 기존: 인증 상태 관리
├── types/
│   └── auth.ts              # 기존: TypeScript 인터페이스
├── services/
│   └── api.ts               # 수정: changePassword API 호출 추가
├── pages/
│   ├── Login.tsx             # 기존: 로그인 UI
│   └── ChangePassword.tsx    # 신규: 비밀번호 변경 UI
├── components/
│   ├── ProtectedRoute.tsx    # 기존: 라우트 가드
│   └── layout/
│       └── MainLayout.tsx    # 수정: 비밀번호 변경 메뉴 항목 추가
└── App.tsx                   # 수정: /change-password 라우트 추가
```

**Structure Decision**: 기존 Web application 구조 (backend/ + frontend/) 유지. 신규 파일 최소화 — 백엔드는 기존 auth.py에 엔드포인트 추가, 프론트엔드는 ChangePassword 페이지 1개만 신규.

## 구현 범위 (Auth Phase A only)

### 구현 대상 (US1~US4)

| User Story | 상태 | 작업 |
|------------|------|------|
| US1 부서 로그인 | 구현됨 | 에러 처리 보강 |
| US2 관리자 로그인 | 구현됨 | 에러 처리 보강 |
| US3 로그아웃 | 구현됨 | 변경 없음 |
| US4 비밀번호 변경 | **미구현** | API 엔드포인트 + UI 신규 |

### 제외 (Auth Phase B)

| User Story | 사유 |
|------------|------|
| US5 개인별 로그인 | Phase B. 서비스 로직/UI 드래프트 존재, 추후 연결 |

## Complexity Tracking

> Constitution Check 위반 없음 - 해당 없음
