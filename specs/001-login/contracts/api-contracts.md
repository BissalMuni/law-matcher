# API Contracts: 001-login

**Date**: 2026-02-28
**Base Path**: `/api/v1`

## 엔드포인트 목록

| Method | Path | 인증 | 설명 | 상태 |
|--------|------|------|------|------|
| POST | `/auth/login` | 불필요 | 로그인 | 구현됨 |
| GET | `/auth/me` | JWT | 현재 사용자 정보 | 구현됨 |
| POST | `/auth/change-password` | JWT | 비밀번호 변경 | **미구현** |
| POST | `/auth/register` | 불필요 | 회원가입 (Phase B) | 추후 |
| POST | `/auth/forgot-password` | 불필요 | 비밀번호 재설정 요청 (Phase B) | 추후 |
| POST | `/auth/reset-password` | 불필요 | 비밀번호 재설정 확인 (Phase B) | 추후 |

---

## POST /auth/login

**인증**: 불필요
**spec 참조**: FR-001, FR-002, FR-003, FR-008

### Request

```json
{
  "username": "admin",          // "admin" 또는 "user"
  "password": "string",         // 최소 8자
  "department_name": "string"   // 부서 로그인 시만 (선택)
}
```

### Response 200

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "user_type": "ADMIN",       // "ADMIN" | "USER"
    "full_name": "관리자",
    "department_name": null     // 부서 사용자인 경우 부서명
  }
}
```

### Error Responses

| 상태 | 조건 | 응답 |
|------|------|------|
| 401 | 잘못된 비밀번호 | `{"detail": "비밀번호가 일치하지 않습니다"}` |
| 401 | 사용자 없음 | `{"detail": "사용자를 찾을 수 없습니다"}` |
| 403 | is_active=false | `{"detail": "비활성화된 계정입니다"}` |

---

## GET /auth/me

**인증**: Bearer JWT
**spec 참조**: FR-003, FR-004

### Request Headers

```
Authorization: Bearer eyJ...
```

### Response 200

```json
{
  "id": 1,
  "username": "admin",
  "user_type": "ADMIN",
  "full_name": "관리자",
  "department_name": null
}
```

### Error Responses

| 상태 | 조건 | 응답 |
|------|------|------|
| 401 | 토큰 없음/만료/유효하지 않음 | `{"detail": "인증 정보가 유효하지 않습니다"}` |

---

## POST /auth/change-password (**신규 구현 필요**)

**인증**: Bearer JWT
**spec 참조**: FR-009

### Request

```json
{
  "current_password": "string",   // 현재 비밀번호
  "new_password": "string"        // 새 비밀번호 (최소 8자)
}
```

### Response 200

```json
{
  "message": "비밀번호가 변경되었습니다"
}
```

### Error Responses

| 상태 | 조건 | 응답 |
|------|------|------|
| 401 | 현재 비밀번호 불일치 | `{"detail": "현재 비밀번호가 일치하지 않습니다"}` |
| 422 | 새 비밀번호 8자 미만 | Pydantic validation error |

---

## 공통 보안 헤더

### 관리 API 추가 인증 (FR-010)

민감한 관리 API(법령 동기화 등)는 JWT 외에 추가 인증 필요:

```
X-Admin-Password: {ADMIN_PASSWORD}
```

이 헤더는 `backend/api/deps.py`의 `verify_admin_password()` 의존성으로 검증.

---

## JWT 토큰 구조

```json
{
  "sub": "1",                   // user.id (문자열)
  "exp": 1709251200            // 만료 시간 (발급 후 24시간)
}
```

- 알고리즘: HS256
- 서명 키: `SECRET_KEY` 환경변수
- 만료: 1440분 (24시간)
