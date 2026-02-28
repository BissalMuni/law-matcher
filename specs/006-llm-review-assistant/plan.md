# Implementation Plan: LLM 기반 검토의견 자동 생성

**Branch**: `006-llm-review-assistant` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-llm-review-assistant/spec.md`

## Summary

법령 제개정이유와 조례 정보를 LLM API에 전송하여 개정내용 요약 및 검토의견 초안을 자동 생성한다. **전면 신규 구현** 피처이며, 핵심은 (1) 격리된 LLM 클라이언트 모듈, (2) 1회 실행 원칙 보장, (3) AI 생성 메타데이터 추적이다. 005(제개정이유 데이터)에 의존한다.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.3 (frontend)
**Primary Dependencies**: FastAPI >=0.104, SQLAlchemy 2.0 (async), React 18, Ant Design 5, TanStack Query 5
**Storage**: PostgreSQL 15
**Testing**: pytest (backend)
**Target Platform**: Docker (Linux containers), 브라우저 (Chrome/Edge)
**Project Type**: Web application (SPA + REST API)
**Performance Goals**: AI 요약 10초 이내 (SC-001), 저장된 결과 1초 이내 (SC-002)
**Constraints**: 관공서 보안성 검토, 시큐어코딩, 공개 데이터만 LLM 전송, 1회 실행 원칙
**Scale/Scope**: 지자체 단위, 분석 건수 수십~수백 건/월

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | 원칙 | 준수 여부 | 근거 |
|---|------|----------|------|
| I | 데이터 무결성 | PASS | AI 입력(prompt)+출력(response) 모두 DB 보존. input_hash로 재현성 |
| II | 관심사 분리 | PASS | LLM Client(외부 통신) → LLM Service(비즈니스) → API(표현) 분리 |
| III | 외부 의존 격리 | PASS | LLM 클라이언트를 별도 모듈(llm_client.py)로 격리. 장애 시 수동 검토 정상 동작 |
| IV | 비차단 처리 | PASS | LLM 호출은 비동기. 타임아웃 30초. 기존 기능 차단 없음 |
| V | 환경 재현성 | PASS | LLM API 키/모델명 환경변수. Docker Compose |
| VI | 보안 기본 적용 | PASS | API 키 환경변수 관리(FR-007). 공개 데이터만 전송(FR-008). JWT 인증(FR-009) |
| VII | 사용자 중심 설계 | PASS | AI 결과는 참고용. "AI 생성" 라벨 명확 구분. 한국어 UI |
| VIII | AI 보조 활용 | PASS | 수동 버튼만(자동 실행 금지). 1회 실행(재실행 불가). 메타데이터 기록. 입출력 보존 |

**Gate Result**: ALL PASS

## Project Structure

### Documentation (this feature)

```text
specs/006-llm-review-assistant/
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
│   └── config.py                    # 수정: LLM 환경변수 추가
├── models/
│   ├── llm_analysis_result.py       # 신규: AI 분석 결과 캐시
│   └── ordinance_review.py          # 수정: AI 메타데이터 필드 추가
├── schemas/
│   └── llm.py                       # 신규: AI 관련 요청/응답 스키마
├── services/
│   ├── llm_client.py                # 신규: LLM API 클라이언트 (격리 모듈)
│   └── llm_review_service.py        # 신규: AI 요약/초안 비즈니스 로직
├── api/v1/
│   └── llm_reviews.py               # 신규: AI 관련 API 엔드포인트
├── external/
│   └── (moleg_client.py 변경 없음 — 005에서 확장)
└── alembic/versions/
    ├── YYYYMMDD_add_llm_analysis_results.py    # 신규
    └── YYYYMMDD_add_ai_fields_to_reviews.py    # 신규

frontend/src/
├── pages/
│   ├── OrdinanceDetail.tsx          # 수정: AI 요약 버튼 + 결과 패널
│   └── AiAnalytics.tsx              # 신규: 관리자 AI 분석 이력 (US4)
├── components/
│   └── ai/
│       ├── AiSummaryPanel.tsx       # 신규: AI 요약 표시 패널
│       ├── AiDraftButton.tsx        # 신규: AI 초안 생성 버튼
│       └── AiLabel.tsx              # 신규: "AI 생성" 라벨 컴포넌트
├── services/
│   └── api.ts                       # 수정: AI API 호출 함수 추가
└── types/
    └── api.ts                       # 수정: AI 관련 타입 추가
```

**Structure Decision**: LLM 클라이언트를 `services/llm_client.py`에 격리 (III. 외부 의존 격리). 프론트엔드 AI 컴포넌트를 `components/ai/`에 분리하여 재사용성 확보.

## 구현 범위

### 구현 대상

| User Story | 상태 | 작업 |
|------------|------|------|
| US1 AI 요약 | ❌ 미구현 | **신규**: LLM 클라이언트 + 서비스 + API + UI |
| US2 검토의견 초안 | ❌ 미구현 | **신규**: 초안 생성 + 입력 필드 자동 채움 + 메타데이터 |
| US3 결과 보존/재조회 | ❌ 미구현 | **신규**: DB 저장 + 1회 실행 원칙 + 버튼 비활성화 |
| US4 AI 이력 조회 | ❌ 미구현 | **신규**: 관리자 대시보드 (P3, 후순위) |

### 의존성

- **005-revision-detection-tabs**: `LawRevisionReason` 테이블의 `revision_reason` 데이터를 LLM 입력으로 사용

### 핵심 구현 단계

#### Step 1: 백엔드 인프라

1. **config.py**: LLM 환경변수 (`LLM_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT`, `LLM_MAX_RETRIES`)
2. **llm_client.py**: 프로바이더 추상화 클라이언트
   - 인터페이스: `async def generate(prompt, system_prompt) -> LlmResponse`
   - 재시도: 최대 2회, 지수 백오프
   - 타임아웃: 30초
   - 에러 핸들링: 장애 시 기존 기능 무영향
3. **모델 + 마이그레이션**: LlmAnalysisResult 신규, OrdinanceReview AI 필드 추가

#### Step 2: 서비스 로직

1. **llm_review_service.py**:
   - `generate_summary(ordinance_id)`: 제개정이유 → LLM → 요약
   - `generate_draft(ordinance_id)`: 제개정이유 + 조례 → LLM → 초안
   - 1회 실행 검증: `LlmAnalysisResult` UNIQUE 제약 + input_hash 비교
   - 프롬프트 템플릿: 한국어, 법률 용어, 구조화된 출력 요청

#### Step 3: API 엔드포인트

1. `POST /ordinances/{id}/ai-summary`: AI 요약 생성 (1회)
2. `POST /ordinances/{id}/ai-draft`: AI 초안 생성 (1회)
3. `GET /ordinances/{id}/ai-results`: 저장된 결과 조회
4. `GET /admin/ai-analytics`: 관리자 통계

#### Step 4: 프론트엔드

1. **AiSummaryPanel**: AI 요약 표시 + "AI 생성" 라벨 + 버튼 비활성화
2. **AiDraftButton**: 초안 생성 → 입력 필드 자동 채움 + ai_modified 추적
3. **AiLabel**: 재사용 가능한 "AI 생성" 배지
4. **OrdinanceDetail 수정**: 기존 상세 페이지에 AI 패널 통합
5. **AiAnalytics 페이지**: 관리자 대시보드 (US4, P3)

## 프로바이더 추상화 설계

```python
# llm_client.py — III. 외부 의존 격리
class LlmClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str) -> LlmResponse: ...

class AnthropicClient(LlmClient): ...  # Anthropic Claude 구현
class OpenAIClient(LlmClient): ...     # OpenAI GPT 구현 (예비)

def get_llm_client() -> LlmClient:
    """환경변수 LLM_PROVIDER에 따라 클라이언트 반환"""
```

구현 시점에 프로바이더 결정. 인터페이스 분리로 전환 비용 최소화.

## Complexity Tracking

> Constitution Check 위반 없음 - 해당 없음
