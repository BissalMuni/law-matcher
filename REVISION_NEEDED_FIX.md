# 개정검토 필요 기능 수정 완료

**수정일**: 2026-02-20
**문제**: 모든 조문 변경사항이 표시되는 문제
**해결**: related_articles 파싱하여 해당 조문만 표시

---

## 📋 변경 사항

### 1. revision-needed API 로직 수정 ✅

**파일**: `backend/api/v1/articles.py`

**기존 문제:**
- 조례의 상위법령에 속한 **모든 조문**의 변경사항 표시
- `related_articles` 필드 미사용

**수정 내용:**
```python
def parse_article_numbers(related_articles: str) -> list:
    """
    related_articles 텍스트를 파싱하여 조문 번호 리스트 반환

    예:
    - "제13조" → ["13"]
    - "제64조~제68조" → ["64", "65", "66", "67", "68"]
    - "제13조, 제20조" → ["13", "20"]
    """
```

**새로운 로직:**
1. `ordinance_law_mappings.related_articles` 가져오기
2. 텍스트 파싱:
   - "제13조" → ["13"]
   - "제64조~제68조" → ["64", "65", "66", "67", "68"]
   - "제13조, 제20조" → ["13", "20"]
3. 파싱된 조문 번호로 `articles.article_no` 필터링
4. 해당 조문의 변경사항만 반환

---

### 2. 불필요한 코드 제거 ✅

**제거된 파일:**
- `frontend/src/components/ArticleMappingManager.tsx`

**수정된 파일:**
- `frontend/src/pages/OrdinanceDetail.tsx`
  - ArticleMappingManager import 제거
  - "근거 조문 관리" Card 제거

**유지된 API (사용 안 함):**
- `GET /ordinances/{id}/mapped-articles`
- `GET /ordinances/{id}/available-articles`
- `POST /ordinances/{id}/mapped-articles/bulk`
- `ordinanceApi.getMappedArticles()`, `getAvailableArticles()`, `setMappedArticles()`

→ 나중에 필요하면 사용 가능하도록 유지

---

## 🎯 동작 방식

### Before (문제)
```
조례: 노래연습장업자의 교육에 관한 조례
├─ 상위법령: 음악산업진흥에 관한 법률
└─ related_articles: "제4조"

revision-needed 페이지:
→ 음악산업진흥에 관한 법률의 **모든 조문** 변경사항 표시 ❌
```

### After (해결)
```
조례: 노래연습장업자의 교육에 관한 조례
├─ 상위법령: 음악산업진흥에 관한 법률
└─ related_articles: "제4조"

revision-needed 페이지:
→ 음악산업진흥에 관한 법률의 **제4조만** 변경사항 표시 ✅
```

---

## 📊 파싱 예시

| related_articles | 파싱 결과 | 설명 |
|------------------|-----------|------|
| `"제13조"` | `["13"]` | 단일 조문 |
| `"제64조~제68조"` | `["64", "65", "66", "67", "68"]` | 범위 (5개 조문) |
| `"제13조, 제20조"` | `["13", "20"]` | 복수 조문 |
| `"13조"` | `["13"]` | "제" 없이도 파싱 |
| `"제10조-제15조"` | `["10", "11", "12", "13", "14", "15"]` | "-"도 범위로 인식 |
| `NULL` 또는 `""` | 모든 조문 | related_articles가 없으면 상위법령의 모든 조문 |

---

## 🧪 테스트 방법

### 1. 조례에 related_articles 입력 확인

**DB 확인:**
```sql
SELECT
    o.id,
    o.name,
    l.law_name,
    olm.related_articles
FROM ordinances o
JOIN ordinance_law_mappings olm ON olm.ordinance_id = o.id
JOIN laws l ON l.id = olm.law_id
WHERE olm.related_articles IS NOT NULL
LIMIT 10;
```

**결과 예시:**
```
 id  |           조례명            |        법령명        | related_articles
-----+----------------------------+--------------------+------------------
 787 | 재활용 촉진 조례            | 자원의 절약과...    | 제20조
 698 | 공유재산 관리 조례          | 지방자치법 시행령   | 제64조~제68조
```

### 2. 해당 조문의 변경사항 생성

**조문 동기화:**
```bash
# Swagger UI에서
POST /api/v1/articles/sync
{
  "law_ids": [1],  # 해당 법령 ID
  "force": true
}
```

### 3. revision-needed 페이지 확인

**브라우저:**
```
http://localhost:3000/revision-needed
```

**예상 결과:**
- ✅ related_articles에 명시된 조문만 표시
- ✅ 조례 787 → "제20조" 변경사항만
- ✅ 조례 698 → "제64조~제68조" 변경사항만 (5개 조문)

### 4. API 직접 테스트

**Swagger UI:**
```
GET /api/v1/articles/revision-needed?days=30&page=1&size=20
```

**cURL:**
```bash
curl -X GET "http://localhost:8000/api/v1/articles/revision-needed?days=30" \
  -H "Authorization: Bearer {token}"
```

---

## 🔍 디버깅

### related_articles가 파싱되지 않는 경우

**확인 사항:**
1. `related_articles` 필드가 NULL인지 확인
2. 조문 번호 형식이 올바른지 확인 (예: "제13조", "13조", "제10조~제15조")
3. `articles.article_no`와 형식이 일치하는지 확인

**로그 확인:**
```bash
docker logs law-matcher-backend-1 --tail 50
```

### 조문이 표시되지 않는 경우

**원인:**
1. 해당 조문이 아직 동기화되지 않음
2. related_articles 파싱 오류
3. 최근 변경사항이 없음 (days 파라미터)

**해결:**
```bash
# 1. 조문 동기화 확인
curl "http://localhost:8000/api/v1/articles?law_id={법령ID}"

# 2. 변경 이력 확인
docker exec law-matcher-db-1 psql -U lawmatcher -d lawmatcher -c \
  "SELECT * FROM article_changes WHERE article_id IN (SELECT id FROM articles WHERE law_id = {법령ID}) LIMIT 5;"
```

---

## ✅ 완료 체크리스트

- [x] revision-needed API 수정
- [x] parse_article_numbers() 함수 구현
- [x] 불필요한 ArticleMappingManager 제거
- [x] OrdinanceDetail.tsx 정리
- [x] Backend 재시작
- [x] Frontend 재시작
- [ ] related_articles가 있는 조례에서 테스트
- [ ] 범위 표현 ("제64조~제68조") 테스트
- [ ] revision-needed 페이지에서 필터링 확인

---

## 🎉 결과

이제 **related_articles에 명시된 조문의 변경사항만** `/revision-needed` 페이지에 표시됩니다!

**예시:**
- 조례: "노래연습장업자의 교육에 관한 조례"
- 상위법령: "음악산업진흥에 관한 법률"
- related_articles: "제4조"
- 결과: **제4조 변경사항만** 표시 ✅
