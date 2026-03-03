# Implementation Plan: LLM 기반 검토의견 자동 생성

**Branch**: `006-llm-review-assistant` | **Date**: 2026-03-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-llm-review-assistant/spec.md`

## Summary

법령 제개정이유와 조례 정보를 LLM API에 **1회 통합 호출**하여 개정내용 요약 및 검토의견 초안을 **동시에** 생성한다. **전면 신규 구현** 피처이며, 핵심은 (1) DB 기반 LLM 프로바이더/모델 관리, (2) 격리된 LLM 클라이언트 추상화 (3개 프로바이더), (3) 동기 처리 + 30초 타임아웃, (4) YAML 프롬프트 관리, (5) 1회 실행 원칙 + JSON 구조화 출력 강제, (6) Redis 기반 Rate Limiting이다. 005(제개정이유 데이터)에 의존한다.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.3 (frontend)
**Primary Dependencies**: FastAPI >=0.104, SQLAlchemy 2.0 (async), React 18, Ant Design 5, TanStack Query 5, anthropic, openai, google-generativeai, PyYAML
**Storage**: PostgreSQL 15, Redis 7 (rate limiting)
**Testing**: pytest (backend)
**Target Platform**: Docker (Linux containers), Browser (Chrome/Edge)
**Project Type**: Web application (SPA + REST API)
**Performance Goals**: AI 분석 10초 이내 (SC-001), 저장된 결과 1초 이내 (SC-002)
**Constraints**: 관공서 보안성 검토, 시큐어코딩, 공개 데이터만 LLM 전송, 1회 실행 원칙, 동기 처리 (30초 타임아웃)
**Scale/Scope**: 지자체 단위, 분석 건수 수십~수백 건/월

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | 원칙 | 준수 여부 | 근거 |
|---|------|----------|------|
| I | 데이터 무결성 | PASS | AI 입력(prompt_text)+출력(summary_text, review_draft_text) 모두 DB 보존. input_hash로 변경 감지 |
| II | 관심사 분리 | PASS | LLM Client(외부 통신) → LLM Service(비즈니스) → API(표현) 3계층 분리 |
| III | 외부 의존 격리 | PASS | LLM 클라이언트를 별도 모듈(llm_client.py)에 격리. ABC 추상화. 장애 시 수동 검토 정상 동작 |
| IV | 비차단 처리 | PASS | FastAPI async로 서버 비차단. 로딩 스피너로 사용자 안내. 다른 사용자/기능 무영향. 동기 응답 대기는 사용자의 명시적 설계 결정 |
| V | 환경 재현성 | PASS | API 키 환경변수. 프롬프트 YAML 설정 파일. Docker Compose |
| VI | 보안 기본 적용 | PASS | API 키 환경변수만(DB 미저장). 공개 데이터만 전송. JWT 인증 필수 |
| VII | 사용자 중심 설계 | PASS | AI 결과는 참고용. "AI 생성" 라벨 명확 구분. 한국어 UI. 관리자 설정 탭 |
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
├── config/
│   └── prompts.yaml                    # 신규: LLM 프롬프트 템플릿
├── core/
│   └── config.py                       # 수정: LLM 환경변수 추가
├── models/
│   ├── llm_provider.py                 # 신규: LLM 프로바이더 DB 관리
│   ├── llm_analysis_result.py          # 신규: AI 통합 분석 결과
│   └── ordinance_review.py             # 수정: AI 메타데이터 필드 추가
├── schemas/
│   └── llm.py                          # 신규: LLM 관련 요청/응답 스키마
├── services/
│   ├── llm_client.py                   # 신규: LLM 클라이언트 추상화 (ABC + 3개 프로바이더)
│   ├── llm_analysis_service.py         # 신규: AI 통합 분석 비즈니스 로직
│   └── llm_rate_limiter.py             # 신규: Redis 기반 Rate Limiter
├── api/v1/
│   ├── llm_analysis.py                 # 신규: AI 분석 엔드포인트
│   └── admin.py                        # 신규: LLM 프로바이더 관리 + AI 통계
├── external/
│   └── (moleg_client.py 변경 없음 — 005에서 확장)
└── alembic/versions/
    ├── YYYYMMDD_add_llm_providers.py              # 신규 + 초기 데이터
    ├── YYYYMMDD_add_llm_analysis_results.py       # 신규
    └── YYYYMMDD_add_ai_fields_to_reviews.py       # 신규

frontend/src/
├── pages/
│   ├── OrdinanceDetail.tsx             # 수정: AI 분석 버튼 + 요약 패널 통합
│   └── AdminSettings.tsx               # 신규: 관리자 LLM 설정 탭
├── components/
│   └── ai/
│       ├── AiAnalysisButton.tsx        # 신규: "AI 분석" 버튼 + 로딩 스피너
│       ├── AiSummaryPanel.tsx          # 신규: AI 요약 표시 패널
│       ├── AiDraftModal.tsx            # 신규: AI 초안 → 검토의견 모달 자동 채움
│       └── AiLabel.tsx                 # 신규: "AI 생성" 라벨 배지
├── services/
│   └── api.ts                          # 수정: AI API + Admin API 호출 함수 추가
└── types/
    └── api.ts                          # 수정: AI + LlmProvider 관련 타입 추가
```

**Structure Decision**: 기존 Web application 구조 유지. LLM 클라이언트를 `services/llm_client.py`에 격리 (III. 외부 의존 격리). 프론트엔드 AI 컴포넌트를 `components/ai/`에 분리. 프롬프트 템플릿은 `backend/config/prompts.yaml`에서 코드 외부 관리.

## 구현 범위

### 구현 대상

| User Story | 상태 | 작업 |
|------------|------|------|
| US1 AI 통합 분석 (요약+초안) | ❌ 미구현 | **신규**: 1회 통합 호출 → 요약+초안 동시 생성 → DB 저장 → UI 표시 |
| US3 결과 보존/재조회 (P2) | ❌ 미구현 | **신규**: UNIQUE 제약 + status 기반 1회 실행 원칙 + 법령 버전 추적 |
| US4 LLM 프로바이더/모델 관리 (P2) | ❌ 미구현 | **신규**: llm_providers DB 테이블 + 관리자 설정 탭 |
| US3 AI 이력 조회 (P3) | ❌ 미구현 | **신규**: 관리자 통계 대시보드 (후순위) |

### 의존성

- **005-revision-detection-tabs**: `LawRevisionReason` 테이블의 `revision_reason`, `amendment_content` 데이터를 LLM 입력으로 사용
- 005 미구현 시 LLM 입력 데이터 부재 → "제개정이유 데이터가 없어 AI 분석을 수행할 수 없습니다" (Edge Case 처리)

### 핵심 구현 단계

#### Step 1: 백엔드 인프라 (모델 + 설정 + 마이그레이션)

1. **config.py 확장**: LLM 환경변수 추가
   - `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_AI_API_KEY`
   - `LLM_TIMEOUT` (기본 30초)
   - `LLM_MAX_RETRIES` (기본 2회)

2. **LlmProvider 모델**: 프로바이더/모델 DB 관리
   - provider_name (UNIQUE), display_name, model_name
   - api_key_env_name, is_active, rate_limit_per_minute
   - 초기 데이터: claude (active), chatgpt, gemini

3. **LlmAnalysisResult 모델**: 통합 분석 결과
   - ordinance_id, law_id, law_proclaimed_date (법령 버전)
   - status (pending/success/failed)
   - input_hash (입력 데이터만)
   - prompt_text, summary_text, review_draft_text, review_draft_result
   - provider_name, model_name, token_usage (JSONB)
   - UNIQUE(ordinance_id, law_id, law_proclaimed_date)

4. **OrdinanceReview 수정**: AI 메타데이터 필드
   - is_ai_generated, ai_modified, ai_analysis_id (FK)

5. **마이그레이션 3건** 실행

6. **prompts.yaml**: LLM 프롬프트 템플릿 파일 생성
   - 통합 분석 프롬프트 (요약+초안 동시 생성)
   - 토큰 초과 시 요약 프롬프트
   - JSON 출력 형식 정의

#### Step 2: LLM 클라이언트 추상화 (외부 의존 격리)

1. **LlmClient ABC**: 공통 인터페이스
   ```python
   class LlmClient(ABC):
       @abstractmethod
       async def generate(self, prompt: str, system_prompt: str) -> LlmResponse: ...
   ```

2. **ClaudeClient**: anthropic SDK → messages.create()
3. **ChatGptClient**: openai SDK → chat.completions.create()
4. **GeminiClient**: google-generativeai → generate_content()

5. **프로바이더 팩토리**: DB의 is_active=True 프로바이더로 클라이언트 생성
   ```python
   async def get_active_llm_client(db: AsyncSession) -> LlmClient:
       provider = await db.execute(
           select(LlmProvider).where(LlmProvider.is_active == True)
       )
       # provider.api_key_env_name → os.getenv() → 해당 Client 인스턴스 반환
   ```

6. **공통 기능**: 타임아웃 30초, 재시도 최대 2회 (지수 백오프), JSON 파싱 검증

#### Step 3: 서비스 로직

1. **llm_analysis_service.py**: 통합 분석 비즈니스 로직
   - `analyze_ordinance(ordinance_id, law_id)`: 메인 진입점
     - 1회 실행 검증 (UNIQUE + status 확인, 실패 건 1회 재시도 허용)
     - 법령 버전 확인 (law.proclaimed_date)
     - 입력 데이터 수집 (LawRevisionReason → revision_reason + amendment_content)
     - input_hash 계산 (입력 데이터만, 프롬프트 제외)
     - 토큰 초과 검사 → 초과 시 1차 요약 호출
     - 프롬프트 렌더링 (YAML 템플릿 + 변수 치환)
     - Rate Limit 검사
     - LLM 호출 → JSON 파싱 → 파싱 실패 시 1회 재시도
     - 결과 DB 저장 (status=success/failed)
   - `get_analysis_results(ordinance_id, law_id?)`: 결과 조회

2. **llm_rate_limiter.py**: Redis 기반 시스템 전체 Rate Limiting
   - Redis INCR + EXPIRE (60초 TTL) 패턴
   - 활성 프로바이더의 rate_limit_per_minute 참조
   - 초과 시 429 에러

#### Step 4: API 엔드포인트

1. **llm_analysis.py** (신규 라우터):
   - `POST /ordinances/{id}/ai-analyze`: 통합 AI 분석 실행
   - `GET /ordinances/{id}/ai-results`: 분석 결과 조회

2. **admin.py** (신규 또는 기존 확장):
   - `GET /admin/llm-providers`: 프로바이더 목록 (api_key_configured 마스킹)
   - `PATCH /admin/llm-providers/{id}`: 모델명/활성 상태/Rate Limit 변경
   - `GET /admin/ai-analytics`: 분석 이력 통계

#### Step 5: 프론트엔드

1. **AiAnalysisButton**: "AI 분석" 버튼 + 로딩 스피너 + 비활성화 상태
   - 이미 분석 완료 → 비활성화 (FR-012)
   - 클릭 → 로딩 스피너 → 동기 대기 → 결과 표시 또는 에러

2. **AiSummaryPanel**: 개정검토 탭에 AI 요약 구조화 표시
   - 주요 변경사항, 변경 조문 목록, 조례 영향
   - "AI 생성" 라벨 + 프로바이더/모델명 표시

3. **AiDraftModal**: 검토의견 작성 모달에 AI 초안 자동 채움
   - review_result + review_content 자동 채움
   - 담당자 수정 시 ai_modified=TRUE 추적
   - 수정 없이 제출 시 ai_modified=FALSE

4. **AiLabel**: "AI 생성" 배지 컴포넌트 (재사용)

5. **OrdinanceDetail.tsx 수정**:
   - 개정검토 탭에 법령별 AiAnalysisButton + AiSummaryPanel 배치
   - 검토의견 작성 모달에 AiDraftModal 연동
   - 법령별 AI 결과 구분 표시 (상위법령 복수 연결 시)

6. **AdminSettings.tsx** (신규):
   - LLM 프로바이더 관리 탭
   - 프로바이더 목록 테이블 (모델명, 활성 상태, API 키 여부, Rate Limit)
   - 모델명 편집, 활성 프로바이더 전환, Rate Limit 조정

7. **api.ts + types/api.ts 수정**:
   - AI API 호출 함수: `aiApi.analyze()`, `aiApi.getResults()`
   - Admin API: `adminApi.getLlmProviders()`, `adminApi.updateLlmProvider()`
   - TypeScript 타입: `LlmAnalysisResult`, `LlmProvider`, `AiAnalyzeResponse`

#### Step 6: 인프라

1. **requirements.txt**: `anthropic`, `openai`, `google-generativeai`, `pyyaml` 추가
2. **docker-compose.yml**: LLM 환경변수 추가 (backend + worker 서비스)
3. **.env.example**: LLM API 키 환경변수 문서화

## LLM 클라이언트 추상화 설계

```python
# services/llm_client.py — III. 외부 의존 격리
from abc import ABC, abstractmethod

class LlmResponse:
    content: str           # LLM 응답 원문
    input_tokens: int
    output_tokens: int

class LlmClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str) -> LlmResponse: ...

class ClaudeClient(LlmClient):
    """Anthropic Claude API (anthropic SDK)"""
    async def generate(self, prompt, system_prompt) -> LlmResponse:
        response = await self.client.messages.create(
            model=self.model_name,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        return LlmResponse(...)

class ChatGptClient(LlmClient):
    """OpenAI ChatGPT API (openai SDK)"""
    # response_format={"type": "json_object"} 네이티브 지원

class GeminiClient(LlmClient):
    """Google Gemini API (google-generativeai SDK)"""
    # response_mime_type="application/json" 지원

async def get_active_llm_client(db: AsyncSession) -> LlmClient:
    """DB에서 활성 프로바이더를 조회하여 해당 클라이언트 반환"""
    provider = await _get_active_provider(db)
    api_key = os.getenv(provider.api_key_env_name)
    if not api_key:
        raise ServiceUnavailableError("LLM API 키가 설정되지 않았습니다")

    clients = {
        "claude": ClaudeClient,
        "chatgpt": ChatGptClient,
        "gemini": GeminiClient,
    }
    return clients[provider.provider_name](api_key, provider.model_name)
```

## 프롬프트 관리 설계

```yaml
# backend/config/prompts.yaml
unified_analysis:
  system_prompt: |
    당신은 대한민국 법령 분석 전문가입니다.
    법령의 제개정이유와 개정문을 분석하여 관련 조례의 개정 필요 여부를 판단합니다.
    반드시 아래 JSON 형식으로만 응답하세요.

  user_prompt: |
    다음 법령의 제개정이유와 개정문을 분석하여, 아래 조례의 개정 필요 여부를 검토해 주세요.

    ## 상위법령 정보
    - 법령명: {law_name}
    - 공포일자: {law_proclaimed_date}

    ## 제개정이유
    {revision_reason}

    ## 개정문 내용
    {amendment_content}

    ## 자치법규 (조례) 정보
    - 조례명: {ordinance_name}

    ## 응답 형식 (JSON)
    ```json
    {
      "summary": {
        "main_changes": ["변경사항1", "변경사항2"],
        "affected_articles": ["제X조", "제Y조"],
        "ordinance_impact": "조례에 미치는 영향 설명"
      },
      "review_draft": {
        "result": "개정필요 또는 개정불필요",
        "content": "검토의견 내용"
      }
    }
    ```

summarize_long_text:
  system_prompt: |
    법령 텍스트를 핵심 내용만 간결하게 요약해 주세요.
  user_prompt: |
    다음 법령 텍스트를 핵심 내용만 요약해 주세요 (1000자 이내):
    {text}
```

## Complexity Tracking

> Constitution Check 위반 없음 - 해당 없음
