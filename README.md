# Law Matcher

자치법규 개정 검토 시스템 - 상위법령 개정 시 자치법규(조례/규칙)의 개정 필요성을 자동으로 감지하고, 담당자의 검토 업무를 지원합니다.

---

## Table of Contents

- [Overview](#overview)
- [Core Rule](#core-rule)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Spec-Driven Development](#spec-driven-development)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Strategic Direction](#strategic-direction)
- [License](#license)

## Overview

지방자치단체에서 관리하는 조례와 규칙은 상위법령의 개정에 따라 함께 개정되어야 합니다. 이 시스템은 법제처 API를 활용하여 상위법령의 개정 여부를 자동으로 감지하고, 개정이 필요한 자치법규만 선별하여 담당자에게 알려줍니다.

### 주요 대상 사용자

| 역할 | 설명 |
|------|------|
| **사용자** (부서 담당자) | 소속 부서의 조례를 열람/검토하고, 개정 여부 결과를 저장 |
| **관리자** | 전체 부서 조례를 관리하고, 법령 동기화/연계 설정/부서 관리를 담당 |

## Core Rule

> **개정대상 판별**: 상위법령의 공포일자가 자치법규(조례)의 공포일자보다 **이후**이면, 해당 자치법규는 개정 검토 대상이다.

이 규칙을 기반으로 3가지 감지 방법(공포일자 비교, 조문 변경 추적, 제개정이유 분석)을 통해 개정 필요성을 종합 판단합니다.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│ PostgreSQL  │
│  React SPA  │     │   FastAPI   │     │             │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
              ┌─────▼─────┐ ┌────▼────┐
              │   Celery   │ │  Redis  │
              │Worker/Beat │ │ Broker  │
              └─────┬──────┘ └─────────┘
                    │
              ┌─────▼─────┐
              │ 법제처 API │
              │  (외부)    │
              └───────────┘
```

- **Frontend**: React SPA가 REST API를 통해 백엔드와 통신
- **Backend**: FastAPI가 비즈니스 로직 처리 및 API 제공
- **Celery Worker/Beat**: 법령 동기화 등 장시간 작업을 백그라운드에서 비동기 처리
- **Redis**: Celery 메시지 브로커 및 캐시
- **PostgreSQL**: 법령, 조례, 검토 이력 등 모든 데이터 영속 저장
- **법제처 API**: 상위법령 정보를 외부 API에서 수집 (격리된 클라이언트 모듈로 관리)

## Tech Stack

### Backend

| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.11+ | 서버 런타임 |
| FastAPI | >=0.104 | REST API 프레임워크 |
| SQLAlchemy | 2.0 (async) | ORM / 데이터 접근 |
| PostgreSQL | 15 | 관계형 데이터베이스 |
| Redis | 7 | 캐시 / 메시지 브로커 |
| Celery | 5.3 | 백그라운드 태스크 큐 |
| Alembic | >=1.12 | DB 마이그레이션 |

### Frontend

| 기술 | 버전 | 용도 |
|------|------|------|
| React | 18 | UI 라이브러리 |
| TypeScript | 5.3 | 타입 안전성 |
| Ant Design | 5 | UI 컴포넌트 프레임워크 |
| TanStack Query | 5 | 서버 상태 관리 |
| Vite | - | 빌드 도구 |

### Infrastructure

| 기술 | 용도 |
|------|------|
| Docker / Docker Compose | 컨테이너 오케스트레이션 |
| Celery Beat | 스케줄링 (정기 동기화) |

## Features

### 001. 로그인 및 인증

부서 단위 로그인 (Auth Phase A). 부서 선택 + 비밀번호로 인증하며, 관리자는 별도 비밀번호로 접근합니다.

### 002. 조례 관리

조례의 CRUD, 법제처 API 동기화, 부서 배정, 엑셀 내보내기/가져오기를 제공합니다. 조례 상태 생명주기(ACTIVE/ABOLISHED/EXCLUDED)를 관리합니다.

### 003. 상위법령 연결 관리

조례와 상위법령의 N:M 연결 관리, 조문 단위 매핑, Core Rule 기반 개정 필요 판별, 자동 추천(Jaccard 유사도) 기능을 포함합니다.

### 004. 법령 변경 추적

법제처 API를 통해 법령/조문의 변경사항을 자동 감지합니다. SHA-256 해시 기반 변경 감지, Celery Beat 정기 동기화, SSE 스트리밍 진행률 표시를 지원합니다.

### 005. 개정 감지 탭

3가지 감지 방법을 탭 UI로 제공합니다:

- **Tab A** (공포일자): 법령 공포일자 vs 조례 공포일자 비교
- **Tab B** (조문변경): 조문 단위 변경 이력 추적
- **Tab C** (제개정이유): 법령 제개정이유 텍스트 분석

### 006. LLM 검토의견 자동 생성

법령 제개정이유와 조례 정보를 LLM API에 전송하여 개정내용 요약 및 검토의견 초안을 자동 생성합니다. 1회 실행 원칙을 적용하며, AI 생성 결과는 참고용으로만 제공합니다.

## Getting Started

### Prerequisites

- Docker & Docker Compose
- (선택) Python 3.11+, Node.js 20+

### 1. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일에서 필수 값을 설정합니다:

| 변수 | 설명 | 필수 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 연결 문자열 | O |
| `REDIS_URL` | Redis 연결 문자열 | O |
| `MOLEG_API_KEY` | 법제처 API 키 | O |
| `ADMIN_PASSWORD` | 관리자 비밀번호 | O |
| `CELERY_BROKER_URL` | Celery 브로커 URL | O |
| `CELERY_RESULT_BACKEND` | Celery 결과 백엔드 | O |

### 2. Docker로 실행

```bash
docker-compose up -d
```

서비스 구성:

- **Backend**: `http://localhost:8000`
- **Frontend**: `http://localhost:3000`
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`

### 3. 개별 실행 (개발용)

#### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

#### Celery Worker

```bash
cd backend
celery -A celery_app worker --loglevel=info
```

#### Celery Beat (스케줄러)

```bash
cd backend
celery -A celery_app beat --loglevel=info
```

## Project Structure

```
law-matcher/
├── backend/                    # FastAPI 백엔드
│   ├── api/v1/                 # API 엔드포인트
│   │   ├── auth.py             #   인증
│   │   ├── ordinances.py       #   조례 관리
│   │   ├── laws.py             #   법령 관리
│   │   ├── articles.py         #   조문 관리
│   │   ├── reviews.py          #   검토 관리
│   │   └── ...
│   ├── models/                 # SQLAlchemy ORM 모델
│   ├── schemas/                # Pydantic 요청/응답 스키마
│   ├── services/               # 비즈니스 로직
│   ├── external/               # 외부 API 클라이언트 (법제처)
│   ├── core/                   # 설정, 보안, DB 연결
│   ├── alembic/                # DB 마이그레이션
│   ├── celery_app.py           # Celery 설정
│   └── main.py                 # FastAPI 앱 진입점
│
├── frontend/                   # React SPA
│   └── src/
│       ├── pages/              # 페이지 컴포넌트
│       ├── components/         # 재사용 UI 컴포넌트
│       ├── services/           # API 클라이언트
│       ├── contexts/           # React Context
│       └── types/              # TypeScript 타입
│
├── specs/                      # 피처 사양 문서
│   ├── 001-login/
│   ├── 002-ordinance-management/
│   ├── 003-law-mapping-management/
│   ├── 004-law-change-tracking/
│   ├── 005-revision-detection-tabs/
│   └── 006-llm-review-assistant/
│
├── .specify/                   # Spec-Driven Development 설정
│   ├── memory/constitution.md  # 프로젝트 헌법 (최상위 원칙)
│   ├── templates/              # 문서 템플릿
│   └── scripts/                # 자동화 스크립트
│
├── docker-compose.yml          # Docker 서비스 구성
├── .env.example                # 환경 변수 템플릿
└── CLAUDE.md                   # AI 어시스턴트 가이드라인
```

## Spec-Driven Development

이 프로젝트는 **Spec-Driven Development** 방법론을 따릅니다. 코드 작성 전에 사양(Spec)과 계획(Plan)을 먼저 수립하고, 검증된 계획을 기반으로 구현합니다.

### 개발 워크플로우

```
Constitution ──▶ Spec ──▶ Plan ──▶ Tasks ──▶ Implement
  (원칙)        (사양)    (설계)   (태스크)    (구현)
```

### 사용 가능한 명령어

| 명령어 | 설명 |
|--------|------|
| `/speckit.constitution` | 프로젝트 헌법 (최상위 원칙) 생성/수정 |
| `/speckit.feature` | 새 피처 사양(spec.md) 생성 |
| `/speckit.plan` | 구현 계획 생성 (research → data-model → contracts → plan) |
| `/speckit.tasks` | 태스크 목록 생성 |
| `/speckit.checklist` | 검증 체크리스트 생성 |

### 피처별 문서 구조

각 피처는 다음 문서들로 구성됩니다:

```
specs/{feature}/
├── spec.md              # 요구사항 정의 (User Story, FR, NFR)
├── research.md          # 기존 코드 분석 및 기술 조사
├── data-model.md        # ERD 및 테이블 스키마
├── contracts/
│   └── api-contracts.md # API 엔드포인트 계약
└── plan.md              # 구현 계획 및 Constitution Check
```

### Constitution (프로젝트 헌법)

모든 설계 및 구현 결정에 우선하는 8대 원칙:

| # | 원칙 | 핵심 내용 |
|---|------|----------|
| I | 데이터 무결성 | 변경 이력 삭제 금지, 해시 기반 감지, 원본/파생 데이터 보존 |
| II | 관심사 분리 | API → Service → Model 3계층 분리, 단방향 의존 |
| III | 외부 의존 격리 | 외부 API 클라이언트 별도 모듈화, 장애 격리 |
| IV | 비차단 처리 | I/O 비동기 처리, 장시간 작업 백그라운드 위임 |
| V | 환경 재현성 | 인프라 코드 선언, 환경 변수 관리 |
| VI | 보안 기본 적용 | 시큐어코딩 준수, 인증 필수, 비밀 정보 암호화 |
| VII | 사용자 중심 설계 | 한국어 UI, 역할별 메뉴 분리, 권한 강제 |
| VIII | AI 보조 활용 | AI 결과 참고용, 수동 실행, 1회 실행 원칙 |

## API Documentation

서버 실행 후 다음 경로에서 API 문서를 확인할 수 있습니다:

- **Swagger UI**: `http://localhost:8000/api/v1/docs`
- **ReDoc**: `http://localhost:8000/api/v1/redoc`

### 주요 API 경로

| 경로 | 설명 |
|------|------|
| `/api/v1/auth` | 인증 (로그인/로그아웃) |
| `/api/v1/ordinances` | 조례 관리 (CRUD, 동기화, 내보내기) |
| `/api/v1/laws` | 법령 관리 (조회, 동기화) |
| `/api/v1/articles` | 조문 관리 |
| `/api/v1/reviews` | 검토의견 관리 |
| `/api/v1/amendments` | 개정 감지 결과 |
| `/api/v1/dashboard` | 대시보드 통계 |
| `/api/v1/sync` | 법령 동기화 |
| `/health` | 헬스체크 |

## Development

### 테스트 실행

```bash
cd backend
pytest
```

### 코드 품질

```bash
cd backend
ruff check .
```

### DB 마이그레이션

```bash
cd backend
alembic upgrade head          # 마이그레이션 적용
alembic revision --autogenerate -m "description"  # 새 마이그레이션 생성
```

## Strategic Direction

### Phase 1 → Phase 2 전환

| | Phase 1 (현재) | Phase 2 (계획) |
|---|---|---|
| **Backend** | Python / FastAPI | Java / eGovFrame (전자정부표준프레임워크) |
| **Frontend** | React / TypeScript | 미정 (UI 흐름 동일 유지) |
| **인증** | 부서 단위 로그인 (Auth Phase A) | 개인별 로그인 (Auth Phase B) |

Phase 1은 Phase 2의 설계 기준(프로토타입)이 됩니다. API 계약, DB 스키마, UI 흐름은 전환 후에도 동일하게 유지됩니다.

## License

MIT
