# 조문 매핑 구조 개선 제안

## 📋 현재 문제점

1. **조문조회 페이지**: 모든 조문(349개) 표시
2. **개정검토 필요 페이지**: 모든 조문 변경사항 표시
3. **문제**: 조례와 무관한 조문까지 표시되어 담당자가 관리하기 어려움

## 🎯 목표

```
조례 → 상위법령(모법) → 근거 조문들만 추적
```

---

## 💡 해결 방안 비교

| 방안 | 장점 | 단점 | 구현 난이도 | 정확도 |
|------|------|------|-------------|--------|
| 1. 자동 필터링 | 즉시 적용 가능 | 불필요한 조문 포함 | ⭐ 쉬움 | ⭐⭐ 보통 |
| 2. 명시적 매핑 | 정확한 추적 | 초기 매핑 작업 필요 | ⭐⭐ 보통 | ⭐⭐⭐ 높음 |
| 3. 하이브리드 | 자동+수동 장점 | 구현 복잡 | ⭐⭐⭐ 어려움 | ⭐⭐⭐ 높음 |

---

## 🚀 권장 방안: 명시적 매핑 방식

### Step 1: 조례 상세 페이지에 "근거 조문 관리" 탭 추가

```
OrdinanceDetail.tsx
├─ 탭1: 기본 정보
├─ 탭2: 상위법령
├─ 탭3: 근거 조문 관리 ⭐ NEW
└─ 탭4: 검토 이력
```

### Step 2: 근거 조문 관리 UI

```tsx
// 탭3: 근거 조문 관리
<div>
  <h3>상위법령: 지방자치법</h3>

  <Alert>
    이 조례의 근거가 되는 조문을 선택하세요.
    선택한 조문이 변경되면 개정 검토 알림을 받습니다.
  </Alert>

  <Table>
    <Column title="선택" render={(record) => (
      <Checkbox
        checked={mappedArticles.includes(record.id)}
        onChange={() => toggleArticle(record.id)}
      />
    )} />
    <Column title="조문번호" dataIndex="article_no" />
    <Column title="제목" dataIndex="article_title" />
    <Column title="내용 미리보기" render={(record) => (
      record.article_content.substring(0, 100) + "..."
    )} />
  </Table>

  <Button onClick={saveMappings}>저장</Button>
</div>
```

### Step 3: API 수정

#### Backend API 추가
```python
# backend/api/v1/ordinances.py

@router.get("/{ordinance_id}/mapped-articles")
async def get_ordinance_mapped_articles(
    ordinance_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """조례에 매핑된 근거 조문 목록"""
    mappings = await db.execute(
        select(OrdinanceArticleMapping)
        .options(selectinload(OrdinanceArticleMapping.article))
        .where(OrdinanceArticleMapping.ordinance_id == ordinance_id)
    )
    return {"items": mappings.scalars().all()}


@router.post("/{ordinance_id}/mapped-articles/bulk")
async def set_ordinance_mapped_articles(
    ordinance_id: int,
    article_ids: List[int],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """조례의 근거 조문 일괄 설정"""
    # 1. 기존 매핑 삭제
    await db.execute(
        delete(OrdinanceArticleMapping)
        .where(OrdinanceArticleMapping.ordinance_id == ordinance_id)
    )

    # 2. 새로운 매핑 생성
    for article_id in article_ids:
        mapping = OrdinanceArticleMapping(
            ordinance_id=ordinance_id,
            article_id=article_id,
            mapping_reason="근거 조문",
            created_by=current_user.id,
        )
        db.add(mapping)

    await db.commit()
    return {"success": True, "count": len(article_ids)}
```

#### Frontend API 추가
```typescript
// frontend/src/services/api.ts

export const ordinanceApi = {
  // 기존 메서드들...

  // 조례의 매핑된 근거 조문 목록
  getMappedArticles: async (ordinanceId: number) => {
    const { data } = await api.get(`/ordinances/${ordinanceId}/mapped-articles`)
    return data
  },

  // 근거 조문 일괄 설정
  setMappedArticles: async (ordinanceId: number, articleIds: number[]) => {
    const { data } = await api.post(
      `/ordinances/${ordinanceId}/mapped-articles/bulk`,
      { article_ids: articleIds }
    )
    return data
  },
}
```

### Step 4: 개정검토 필요 로직 수정

#### 기존 (문제)
```sql
-- 모든 조문 변경사항 표시
SELECT * FROM article_changes
WHERE detected_at >= '최근 30일'
```

#### 수정 (해결)
```sql
-- 매핑된 조문의 변경사항만 표시
SELECT
  ordinances.id,
  ordinances.name,
  articles.article_no,
  article_changes.*
FROM article_changes
JOIN articles ON article_changes.article_id = articles.id
JOIN ordinance_article_mappings ON articles.id = ordinance_article_mappings.article_id
JOIN ordinances ON ordinance_article_mappings.ordinance_id = ordinances.id
WHERE article_changes.detected_at >= '최근 30일'
```

이 쿼리는 이미 구현되어 있음! (`backend/api/v1/articles.py:546`)

---

## 📊 구현 순서

### 즉시 적용 가능 (방안 1)

**조문조회 페이지 필터 추가:**
```tsx
// ArticleList.tsx
<Select placeholder="상위법령 선택">
  {laws.map(law => (
    <Option key={law.id} value={law.id}>{law.law_name}</Option>
  ))}
</Select>
```

**개정검토 필요 페이지:**
- 이미 구현된 쿼리가 매핑된 조문만 표시하도록 되어 있음
- 문제: 매핑이 안 되어 있으면 아무것도 표시 안 됨

### 권장 구현 (방안 2)

**Phase A: UI 추가 (30분)**
1. OrdinanceDetail에 "근거 조문 관리" 탭 추가
2. 상위법령의 조문 목록 표시
3. 체크박스로 선택 기능

**Phase B: API 추가 (30분)**
1. GET `/ordinances/{id}/mapped-articles` 구현
2. POST `/ordinances/{id}/mapped-articles/bulk` 구현

**Phase C: 초기 데이터 매핑 (담당자 작업)**
1. 각 조례 담당자가 근거 조문 선택
2. 또는 자동 추천 기능 사용 (Phase D)

**Phase D: 자동 추천 기능 (선택사항, 1시간)**
1. 조례 내용과 조문 내용의 키워드 매칭
2. 유사도 높은 조문 자동 추천
3. 담당자가 확정

---

## 🎯 예상 효과

### Before (현재)
- 조문조회: 349개 조문 모두 표시
- 개정검토 필요: 모든 변경사항 표시
- 담당자 혼란 ⚠️

### After (개선)
- 조문조회: 내 조례의 상위법령 조문만 표시
- 개정검토 필요: 내 조례가 근거하는 조문 변경만 표시
- 담당자 편의성 향상 ✅

### 수치 예상
- 조문 표시 개수: 349개 → 평균 10-20개 (95% 감소)
- 개정검토 알림: 모든 변경 → 관련 변경만 (노이즈 90% 감소)

---

## 💬 의사결정 질문

1. **어떤 방안을 선호하시나요?**
   - [ ] 방안 1: 자동 필터링 (빠름, 부정확)
   - [ ] 방안 2: 명시적 매핑 (느림, 정확) ⭐ 권장
   - [ ] 방안 3: 하이브리드 (복잡, 최적)

2. **초기 매핑 작업을 누가 하나요?**
   - [ ] 담당자가 직접 (정확)
   - [ ] 자동 추천 후 확정 (반자동)
   - [ ] 전체 자동 (빠름)

3. **즉시 적용할까요, 아니면 완전 구현할까요?**
   - [ ] 즉시: 상위법령 필터만 추가 (10분)
   - [ ] 완전: 근거 조문 매핑 시스템 구축 (2시간)

제가 바로 구현해드릴 수 있습니다. 어떤 방안으로 진행할까요?
