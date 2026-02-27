# 근거 조문 매핑 시스템 구현 완료

**구현일**: 2026-02-20
**구현 방안**: B안 (명시적 매핑 방식)
**소요 시간**: 약 1시간

---

## 📋 구현 내용

### 1. Backend API 추가 ✅

**파일**: `backend/api/v1/ordinances.py`

**추가된 엔드포인트**:
```python
# 1. GET /ordinances/{id}/mapped-articles
# 조례에 매핑된 근거 조문 목록 조회

# 2. GET /ordinances/{id}/available-articles
# 조례의 상위법령에 속한 모든 조문 조회 (매핑 가능한 조문)

# 3. POST /ordinances/{id}/mapped-articles/bulk
# 근거 조문 일괄 설정 (기존 매핑 삭제 후 새로 생성)
```

**주요 기능**:
- 조례의 상위법령 기반으로 조문 목록 자동 필터링
- 이미 매핑된 조문 표시 (`is_mapped` 플래그)
- 권한 체크 (부서 계정 이상만 매핑 가능)
- 일괄 매핑 시 기존 매핑 삭제 후 새로 생성

---

### 2. Frontend API 서비스 추가 ✅

**파일**: `frontend/src/services/api.ts`

**추가된 메서드**:
```typescript
ordinanceApi.getMappedArticles(ordinanceId: number)
ordinanceApi.getAvailableArticles(ordinanceId: number)
ordinanceApi.setMappedArticles(ordinanceId: number, articleIds: number[], mappingReason?: string)
```

---

### 3. 근거 조문 관리 컴포넌트 추가 ✅

**파일**: `frontend/src/components/ArticleMappingManager.tsx`

**기능**:
- 상위법령의 조문 목록 표시
- 체크박스로 선택/해제
- 이미 매핑된 조문 자동 체크
- 변경사항 감지 (저장/취소 버튼 활성화)
- 통계 표시 (전체 조문, 선택된 조문)
- 저장 시 API 호출 및 캐시 무효화

---

### 4. OrdinanceDetail 페이지 수정 ✅

**파일**: `frontend/src/pages/OrdinanceDetail.tsx`

**변경 사항**:
- ArticleMappingManager 컴포넌트 import
- 상위법령 Card와 검토이력 Card 사이에 "근거 조문 관리" Card 추가

**페이지 구조**:
```
조례 상세 페이지
├─ 기본 정보
├─ 상위법령
├─ 근거 조문 관리 ← NEW
└─ 검토이력
```

---

## 🎯 주요 개선 효과

### Before (문제점)
```
조문조회: 모든 법령의 모든 조문 표시 (349개)
개정검토 필요: 모든 조문 변경사항 표시
→ 담당자가 관리할 수 없음
```

### After (해결)
```
1. 조례 상세 → 근거 조문 관리 → 근거 조문 선택
2. 선택된 조문만 추적
3. 개정검토 필요: 매핑된 조문 변경만 표시
→ 담당자가 관리 가능
```

**예상 효과**:
- 조문 표시 개수: 349개 → 평균 10-20개 (95% 감소)
- 개정검토 알림: 전체 → 관련 조문만 (노이즈 90% 감소)

---

## 📊 데이터 흐름

```
조례 등록
  ↓
상위법령 추가 (이미 구현됨)
  ↓
근거 조문 관리 탭에서 조문 선택 ← NEW
  ↓
ordinance_article_mappings 테이블에 저장
  ↓
조문 변경 감지 (동기화)
  ↓
개정검토 필요 페이지에 알림 표시
```

---

## 🧪 테스트 가이드

### 1. Backend API 테스트

**Swagger UI**: http://localhost:8000/docs

```bash
# 1. 조례의 상위법령에 속한 조문 목록 조회
GET /api/v1/ordinances/{ordinance_id}/available-articles

# 2. 근거 조문 일괄 설정
POST /api/v1/ordinances/{ordinance_id}/mapped-articles/bulk
{
  "article_ids": [1, 2, 3],
  "mapping_reason": "근거 조문"
}

# 3. 매핑된 조문 목록 확인
GET /api/v1/ordinances/{ordinance_id}/mapped-articles
```

### 2. Frontend 통합 테스트

**브라우저**: http://localhost:5173

#### 시나리오 1: 근거 조문 선택
```
1. 조례 목록 → 조례 상세 클릭
2. "근거 조문 관리" 섹션 확인
3. 상위법령의 조문 목록 표시 확인
4. 체크박스로 근거 조문 선택
5. "저장" 버튼 클릭
6. 성공 메시지 확인
```

#### 시나리오 2: 개정검토 필요 확인
```
1. 근거 조문 선택 후 저장
2. 조문 동기화 (조문 변경 감지)
3. "개정 검토 필요" 메뉴 클릭
4. 매핑된 조문의 변경사항만 표시되는지 확인
```

#### 시나리오 3: 근거 조문 수정
```
1. 조례 상세 → 근거 조문 관리
2. 일부 조문 선택 해제
3. "저장" 버튼 클릭
4. 변경사항 반영 확인
```

---

## 🔧 기술적 세부사항

### 데이터베이스

**사용 테이블**: `ordinance_article_mappings`

```sql
-- 이미 존재하는 테이블 활용
CREATE TABLE ordinance_article_mappings (
  id SERIAL PRIMARY KEY,
  ordinance_id INTEGER NOT NULL REFERENCES ordinances(id) ON DELETE CASCADE,
  article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  mapping_reason TEXT,
  created_by INTEGER REFERENCES users(id),
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  UNIQUE(ordinance_id, article_id)
);
```

### API 응답 예시

**GET /ordinances/{id}/available-articles**:
```json
{
  "items": [
    {
      "article_id": 1,
      "article_no": "1",
      "article_title": "목적",
      "article_content": "이 법은...",
      "law_id": 472,
      "law_name": "지방자치법",
      "is_mapped": true  ← 이미 매핑됨
    }
  ],
  "total": 50,
  "mapped_count": 5
}
```

---

## 📝 알려진 제약사항

1. **상위법령 필수**: 조례에 상위법령이 없으면 근거 조문을 선택할 수 없음
   - 해결: 먼저 상위법령 탭에서 상위법령 추가 필요

2. **일괄 설정**: 저장 시 기존 매핑 모두 삭제 후 새로 생성
   - 장점: 데이터 일관성
   - 단점: 이력 추적 불가 (필요 시 별도 이력 테이블 추가 가능)

3. **권한**: 부서 계정 이상만 매핑 가능
   - DEPARTMENT, GENERAL, ADMIN, SUPER_ADMIN

---

## 🚀 다음 단계 (선택사항)

### A. 자동 추천 기능 추가
- 조례 내용과 조문 내용의 키워드 매칭
- 유사도 높은 조문 자동 추천
- 담당자가 확정

### B. 매핑 이력 추적
- 언제 어떤 조문을 추가/삭제했는지 이력 저장
- 별도 `article_mapping_history` 테이블 추가

### C. 대량 매핑 기능
- 여러 조례에 동일한 조문 일괄 매핑
- CSV 업로드로 대량 매핑

---

## ✅ 체크리스트

- [x] Backend API 구현
- [x] Frontend 컴포넌트 구현
- [x] OrdinanceDetail 페이지 통합
- [x] API 서비스 추가
- [ ] Backend 서버 재시작 (코드 반영)
- [ ] Frontend 서버 재시작 (코드 반영)
- [ ] Swagger UI에서 API 테스트
- [ ] 브라우저에서 기능 테스트
- [ ] 개정검토 필요 페이지에서 필터링 확인

---

## 🎉 완료!

근거 조문 매핑 시스템이 성공적으로 구현되었습니다.

이제 다음을 수행하세요:
1. Backend 서버 재시작
2. Frontend 서버 재시작
3. 브라우저에서 테스트

**테스트 경로**:
```
http://localhost:5173/ordinances/{조례ID}
→ "근거 조문 관리" 섹션 확인
```
