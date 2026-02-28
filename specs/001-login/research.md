# Research: 001-login

**Date**: 2026-02-28
**Input**: specs/001-login/spec.md

## 기존 구현 현황

### 백엔드 인증 구조 (구현 완료)

| 파일 | 역할 | 상태 |
|------|------|------|
| `backend/core/security.py` | JWT 생성/검증, bcrypt 해시 | 구현됨 |
| `backend/core/config.py` | SECRET_KEY, PASSWORD 환경변수 | 구현됨 |
| `backend/api/v1/auth.py` | `POST /auth/login`, `GET /auth/me` | 구현됨 |
| `backend/services/auth_service.py` | 인증/등록/비밀번호 변경/리셋 로직 | 구현됨 |
| `backend/schemas/auth.py` | Pydantic 스키마 | 구현됨 |
| `backend/api/deps.py` | `get_current_user()`, `verify_admin_password()` | 구현됨 |
| `backend/models/user.py` | User ORM 모델 | 구현됨 |
| `backend/models/department.py` | Department ORM 모델 | 구현됨 |
| `backend/alembic/versions/add_users_table.py` | users 테이블 마이그레이션 | 구현됨 |

### 프론트엔드 인증 구조 (구현 완료)

| 파일 | 역할 | 상태 |
|------|------|------|
| `frontend/src/contexts/AuthContext.tsx` | 인증 상태 관리, 토큰 저장 | 구현됨 |
| `frontend/src/types/auth.ts` | TypeScript 인터페이스 | 구현됨 |
| `frontend/src/services/api.ts` | Axios 클라이언트, 인터셉터 | 구현됨 |
| `frontend/src/pages/Login.tsx` | 로그인 UI (관리자/부서) | 구현됨 |
| `frontend/src/pages/Register.tsx` | 회원가입 UI | 드래프트 (미연결) |
| `frontend/src/pages/ForgotPassword.tsx` | 비밀번호 재설정 UI | 드래프트 (미연결) |
| `frontend/src/components/ProtectedRoute.tsx` | 라우트 가드 | 구현됨 |
| `frontend/src/components/layout/MainLayout.tsx` | 역할별 메뉴 분리 | 구현됨 |

### 인증 플로우 (현재)

```
[프론트엔드]                              [백엔드]
Login.tsx                                 auth.py
  ├─ 관리자: login('admin', password)       POST /auth/login
  └─ 부서: login('user', password, dept)     ├─ DB에서 users 조회
                                              ├─ bcrypt 비밀번호 검증
                                              ├─ JWT 토큰 생성 (HS256, 24h)
AuthContext.tsx                                └─ TokenResponse 반환
  ├─ localStorage에 토큰/유저 저장
  ├─ Axios 인터셉터로 Bearer 토큰 첨부
  └─ 개발 모드: VITE_DEV_BYPASS_AUTH=true → 자동 관리자 주입
```

### user_type 매핑 구조

```
DB 저장          백엔드 API       프론트엔드
─────────       ──────────      ──────────
"GENERAL"   →   "ADMIN"     →   user_type: 'ADMIN'
"DEPARTMENT" →  "USER"      →   user_type: 'USER'
```

## 미구현/미완성 항목

| 항목 | spec 요구사항 | 현재 상태 | 필요 작업 |
|------|--------------|-----------|-----------|
| 비밀번호 변경 API | FR-009 | AuthService에 로직 있음, API 라우트 없음 | 엔드포인트 추가 |
| 회원가입 API | FR-012 (Phase B) | AuthService에 로직 있음, API 라우트 없음 | 추후 |
| 비밀번호 재설정 | FR-013 (Phase B) | AuthService+Redis 로직 있음, API 라우트 없음 | 추후 |
| 프론트엔드 Register | Phase B | 컴포넌트 존재, auth context 미연결 | 추후 |
| 프론트엔드 ForgotPassword | Phase B | 컴포넌트 존재, API 미연결 | 추후 |
| 토큰 무효화/로그아웃 | FR-006 | 클라이언트 측만 (localStorage 삭제) | 서버 사이드 토큰 무효화는 Phase B |

## 기술 스택

- **JWT**: python-jose[cryptography] >=3.3.0, HS256
- **Password**: passlib >=1.7.4, bcrypt==4.1.2
- **토큰 저장 (리셋)**: Redis >=5.0.0
- **API 프레임워크**: FastAPI, HTTPBearer 스키마
- **프론트엔드 HTTP**: Axios, Bearer 토큰 인터셉터
- **상태 관리**: React Context (AuthContext)
- **UI**: Ant Design 5 (Form, Input, Select, Button)

## 핵심 발견사항

1. **Auth Phase A 핵심 기능은 대부분 구현 완료** - 로그인/로그아웃/역할 분리/라우트 보호 모두 동작
2. **비밀번호 변경만 API 라우트 노출 필요** (서비스 로직은 이미 있음)
3. **Phase B 준비 코드가 이미 존재** - Register, ForgotPassword 컴포넌트, AuthService 메서드
4. **보안 취약점**: 기본 비밀번호 "admin123", "user123" 하드코딩 (Security Notes에 문서화됨)
5. **USER_PASSWORD 환경변수가 config에 정의되어 있지만 로그인 로직에서 미사용** - DB 기반 인증으로 전환됨
