# egovframework 조사 결과

## 조사일: 2026-03-23

## 1. 프로젝트 결정사항

- **자체 개발** (RFP 발주 아님)
- **egovframework 공통컴포넌트**: 참조용으로만 사용 (종속 X)
- **핵심 목표**: 보안성검토 통과 (시큐어코딩 49개 항목 준수)
- **프레임워크**: Spring Boot 3.x (순수)

## 2. egovframework 저장소 목록

### 참조용으로 clone 필요
| 저장소 | URL | 용도 |
|--------|-----|------|
| 공통컴포넌트 | https://github.com/eGovFramework/egovframe-common-components.git | 보안/인증 코드 참조 |
| 백엔드 템플릿 | https://github.com/eGovFramework/egovframe-template-simple-backend.git | Spring Boot 프로젝트 구조 참조 |
| React 템플릿 | https://github.com/eGovFramework/egovframe-template-simple-react.git | 프론트엔드 참조 |

### 참고할 만한 저장소
| 저장소 | 설명 |
|--------|------|
| egovframe-ai-rag | Spring AI + Langchain4j RAG 샘플 (LLM 연동 참조) |
| egovframe-msa-edu | 클라우드 네이티브 MSA 교육자료 |
| egovframe-vscode-initializr | VS Code용 프로젝트 생성기 |

## 3. egovframe-template-simple-backend 구조

| 항목 | 내용 |
|------|------|
| Java | 17 |
| Spring Boot | 3.5.6 |
| Spring Framework | 6.2.11 |
| ORM | JPA + QueryDSL |
| 인증 | JWT (jjwt 0.12.6) |
| DB | MySQL (PostgreSQL 변경 가능) |
| API 문서 | Swagger (SpringDoc OpenAPI 2.6.0) |
| 빌드 | Maven → JAR |
| 패키징 | egovframe-boot-simple-backend v5.0.0 |

### 주요 의존성
- egovframe-rte-ptl-mvc (MVC)
- egovframe-rte-psl-dataaccess (데이터접근)
- egovframe-rte-fdl-idgnr (ID생성)
- egovframe-rte-fdl-crypto (암호화)
- egovframe-rte-fdl-security (보안)
- spring-boot-starter-data-jpa
- QueryDSL (JPA, Jakarta)
- Lombok, Log4JDBC, Hibernate Validator

## 4. egovframe-template-simple-react 구조

| 항목 | 내용 |
|------|------|
| React | JavaScript (TypeScript 아님) |
| 빌드 | Vite |
| Node.js | v18.12.0 |
| 테스트 | Vitest |
| 페이지 | 로그인, 게시판, 공지사항, 일정, 갤러리, 관리자 |

## 5. 공통컴포넌트 참조 대상 (253개 중)

### 보안성검토 관련 필수 참조
- `com/sec/` - 보안 (권한, 롤, 그룹 관리)
- `com/uat/` - 인증 (로그인, 인증서)
- `com/sym/` - 시스템관리 (코드, 로그, 메뉴)
- `com/cmm/` - 공통 클래스 (유틸리티)
- `script/` - DB DDL/DML (PostgreSQL 스키마)

### 카테고리별 전체 목록
- 보안관리: 권한관리, 그룹관리, 롤관리, 부서권한관리, 암호화/복호화
- 사용자관리: 사용자관리, 인증, 로그인정책
- 시스템관리: 공통코드, 로그관리, 프로그램관리, 메뉴관리, 배치관리
- 통계/리포팅: 게시물/사용자/접속 통계
- 협업: 게시판, 일정, 전자결재 등

## 6. 현재 프로젝트 → Spring Boot 매핑

| Python (현재) | Java (전환) |
|--------------|-------------|
| FastAPI router | @RestController |
| SQLAlchemy Model | JPA @Entity |
| Pydantic Schema | DTO class |
| Service 클래스 | @Service 클래스 |
| Alembic migration | Flyway/Liquibase |
| Celery task | Spring Scheduler / @Async |
| httpx (법제처 API) | WebClient / RestTemplate |
| pytest | JUnit 5 |

## 7. 시큐어코딩 49개 항목 (7대 영역)

1. 입력데이터 검증 및 표현 (SQL인젝션, XSS 등)
2. 보안기능 (인증, 접근제어, 암호화 등)
3. 시간 및 상태 (경쟁조건, 동기화 등)
4. 에러처리 (오류메시지 정보노출 등)
5. 코드오류 (널포인터, 자원해제 등)
6. 캡슐화 (접근제어, 데이터노출 등)
7. API 오용 (위험한 함수 사용 등)

### 참조 문서
- 행안부 소프트웨어 개발보안 가이드: https://www.data.go.kr/data/15049187/fileData.do
- 보안약점 진단가이드: https://www.data.go.kr/data/15049185/fileData.do
