# 입안심사(law-ebansimsa) → law-matcher 통합 마이그레이션 계획

작성일: 2026-05-27

## 결정된 통합 노선 (완전 통합)

- 입안심사 UI를 **React 18 + Ant Design 5**로 포팅 (단일 앱)
- 입안심사 데이터를 **law-matcher PostgreSQL**로 통합 (Prisma → SQLAlchemy/Alembic)
- **조례 본문 + 상위법령** 둘 다 law-matcher 등록분에서 연동

## 핵심 원칙

- **기존 체계 무손상**: 추가(additive)만 한다. 기존 테이블/라우터/페이지 수정 금지.
  입안심사는 격리된 모듈(`drafting`)·새 메뉴·새 라우트로만 들어온다.
- **단일 앱·단일 DB**: 백엔드는 law-matcher FastAPI에 모듈 추가, 프론트는 AntD로 재구현, 데이터는 Postgres로 일원화.
- **실시간 법제처 API → 등록 조례 치환**: 입안심사가 조례 본문/상위법령을 law-matcher 내부 데이터에서 읽는다.

## 아키텍처 매핑 (출발 → 도착)

| 영역 | law-ebansimsa (현재) | law-matcher 통합 후 |
|---|---|---|
| 백엔드 | FastAPI 무상태 연산 (`pipeline/`) | `backend/drafting/` 모듈 + `/api/v1/drafting/*` 라우터 |
| 데이터 | Prisma + SQLite (Next.js) | SQLAlchemy 2.0 + PostgreSQL (Alembic) |
| 조례 로딩 | 법제처 API 실시간 | 등록 조례(`ordinance_texts`) + 상위법령(`ordinance_law_mappings`→`laws`) |
| 프론트 | Next.js15 + shadcn + Tailwind | React18 + AntD5 + Vite, 새 메뉴 `/drafting` |
| 에디터 | Monaco | Monaco (`@monaco-editor/react`, React18 호환 — 그대로 유지) |
| AI | Anthropic SDK 스트리밍(SSE) | law-matcher 설정/키 재사용, SSE 스트리밍 라우터 |
| 기준(wiki) | 파일 참조(문자열 ID) | 파일 그대로 이관, 읽기전용 서빙 |

## 데이터 모델 이관 (Prisma → SQLAlchemy)

격리를 위해 신규 테이블만 추가 (`drafting_` 접두사). 기존 `ordinances`/`laws`/`ordinance_law_mappings`는 FK로만 참조, 스키마 변경 없음.

| Prisma 모델 | 신규 테이블 | 모델 클래스 |
|---|---|---|
| Project | `drafting_projects` | `DraftingProject` (→ `ordinances.id` FK nullable) |
| Stage | `drafting_stages` | `DraftingStage` (self-FK `parent_id`) |
| OrdinanceSection | `drafting_sections` | `DraftingSection` |
| Message | `drafting_messages` | `DraftingMessage` |
| ValidationResult | `drafting_validations` | `DraftingValidation` |
| Reference | `drafting_references` | `DraftingReference` |
| Snapshot | `drafting_snapshots` | `DraftingSnapshot` |

명명 주의: SQL 예약어 회피 — Prisma `order` → `sort_order`, `trigger` → `trigger_type`.
PK는 law-matcher 관례에 맞춰 Integer 사용(원본 cuid 문자열은 데이터 이관 시 매핑).

## 단계별 실행 계획

- **Phase 0 — 스캐폴딩 (무동작, 안전)**: `backend/drafting/` 패키지 + 빈 라우터(`/api/v1/drafting`) + 기능 플래그(`DRAFTING_ENABLED`), 프론트 `pages/drafting/` + 새 메뉴/라우트.
- **Phase 1 — DB 모델 + 마이그레이션 (additive)**: 7개 `drafting_*` SQLAlchemy 모델, 신규 Alembic 리비전(기존 테이블 ALTER 없음).
- **Phase 2 — 백엔드 연산 파이프라인 포팅**: `draft`(생성)/`review`(검증 매트릭스)/`export`(DOCX/PDF)/`parser`(조문 파싱), wiki 기준 파일 이관·읽기전용 서빙, Anthropic 통일 + SSE 스트리밍.
- **Phase 3 — 조례·상위법령 연동 (핵심)**: 등록 조례에서 시작 → `ordinance_texts.articles_json`으로 `drafting_sections` 시드(개정 모드 `original_body`), 상위법령(`ordinance_law_mappings`→`laws`+`law_revision_reasons`)을 AI 프롬프트/검증 컨텍스트로 주입.
- **Phase 4 — 프론트 포팅 (AntD)**: 8단계 워크플로우(AntD Steps + 채팅 + Monaco), 검증 매트릭스(AntD Table), 개정 diff, 등록 조례 선택 UI.
- **Phase 5 — 통합/패리티 검증**: 원본 대조 + law-matcher 회귀 테스트.
- **Phase 6 — 전환·후속 개발**: 패리티 후 입안심사 후속 개발을 law-matcher에서 진행, 원본 동결.

## 리스크

- **React 19→18**: shadcn/Radix → AntD 대체(가장 공수 큼). Monaco는 React18 호환되어 그대로 이관.
- **Next.js Server Actions/Prisma**: FastAPI 라우터 + SQLAlchemy로 재구현(백엔드 신규 작업의 대부분).
- **wiki 기준 동기화**: 파일 기반 유지(D1 원칙), 단일 소스로 중복 방지.
