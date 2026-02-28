# Research: 006-llm-review-assistant

**Date**: 2026-02-28
**Input**: spec.md

## 기존 구현 현황

### LLM 관련 코드

| 구분 | 상태 | 위치 | 비고 |
|------|------|------|------|
| LLM 클라이언트 | ❌ 없음 (메인 백엔드) | — | `.law-api/llm_processor.py`에 프로토타입 있으나 세금 전용, 재사용 부적합 |
| RAG 시스템 | ❌ 해당 없음 | `.law-api/rag_system.py` | 프로토타입, 이 기능에서는 불필요 |
| LLM 설정 | ❌ 없음 | `backend/core/config.py` | API 키/모델명 환경변수 미정의 |
| LLM 의존성 | ❌ 없음 | `requirements.txt` | openai/anthropic 패키지 미포함 |

### 검토의견 관련 기존 코드

| 구분 | 상태 | 위치 | 비고 |
|------|------|------|------|
| OrdinanceReview 모델 | ✅ 존재 | `backend/models/ordinance_review.py` | AI 필드 없음 (is_ai_generated 등) |
| 검토의견 CRUD | ✅ 존재 | `backend/services/ordinance_service.py` | create/update/approve |
| 검토의견 API | ✅ 존재 | `backend/api/v1/ordinances.py` | POST/PUT/DELETE/approve |
| 검토의견 UI | ✅ 존재 | `frontend/src/pages/OrdinanceDetail.tsx` | 타임라인 표시 + 모달 |

### 누락 사항

1. **OrdinanceReview 모델**: `is_ai_generated`, `ai_modified`, `ai_model`, `ai_generated_at` 필드 없음
2. **LlmAnalysisResult 모델**: 전체 신규
3. **LLM 클라이언트**: 전체 신규 (격리 모듈)
4. **LLM 서비스**: 전체 신규 (요약/초안 생성 로직)
5. **프론트엔드 AI 버튼**: 없음 (AI 요약, AI 초안 생성)

## LLM 프로바이더 선택

spec에서 특정 프로바이더를 지정하지 않았음. 선택지:

| 프로바이더 | 장점 | 단점 |
|-----------|------|------|
| OpenAI (GPT-4) | 안정적 API, 넓은 생태계 | 비용, 외부 의존 |
| Anthropic (Claude) | 법률 텍스트 분석 우수, 한국어 강점 | 비교적 신규 |
| 로컬 (HuggingFace) | 비용 없음, 외부 의존 없음 | 품질 낮음, GPU 필요 |

**결정 보류**: plan 단계에서 프로바이더 추상화 설계 (인터페이스 분리). 구현 시점에 결정.

## 005(제개정이유) → 006(LLM) 연계

005에서 수집하는 `LawRevisionReason.revision_reason`(제개정이유)과 `amendment_content`(개정문)가 006의 LLM 입력 데이터:

```
005: 법제처 API → LawRevisionReason (DB 캐시)
006: LawRevisionReason + Ordinance 정보 → LLM API → 요약/초안
```

**의존성**: 006은 005의 LawRevisionReason 테이블에서 데이터를 가져옴.

## 아키텍처 설계

```
Frontend (OrdinanceDetail.tsx)
  ├─ "AI 요약" 버튼 → POST /ordinances/{id}/ai-summary
  └─ "AI 초안 생성" 버튼 → POST /ordinances/{id}/ai-draft
         │
Backend API (llm_reviews.py)
         │
LLM Review Service (llm_review_service.py)
  ├─ LlmAnalysisResult 캐시 확인 (1회 실행 원칙)
  ├─ 입력 데이터 준비 (제개정이유 + 조례 정보)
  └─ LLM Client 호출
         │
LLM Client (llm_client.py) ← III. 외부 의존 격리
  ├─ 프로바이더 추상화 인터페이스
  ├─ 재시도 (최대 2회) + 타임아웃 (30초)
  └─ 토큰 사용량 추적
         │
External: LLM API (Anthropic/OpenAI)
```

## 결론

006은 **전면 신규 구현** 피처:
- 백엔드: LLM 클라이언트 모듈, 서비스, API 3개, 모델 1개 + 기존 모델 수정
- 프론트엔드: AI 버튼 2개, 결과 표시 패널, 비활성화 로직
- 설정: 환경변수, 의존성 추가
- 005 데이터에 의존 (LawRevisionReason)
