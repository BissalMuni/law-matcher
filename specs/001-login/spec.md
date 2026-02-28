# Feature Specification: 로그인 기능

**Feature Branch**: `001-login`
**Created**: 2026-02-27
**Status**: Draft
**Constitution Ref**: VI. 보안 기본 적용, VII. 사용자 중심 설계, Strategic Direction > 인증 모델 진화

## User Scenarios & Testing

### User Story 1 - 부서 로그인 (Priority: P1) [Auth Phase A]

부서 담당자가 소속 부서를 선택하고 공용 비밀번호를 입력하여 로그인한다.
개인 계정 없이 부서 단위로 인증하며, 로그인 후 해당 부서의 조례만 조회할 수 있다.

**현재 구현 방식**:
- 프론트엔드에서 username은 `'user'`로 고정하여 전송
- 모든 부서가 동일한 공용 비밀번호(환경변수 `USER_PASSWORD`) 사용
- 부서 선택값(`department_name`)은 인증이 아닌 세션 식별 정보로만 사용

**Why this priority**: 현재 운영 중인 핵심 인증 방식. 모든 기능의 진입점.

**Independent Test**: 부서 선택 → 비밀번호 입력 → 로그인 성공 → 해당 부서 조례 목록 표시

**Acceptance Scenarios**:

1. **Given** 로그인 페이지에서 부서를 선택하고 올바른 비밀번호를 입력,
   **When** 로그인 버튼 클릭,
   **Then** JWT 토큰 발급 후 조례 목록 페이지로 이동
2. **Given** 잘못된 비밀번호 입력,
   **When** 로그인 버튼 클릭,
   **Then** "비밀번호가 일치하지 않습니다" 오류 메시지 표시
3. **Given** 로그인 상태에서 브라우저 새로고침,
   **When** 페이지 로드,
   **Then** 저장된 토큰으로 세션 유지 (24시간 이내)

---

### User Story 2 - 관리자 로그인 (Priority: P1)

관리자가 관리자 비밀번호로 로그인하여 전체 시스템을 운영한다.
모든 부서의 조례를 조회할 수 있으며, 법령 동기화/부서 관리 등 관리 기능에 접근한다.

**현재 구현 방식**:
- 프론트엔드에서 username은 `'admin'`으로 고정하여 전송
- 관리자 비밀번호는 환경변수 `ADMIN_PASSWORD`로 관리
- 일부 관리 API(법령 동기화 등)는 JWT 외에 `X-Admin-Password` 헤더 인증을 추가로 요구

**Why this priority**: 시스템 운영에 필수. 부서 로그인과 동일 우선순위.

**Independent Test**: 관리자 로그인 → 전체 조례 목록 + 관리 메뉴 접근 가능

**Acceptance Scenarios**:

1. **Given** 로그인 페이지에서 관리자 모드 선택(`?type=admin`),
   **When** 관리자 비밀번호 입력 후 로그인,
   **Then** `user_type=ADMIN` 토큰 발급, 전체 기능 접근 가능
2. **Given** 일반 사용자로 로그인된 상태,
   **When** 관리자 전용 기능(법령 동기화, 부서 관리) 접근 시도,
   **Then** 접근 차단 또는 해당 UI 미노출

---

### User Story 3 - 로그아웃 (Priority: P1)

로그인된 사용자가 로그아웃하여 세션을 종료한다.

**Why this priority**: 보안 필수 기능. 공용 PC 환경에서 필수.

**Independent Test**: 로그아웃 → 토큰 삭제 → 보호 페이지 접근 불가

**Acceptance Scenarios**:

1. **Given** 로그인 상태,
   **When** 로그아웃 클릭,
   **Then** localStorage 토큰 삭제, 랜딩 페이지로 이동
2. **Given** 로그아웃 후,
   **When** 뒤로가기 또는 직접 URL 입력으로 보호 페이지 접근,
   **Then** 로그인 페이지로 리다이렉트

---

### User Story 4 - 비밀번호 변경 (Priority: P2)

로그인된 사용자(관리자 포함)가 현재 비밀번호를 확인한 후 새 비밀번호로 변경한다.

**Why this priority**: 보안 필수 기능. 기본 비밀번호 운영 환경에서 변경 수단 필요.

**Independent Test**: 로그인 → 비밀번호 변경 → 새 비밀번호로 재로그인 성공

**Acceptance Scenarios**:

1. **Given** 로그인 상태에서 비밀번호 변경 요청,
   **When** 현재 비밀번호 정확 + 새 비밀번호 입력,
   **Then** 비밀번호 변경 성공, 재로그인 시 새 비밀번호 적용
2. **Given** 비밀번호 변경 요청,
   **When** 현재 비밀번호 불일치,
   **Then** "현재 비밀번호가 일치하지 않습니다" 오류 표시

---

### User Story 5 - 개인별 로그인 (Priority: P3) [Auth Phase B - 추후]

사용자가 개인 이메일/사용자명과 비밀번호로 로그인한다.
부서 소속은 사용자 속성으로 관리되며, 개인별 검토 이력 추적이 가능해진다.

**Why this priority**: 추후 전환 대상. 현재는 설계만 고려.

**Independent Test**: 회원가입 → 개인 로그인 → 부서 조례 조회 + 개인 검토 이력

**Acceptance Scenarios**:

1. **Given** 회원가입 완료 후 로그인 페이지에서 개인 정보 입력,
   **When** 로그인 버튼 클릭,
   **Then** 개인 JWT 발급, 소속 부서 조례 조회 가능
2. **Given** 개인 계정으로 검토 작성,
   **When** 검토 이력 조회,
   **Then** 본인이 작성한 검토만 수정/삭제 가능

---

### Edge Cases

- 부서 목록이 비어 있을 때 로그인 페이지 동작
- JWT 토큰 만료 시 자동 로그아웃 및 안내 메시지
- 동시 로그인(같은 부서 비밀번호로 여러 브라우저) 허용 여부
- 유지보수 모드에서 로그인 가능 여부 (현재: `/auth/login` 바이패스 설정)
- 비활성화된 계정(`is_active=false`)으로 로그인 시도 → 403 "비활성화된 계정입니다"
- DB에 사용자가 없는 토큰으로 API 요청 시 가상 사용자 생성 처리
- 개발 환경에서 `VITE_DEV_BYPASS_AUTH=true` 설정 시 인증 우회 동작

## Requirements

### Functional Requirements

- **FR-001**: 시스템은 부서 선택 + 비밀번호 방식(Auth Phase A)으로 인증을 제공해야 한다
- **FR-002**: 시스템은 관리자 비밀번호로 관리자 인증을 제공해야 한다
- **FR-003**: 인증 성공 시 JWT 토큰(HS256, 24시간 만료)을 발급해야 한다
- **FR-004**: 인증되지 않은 요청은 401 응답으로 차단해야 한다
- **FR-005**: 비밀번호는 bcrypt로 해시하여 저장해야 한다
- **FR-006**: 로그아웃 시 클라이언트 토큰을 삭제해야 한다
- **FR-007**: `user_type`에 따라 네비게이션 메뉴와 접근 가능한 기능을 분리해야 한다
  - `DEPARTMENT`(USER): 소속 부서 조례만 조회/검토
  - `GENERAL`(ADMIN): 전체 시스템 관리
  - 프론트엔드 메뉴와 백엔드 API 양쪽에서 권한을 강제한다

#### FR-007 역할별 메뉴 구성

| 메뉴 | 경로 | 관리자 | 사용자 | 비고 |
|------|------|:------:|:------:|------|
| 자치법규 | `/ordinances` | O | O | 사용자는 소속 부서만 |
| 개정검토필요 | `/revision-needed` | O | X | |
| 상위법령 | `/laws` | O | X | |
| 개정법령 | `/amendments` | O | X | |
| 부서관리 | `/departments` | O | X | |
| 법령연계통계 | `/statistics` | O | X | |
| 대시보드 | `/dashboard` | O | X | |

- 사용자에게는 권한 밖의 메뉴를 렌더링하지 않는다 (숨김, 비활성화 아님)
- 메뉴에 없는 경로로 직접 접근 시에도 권한 검증 후 차단해야 한다
- **FR-008**: 비활성화된 계정(`is_active=false`)의 로그인을 차단해야 한다 (403)
- **FR-009**: 로그인된 사용자는 현재 비밀번호 확인 후 비밀번호를 변경할 수 있어야 한다
- **FR-010**: 관리 API(법령 동기화 등)는 JWT 인증 외에 `X-Admin-Password` 헤더 인증을 추가로 요구해야 한다
- **FR-011**: 개발 환경에서만 인증 우회(`VITE_DEV_BYPASS_AUTH`)를 허용하며, 운영 환경에서는 비활성화해야 한다
- **FR-012**: [Auth Phase B] 개인 회원가입(이메일, 사용자명, 비밀번호, 부서 선택)을 지원해야 한다
- **FR-013**: [Auth Phase B] 비밀번호 재설정(토큰 기반, 30분 만료)을 지원해야 한다

### Key Entities

- **User**: 인증 주체. email, username, hashed_password, user_type, department_id
- **Department**: 사용자 소속 부서. Auth Phase A에서 로그인 단위

## Success Criteria

### Measurable Outcomes

- **SC-001**: 부서 로그인 성공까지 3클릭 이내 (부서 선택 → 비밀번호 → 로그인)
- **SC-002**: 잘못된 인증 시도 시 1초 이내 오류 응답
- **SC-003**: Auth Phase A → B 전환 시 기존 검토 데이터 100% 이관
- **SC-004**: 보안성 검토 승인 기준 충족 (비밀번호 평문 저장 금지, 토큰 만료 적용)

## Security Notes

운영 환경 배포 전 반드시 변경해야 하는 설정:

- `SECRET_KEY`: 기본값 `"your-secret-key-change-this-in-production..."` → 32자 이상 랜덤 문자열
- `ADMIN_PASSWORD`: 기본값 `"admin123"` → 강력한 비밀번호
- `USER_PASSWORD`: 기본값 `"user123"` → 강력한 비밀번호
- `VITE_DEV_BYPASS_AUTH`: 운영 환경에서 반드시 미설정 또는 `false`
