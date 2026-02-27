# 사용자 인증 시스템 구현 진행 상황

## 📋 전체 계획
상세 계획은 `/home/user/.claude/plans/fluffy-herding-origami.md` 참조

## ✅ 완료된 작업

### Phase 1: 백엔드 인증 기반 (완료)

#### 1. ✅ requirements.txt 업데이트
- **파일**: `/backend/requirements.txt`
- **변경사항**: JWT 및 비밀번호 해싱 라이브러리 추가
```
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

#### 2. ✅ User 모델 생성
- **파일**: `/backend/models/user.py` (신규 생성)
- **내용**:
  - User 모델 정의
  - department_id로 Department와 외래키 관계
  - email, username (unique)
  - user_type: "DEPARTMENT" | "GENERAL"
  - created_reviews, updated_reviews relationship

#### 3. ✅ Department 모델 수정
- **파일**: `/backend/models/department.py`
- **변경사항**: users relationship 추가
```python
users: Mapped[List["User"]] = relationship(back_populates="department")
```

#### 4. ✅ models/__init__.py 업데이트
- **파일**: `/backend/models/__init__.py`
- **변경사항**: User 모델 import 및 __all__에 추가

#### 5. ✅ Security 유틸리티 생성
- **파일**: `/backend/core/security.py` (신규 생성)
- **내용**:
  - `verify_password()`: 비밀번호 검증
  - `get_password_hash()`: 비밀번호 해싱
  - `create_access_token()`: JWT 토큰 생성
  - `decode_access_token()`: JWT 토큰 디코딩

#### 6. ✅ JWT 설정 추가
- **파일**: `/backend/core/config.py`
- **변경사항**: JWT Authentication 섹션 추가
```python
SECRET_KEY: str = "your-secret-key-change-this-in-production-min-32-chars"
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
```

#### 7. ✅ 인증 스키마 생성
- **파일**: `/backend/schemas/user.py` (신규 생성)
- **내용**:
  - `UserBase`, `UserCreate`, `UserUpdate`
  - `UserBriefResponse`: 간단한 사용자 정보
  - `UserResponse`: 전체 사용자 정보
  - `UserWithDepartmentResponse`: 부서 정보 포함

- **파일**: `/backend/schemas/auth.py` (신규 생성)
- **내용**:
  - `RegisterRequest`: 회원가입 요청
  - `LoginRequest`: 로그인 요청
  - `TokenResponse`: JWT 토큰 응답
  - `PasswordChangeRequest`: 비밀번호 변경 요청

#### 8. ✅ 인증 서비스 생성
- **파일**: `/backend/services/auth_service.py` (신규 생성)
- **내용**:
  - `get_by_username()`: username으로 사용자 조회
  - `get_by_email()`: email로 사용자 조회
  - `authenticate()`: 사용자 인증
  - `register()`: 사용자 등록
  - `change_password()`: 비밀번호 변경
  - `create_token()`: JWT 토큰 생성

#### 9. ✅ 인증 API 엔드포인트 생성
- **파일**: `/backend/api/v1/auth.py` (신규 생성)
- **내용**:
  - `POST /auth/register`: 회원가입
  - `POST /auth/login`: 로그인
  - `GET /auth/me`: 현재 사용자 정보
  - `POST /auth/change-password`: 비밀번호 변경

#### 10. ✅ deps.py에 인증 dependency 추가
- **파일**: `/backend/api/deps.py`
- **변경사항**: `get_current_user()` dependency 추가
  - HTTPBearer security scheme
  - JWT 토큰 검증
  - DB에서 사용자 조회
  - 활성 사용자 확인

#### 11. ✅ API 라우터 등록
- **파일**: `/backend/api/v1/router.py`
- **변경사항**: auth 라우터 추가
```python
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"]
)
```

#### 12. ✅ users 테이블 마이그레이션 생성
- **파일**: `/backend/alembic/versions/add_users_table.py` (신규 생성)
- **내용**: users 테이블 생성 마이그레이션
  - id, email, username, hashed_password
  - full_name, user_type, department_id
  - is_active, created_at, updated_at
  - 인덱스: email, username (unique), user_type

### Phase 2: 검토 의견 사용자 추적 (일부 완료)

#### 13. ✅ OrdinanceReview 모델 수정
- **파일**: `/backend/models/ordinance_review.py`
- **변경사항**: User 추적 필드 추가
  - `created_by_id`: 작성자 ID (User FK)
  - `updated_by_id`: 수정자 ID (User FK)
  - `created_by`, `updated_by` relationship 추가

#### 14. ✅ ordinance_reviews 테이블 마이그레이션 생성
- **파일**: `/backend/alembic/versions/add_user_tracking_to_reviews.py` (신규 생성)
- **내용**: ordinance_reviews 테이블에 사용자 추적 컬럼 추가
  - created_by_id, updated_by_id 컬럼 추가
  - users 테이블로의 외래키 제약 조건 추가

---

### Phase 2: 검토 의견 사용자 추적 (완료)

#### 13. ✅ 마이그레이션 merge head 생성
- **파일**: `/backend/alembic/versions/merge_heads_before_auth.py` (신규 생성)
- **내용**: 기존 마이그레이션 헤드 병합

#### 14. ✅ 백엔드 의존성 설치 및 재빌드
- Docker 컨테이너 재빌드 완료
- bcrypt 버전 4.1.2로 고정
- 모든 서비스 정상 실행 확인
  - Backend: http://localhost:8000
  - Frontend: http://localhost:3000
  - Database, Redis, Worker 정상 실행

#### 15. ✅ 회원가입/로그인 API 테스트
- **테스트 완료 항목**:
  - ✅ POST /api/v1/auth/register (회원가입) - 성공
  - ✅ JWT 토큰 생성 확인
  - ✅ 사용자 정보 응답 확인 (id: 1, user_type: GENERAL)

**테스트 결과**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "test@example.com",
    "username": "testuser",
    "user_type": "GENERAL",
    "is_active": true
  }
}
```

## 🚧 다음 단계

### 1. ✅ 마이그레이션 실행 완료

**실행 결과**:
```bash
alembic current
# add_user_tracking_to_reviews (head)
```

**확인 완료**:
- ✅ users 테이블 생성 완료
- ✅ department_id 외래키 생성 완료
- ✅ 인덱스 생성 완료 (email, username unique, user_type)
- ✅ ordinance_reviews 테이블에 created_by_id, updated_by_id 컬럼 추가 완료
- ✅ 외래키 제약 조건 생성 완료 (created_by_id, updated_by_id → users)

---

## 📝 Phase 2: 검토 의견 사용자 추적 (계속) - 아직 미완성

### 2. ⏳ schemas/review.py 스키마 수정
**파일**: `/backend/schemas/review.py`
- `OrdinanceReviewCreate`: reviewer 필드 제거 (자동 설정)
- `OrdinanceReviewResponse`: created_by, updated_by (UserBriefResponse) 추가

### 3. ⏳ services/review_service.py 수정
**파일**: `/backend/services/review_service.py`
- 검토 의견 생성 시 created_by_id 자동 설정
- 검토 의견 수정 시 updated_by_id 자동 설정

### 4. ⏳ api/v1/reviews.py API 수정
**파일**: `/backend/api/v1/reviews.py`
- current_user dependency 추가
- 권한 검증 로직 추가 (본인 작성 의견만 수정/삭제 가능)

---

## 📝 Phase 3: 프론트엔드 인증 UI (완료)

### 5. ✅ 프론트엔드 타입 정의
**파일**: `/frontend/src/types/auth.ts` (신규 생성)
- User, LoginRequest, RegisterRequest, TokenResponse 타입 정의
- AuthContextType 타입 정의

### 6. ✅ AuthContext 생성
**파일**: `/frontend/src/contexts/AuthContext.tsx` (신규 생성)
- 로그인/로그아웃 상태 관리
- useAuth hook 제공
- JWT 토큰 localStorage 자동 저장/복원
- 토큰 유효성 자동 검증

### 7. ✅ API 서비스 수정
**파일**: `/frontend/src/services/api.ts`
- JWT 토큰 자동 인터셉터 추가
- authApi (login, register, me, changePassword) 추가
- 401 오류 자동 처리 (토큰 만료 시 자동 로그아웃)

### 8. ✅ 인증 페이지 생성
**파일**:
- `/frontend/src/pages/Landing.tsx` (신규 생성): 랜딩 페이지 (시스템 소개)
- `/frontend/src/pages/Login.tsx` (신규 생성): 로그인 페이지
- `/frontend/src/pages/Register.tsx` (신규 생성): 회원가입 페이지 (일반/부서 담당자 선택)

### 9. ✅ ProtectedRoute 컴포넌트 생성
**파일**: `/frontend/src/components/ProtectedRoute.tsx` (신규 생성)
- 인증 확인 후 라우팅
- 미인증 사용자 자동 리디렉션

### 10. ✅ App.tsx 라우팅 수정
**파일**: `/frontend/src/App.tsx`
- AuthProvider로 전체 앱 래핑
- Landing, Login, Register 라우트 추가
- ProtectedRoute 적용 (모든 메인 페이지 보호)

### 11. ✅ MainLayout 수정
**파일**: `/frontend/src/components/layout/MainLayout.tsx`
- 헤더에 사용자 정보 표시 (이름, 사용자 유형)
- 사용자 드롭다운 메뉴 추가
- 로그아웃 버튼 추가

---

---

## 📝 Phase 3 완료 내용 요약

### ✅ 구현된 기능
1. **인증 시스템 UI**
   - 랜딩 페이지: 시스템 소개 및 로그인/회원가입 링크
   - 로그인 페이지: 사용자명/비밀번호 로그인
   - 회원가입 페이지: 일반 사용자/부서 담당자 선택 가능

2. **상태 관리**
   - AuthContext를 통한 전역 인증 상태 관리
   - JWT 토큰 localStorage 자동 저장
   - 페이지 새로고침 시 인증 상태 자동 복원

3. **보안 기능**
   - ProtectedRoute로 미인증 사용자 차단
   - JWT 토큰 자동 인터셉터 (모든 API 요청에 자동 추가)
   - 401 오류 자동 처리 (토큰 만료 시 자동 로그아웃)

4. **사용자 경험**
   - 헤더에 사용자 정보 표시
   - 드롭다운 메뉴로 로그아웃 기능
   - 로그인 후 자동으로 메인 페이지 이동

### 📂 생성된 파일 목록
- `/frontend/src/types/auth.ts`
- `/frontend/src/contexts/AuthContext.tsx`
- `/frontend/src/pages/Landing.tsx`
- `/frontend/src/pages/Login.tsx`
- `/frontend/src/pages/Register.tsx`
- `/frontend/src/components/ProtectedRoute.tsx`

### 🔧 수정된 파일 목록
- `/frontend/src/services/api.ts`
- `/frontend/src/App.tsx`
- `/frontend/src/components/layout/MainLayout.tsx`

---

## 📝 Phase 4: 검토 의견 UI 자동화 (대기 중)

### 12. ⏳ OrdinanceDetail 페이지 수정
**파일**: `/frontend/src/pages/OrdinanceDetail.tsx`
- 검토 의견 모달에서 reviewer 필드 제거 (자동 설정)
- 작성자 정보 표시 (created_by)
- 본인 작성 의견만 수정/삭제 가능하도록 권한 체크

---

## 📝 Phase 5: 테스트 및 검증 (대기 중)

### 13. ⏳ 백엔드 API 테스트 (추가)
- 회원가입/로그인 API 테스트
- JWT 토큰 인증 테스트
- 검토 의견 CRUD 권한 테스트

### 14. ⏳ 프론트엔드 통합 테스트
- 로그인/로그아웃 플로우 테스트
- 인증 상태 유지 테스트
- 검토 의견 작성/수정/삭제 권한 테스트

---

## 🔧 환경 설정 필요 사항

### .env 파일에 추가 필요
```env
# JWT Settings (프로덕션에서는 반드시 변경!)
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars-XXXXXXXXXXXXXXXX
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

**SECRET_KEY 생성 방법**:
```python
import secrets
print(secrets.token_urlsafe(32))
```

---

## 📚 참고 파일

### 주요 파일 경로
- **계획 문서**: `/home/user/.claude/plans/fluffy-herding-origami.md`
- **User 모델**: `/backend/models/user.py`
- **Security**: `/backend/core/security.py`
- **Config**: `/backend/core/config.py`

### 핵심 구현 파일 (18개)
**백엔드**:
1. `/backend/models/user.py` ✅
2. `/backend/models/ordinance_review.py` (수정 필요)
3. `/backend/core/security.py` ✅
4. `/backend/api/deps.py` (수정 필요)
5. `/backend/api/v1/auth.py` (생성 필요)
6. `/backend/api/v1/ordinances.py` (수정 필요)
7. `/backend/services/ordinance_service.py` (수정 필요)
8. `/backend/schemas/ordinance.py` (수정 필요)
9. `/backend/core/config.py` ✅

**프론트엔드**:
10. `/frontend/src/contexts/AuthContext.tsx` (생성 필요)
11. `/frontend/src/services/api.ts` (수정 필요)
12. `/frontend/src/App.tsx` (수정 필요)
13. `/frontend/src/pages/Login.tsx` (생성 필요)
14. `/frontend/src/pages/Register.tsx` (생성 필요)
15. `/frontend/src/pages/Landing.tsx` (생성 필요)
16. `/frontend/src/components/ProtectedRoute.tsx` (생성 필요)
17. `/frontend/src/components/layout/MainLayout.tsx` (수정 필요)
18. `/frontend/src/pages/OrdinanceDetail.tsx` (수정 필요)

---

## 🎯 다음 작업 시작 방법

1. **schemas/user.py 생성** (7번 단계부터)
2. **schemas/auth.py 생성**
3. **services/auth_service.py 생성**
4. **api/v1/auth.py 생성**
5. **api/deps.py 수정**
6. **마이그레이션 생성 및 실행**
7. **의존성 설치 및 백엔드 재시작**

---

## 💡 유용한 명령어

### Docker 관련
```bash
# 백엔드 로그 확인
docker compose logs backend -f

# 백엔드 컨테이너 접속
docker compose exec backend bash

# 마이그레이션 실행
docker compose exec backend bash -c "cd /app/backend && alembic upgrade head"

# 전체 재시작
docker compose down
docker compose up -d --build
```

### Alembic 관련
```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "migration message"

# 마이그레이션 실행
alembic upgrade head

# 마이그레이션 히스토리 확인
alembic history

# 현재 상태 확인
alembic current
```

### API 테스트
```bash
# 회원가입 테스트
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"password123","user_type":"DEPARTMENT"}'

# 로그인 테스트
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}'
```

---

## ⚠️ 주의사항

1. **마이그레이션 충돌**: 현재 3개의 head가 있으므로 새 마이그레이션 생성 시 주의
2. **SECRET_KEY**: 프로덕션 환경에서는 반드시 강력한 키로 변경
3. **의존성 설치**: requirements.txt 업데이트 후 반드시 재설치
4. **테스트**: 각 Phase 완료 후 테스트 진행

---

## 📊 진행 상황 요약

- ✅ **Phase 1 완료**: 백엔드 인증 기반 (100%)
  - 모델, 스키마, 서비스, API 엔드포인트 모두 완료
  - 마이그레이션 파일 생성 완료
  - Docker 재빌드 완료
  - 회원가입/로그인 API 테스트 성공

- 🔄 **Phase 2 진행 중**: 검토 의견 사용자 추적 (60%)
  - ✅ 모델 및 마이그레이션 파일 생성 완료
  - ✅ 마이그레이션 실행 완료 (DB 테이블 업데이트 완료)
  - ⏳ 스키마, 서비스, API 수정 필요

- ✅ **Phase 3 완료**: 프론트엔드 인증 UI (100%)
  - ✅ 타입 정의, AuthContext, API 서비스 수정 완료
  - ✅ Landing, Login, Register 페이지 생성 완료
  - ✅ ProtectedRoute, App.tsx 라우팅, MainLayout 수정 완료
  - ✅ JWT 토큰 자동 관리, 인증 상태 유지 기능 완료

- ⏳ **Phase 4 대기 중**: 검토 의견 UI 자동화 (0%)
- ⏳ **Phase 5 대기 중**: 테스트 및 검증 (0%)

**전체 진행률**: 약 60% 완료

---

**마지막 업데이트**: 2026-02-04 (프론트엔드 인증 UI 구현 완료)
**현재 상태**: Phase 1, 3 완료 / Phase 2 진행 중 (스키마/서비스/API 수정 필요)
