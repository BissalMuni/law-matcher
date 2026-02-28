# Research: 005-revision-detection-tabs

**Date**: 2026-02-28
**Input**: spec.md

## 기존 구현 현황

### 탭별 현황

| 탭 | 백엔드 데이터 | 백엔드 로직 | 프론트엔드 | 비고 |
|----|-------------|------------|-----------|------|
| **A. 공포일자** | ✅ Law.proclaimed_date 존재 | ✅ Core Rule 비교 구현 | ✅ 상위법령 목록에 표시 | 탭 UI 구조화 필요 |
| **B. 조문변경** | ⚠️ ArticleChange 존재, 조문제개정유형 미수집 | ✅ content_hash 기반 감지 | ✅ ArticleList/Detail, RevisionNeeded | 조문변경여부/제개정유형 필드 추가 필요 |
| **C. 제개정이유** | ❌ 모델/필드 없음 | ❌ API 파싱 없음 | ❌ UI 없음 | **전면 신규 구현** |

### 주요 코드 위치

| 구분 | 파일 | 탭 관련 |
|------|------|---------|
| moleg_client | `backend/external/moleg_client.py` | A/B/C — 제개정이유/개정문/조문메타 파싱 미구현 |
| Law ORM | `backend/models/law.py` | A — proclaimed_date 존재 |
| Article ORM | `backend/models/article.py` | B — content_hash 존재, 조문제개정유형 없음 |
| ArticleChange ORM | `backend/models/article_change.py` | B — change_type/diff_html 존재 |
| LawSyncService | `backend/services/law_sync_service.py` | A — 공포일자 비교 구현 |
| ArticleService | `backend/services/article_service.py` | B — 해시 기반 변경 감지 구현 |
| OrdinanceDetail | `frontend/src/pages/OrdinanceDetail.tsx` | A — 상위법령 카드 (탭 구조 아님) |
| RevisionNeeded | `frontend/src/pages/RevisionNeededList.tsx` | B — 변경 조문 기반 목록 |

## 법제처 API 데이터 조사

### lawService.do 응답 구조 (JSON)

```json
{
  "법령": {
    "기본정보": { "법령명_한글": "...", "공포일자": "20260101", ... },
    "조문": {
      "조문단위": [
        {
          "조문번호": "제1조",
          "조문제목": "...",
          "조문내용": "...",
          "조문제개정유형": "일부개정",  // ← 탭B 필요
          "조문변경여부": "Y"           // ← 탭B 필요
        }
      ]
    },
    "제개정이유": {
      "제개정이유내용": [["[일부개정]", "◇ 개정이유...", ...]]  // ← 탭C 필요
    },
    "개정문": {
      "개정문내용": [["⊙법률 제XXXXX호", "제X조...", ...]]     // ← 탭C 필요
    }
  }
}
```

### 주의사항

- **일부개정 MST** 조회 시 `조문단위`가 0건 (개정 부분만 반환)
- 현행 전체 조문은 **현행법 MST**로 별도 조회 필요
- `제개정이유내용`: `list[list[str]]` → `"\n".join(data[0])`으로 텍스트 복원
- `개정문내용`: 동일 구조

### 개정문에서 조문번호 추출

```python
import re
pattern = r'제(\d+조(?:의\d+)?)'
matches = re.findall(pattern, amendment_text)
# "제10조의2제1항" → "제10조의2"
# "제22조의2" → "제22조의2"
```

## 신규 구현 필요 사항

### 1. MolegClient 확장

`get_law_detail()` 메서드에서 추가 파싱:
- `법령.제개정이유.제개정이유내용` → 텍스트 변환
- `법령.개정문.개정문내용` → 텍스트 변환
- `조문단위[].조문제개정유형` → Article 메타데이터
- `조문단위[].조문변경여부` → Article 메타데이터

### 2. 신규 모델: LawRevisionReason

법령의 제개정이유/개정문 캐시:
- law_id (FK), law_mst
- revision_reason_content (TEXT)
- amendment_content (TEXT)
- extracted_articles (JSON) — 개정문에서 추출한 조문번호 목록
- fetched_at (TIMESTAMP)

### 3. 신규 모델: RevisionDetectionResult

탭별 판별 결과 통합 저장 (비교 뷰용):
- ordinance_id, law_id
- detection_method (ENUM: 'A_PROCLAIMED_DATE', 'B_ARTICLE_CHANGE', 'C_REVISION_REASON')
- needs_revision (BOOLEAN)
- detail (JSON) — 방법별 상세 정보
- detected_at

### 4. Article 모델 확장

- `revision_type_detail` (VARCHAR): 조문제개정유형 (신설/일부개정/전부개정 등)
- `change_flag` (VARCHAR): 조문변경여부 (Y/N)

### 5. 프론트엔드 구조 변경

OrdinanceDetail.tsx를 Ant Design `<Tabs>`로 재구성:
- Tab A: 기존 상위법령 카드 → 공포일자 비교 뷰
- Tab B: ArticleChange 기반 조문 변경 뷰
- Tab C: **신규** 제개정이유 + 개정문 파싱 결과 뷰
- Tab 비교: 관리자용 3탭 결과 비교 뷰

## 외부 의존성

| 의존성 | 용도 | 현재 상태 |
|--------|------|-----------|
| 법제처 lawService.do (JSON) | 제개정이유/개정문 데이터 | ✅ 기본 호출 구현, 파싱 확장 필요 |
| 정규식 파서 | 개정문에서 조문번호 추출 | ❌ 신규 구현 |

## 결론

005는 **가장 신규 개발이 많은 피처**:
- 탭A: UI 구조화만 (데이터/로직 완성)
- 탭B: Article 메타 필드 추가 + UI 구조화
- 탭C: **전면 신규** (API 파싱, 모델, 서비스, UI)
- 탭비교: 신규 UI
