# Research: 006-llm-review-assistant

**Date**: 2026-03-02 (updated)
**Input**: spec.md (post-clarification v2)

## 기존 구현 현황

### LLM 관련 코드

| 구분 | 상태 | 위치 | 비고 |
|------|------|------|------|
| LLM 클라이언트 | ❌ 없음 | — | `.law-api/llm_processor.py`에 프로토타입 있으나 재사용 부적합 |
| LLM 프로바이더 관리 | ❌ 없음 | — | DB 테이블, 관리자 UI 모두 신규 |
| LLM 설정 | ❌ 없음 | `backend/core/config.py` | API 키 환경변수 미정의 |
| LLM 의존성 | ❌ 없음 | `requirements.txt` | anthropic/openai/google-generativeai 미포함 |
| 프롬프트 관리 | ❌ 없음 | — | YAML 설정 파일 신규 |
| Rate Limiting | ❌ 없음 | — | Redis 기반 제한 신규 |

### 검토의견 관련 기존 코드

| 구분 | 상태 | 위치 | 비고 |
|------|------|------|------|
| OrdinanceReview 모델 | ✅ 존재 | `backend/models/ordinance_review.py` | AI 필드 없음 |
| 검토의견 CRUD | ✅ 존재 | `backend/services/ordinance_service.py` | create/update/approve |
| 검토의견 API | ✅ 존재 | `backend/api/v1/ordinances.py` | POST/PUT/DELETE/approve |
| 검토의견 UI | ✅ 존재 | `frontend/src/pages/OrdinanceDetail.tsx` | 타임라인 + 모달 (766줄) |

### 누락 사항 (전체 신규)

1. **LlmProvider 모델**: 프로바이더/모델 DB 관리 (clarification에서 추가)
2. **LlmAnalysisResult 모델**: 통합 분석 결과 (요약+초안 동시 저장)
3. **OrdinanceReview AI 필드**: `is_ai_generated`, `ai_modified`, `ai_analysis_id`
4. **LLM 클라이언트 추상화**: ABC + 3개 프로바이더 구현 (Claude/ChatGPT/Gemini)
5. **LLM 분석 서비스**: 통합 호출 로직, 1회 실행 검증, 토큰 초과 2단계 처리
6. **API 엔드포인트**: 통합 분석(POST), 결과 조회(GET), 프로바이더 관리(Admin)
7. **프롬프트 YAML**: `backend/config/prompts.yaml`
8. **Rate Limiter**: Redis 기반 시스템 전체 제한
9. **프론트엔드 AI 컴포넌트**: 분석 버튼, 요약 패널, 초안 채움, "AI 생성" 라벨
10. **관리자 LLM 설정 탭**: 프로바이더 목록, 모델 변경, 활성 전환

## 기존 코드 패턴 분석

### 백엔드 모델 패턴

```python
# 공통 패턴: SQLAlchemy 2.0 Mapped + relationship
class ExampleModel(Base):
    __tablename__ = "examples"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    # FK: ondelete="CASCADE" for detail, "SET NULL" for optional
    # Index: ix_{table}_{column}
    # Unique: UniqueConstraint
```

### 백엔드 서비스 패턴

```python
class ExampleService:
    def __init__(self, db: AsyncSession):
        self.db = db
    async def method(self, ...) -> Model:
        # select() → where() → execute() → scalars()
        # 에러: raise NotFoundError("...")
```

### 백엔드 API 패턴

```python
@router.post("/{id}/action", response_model=ResponseSchema)
async def action(
    id: int,
    body: RequestSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ExampleService(db)
    return await service.method(id, body, current_user)
```

### 외부 API 클라이언트 패턴

```python
# backend/external/moleg_client.py
class MolegClient:
    def __init__(self, api_key: str, base_url: str):
        self.client = httpx.AsyncClient(timeout=30.0)
    # httpx.AsyncClient, timeout=30s, raise_for_status()
```

### 프론트엔드 패턴

```typescript
// API: axios instance + JWT interceptor
const api = axios.create({ baseURL: '/api/v1' })
// Pages: React 18 functional + Ant Design 5 + TanStack Query 5
// Types: interface 정의, from_attributes=True 연동
```

## LLM 프로바이더 기술 조사

### SDK 패키지

| 프로바이더 | Python 패키지 | 주요 API |
|-----------|--------------|----------|
| Claude | `anthropic` | `client.messages.create()` |
| ChatGPT | `openai` | `client.chat.completions.create()` |
| Gemini | `google-generativeai` | `model.generate_content()` |

### 구조화 출력 (JSON) 지원

- **Claude**: `response_format` 미지원 → 프롬프트에서 JSON 형식 강제 + 파싱
- **ChatGPT**: `response_format={"type": "json_object"}` 네이티브 지원
- **Gemini**: `response_mime_type="application/json"` 지원

→ 공통 인터페이스에서 JSON 파싱 계층 추가. 프로바이더별로 구조화 출력 방식 분기.

### Rate Limiting 구현

Redis INCR + EXPIRE 패턴:
```python
key = "llm:rate_limit"
count = await redis.incr(key)
if count == 1:
    await redis.expire(key, 60)  # 1분 TTL
if count > limit:
    raise RateLimitExceeded
```

## 005 → 006 데이터 연계

```
005: 법제처 API → LawRevisionReason (revision_reason, amendment_content)
006: LawRevisionReason + Ordinance → LLM API → LlmAnalysisResult (summary + draft)
```

- `LawRevisionReason.revision_reason`: 제개정이유내용 (LLM 입력)
- `LawRevisionReason.amendment_content`: 개정문내용 (LLM 입력)
- 005가 미구현 시 006 LLM 입력 데이터 없음 → Edge Case 처리 필요

## 아키텍처 설계 (업데이트)

```
Frontend (OrdinanceDetail.tsx)
  └─ "AI 분석" 버튼 (1회) → POST /ordinances/{id}/ai-analyze
         │  ← 동기 응답 (로딩 스피너)
Backend API (llm_analysis.py)
         │
LLM Analysis Service (llm_analysis_service.py)
  ├─ 1회 실행 검증 (UNIQUE + status 확인)
  ├─ 입력 데이터 준비 (제개정이유 + 개정문 + 조례)
  ├─ 토큰 초과 검사 → [초과 시] 1차 요약 호출
  ├─ 프롬프트 렌더링 (prompts.yaml 템플릿)
  ├─ Rate Limit 검사 (Redis)
  └─ LLM Client 호출 → JSON 파싱 → DB 저장
         │
LLM Client (llm_client.py) ← III. 외부 의존 격리
  ├─ LlmClient ABC (공통 인터페이스)
  ├─ ClaudeClient / ChatGptClient / GeminiClient
  ├─ 프로바이더 선택: LlmProvider DB → is_active=True
  ├─ 타임아웃 30초, 재시도 최대 2회
  └─ JSON 구조화 출력 강제 + 파싱 검증
         │
LLM Provider DB (llm_providers)
  └─ 관리자 UI에서 모델명/활성 상태 변경
```

## 결론

006은 **전면 신규 구현** 피처:
- **백엔드**: LLM 클라이언트(3 프로바이더), 서비스, API, 모델 2개 + 기존 모델 수정, YAML 프롬프트, Redis Rate Limiter
- **프론트엔드**: AI 분석 버튼, 요약 패널, 초안 자동 채움, "AI 생성" 라벨, 관리자 LLM 설정 탭
- **인프라**: 3개 SDK 의존성 추가, YAML 설정 파일
- **의존성**: 005 LawRevisionReason 테이블
