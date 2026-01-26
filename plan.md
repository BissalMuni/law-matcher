# 대시보드 개선: 조례 개정 필요 항목 표시

## 📋 목표 및 요구사항

### 핵심 목표
상위법령 개정 시 조례 개정이 필요한 항목을 대시보드에서 한눈에 파악할 수 있도록 UI/UX 구성

### 핵심 로직
```
조례 개정 상태 자동 판별 기준:

🔴 NEEDS_REVISION (개정 필요 - 빨간색):
   ordinance.revision_date < law.proclaimed_date
   → 조례가 최신 법령을 반영하지 못했음

🟢 COMPLETED (개정 완료 - 초록색):
   ordinance.revision_date >= law.proclaimed_date
   → 조례가 최신 법령을 이미 반영함

🟡 UNDER_REVIEW (검토중 - 노란색):
   향후 확장을 위해 예약 (현재 단계에서는 미사용)
```

### 기술 요구사항
- ✅ 백엔드: 법제처 API 활용 (기존 인프라 활용)
- ✅ 상태 자동 계산: 조례 revision_date와 법령 proclaimed_date 비교
- ✅ 프론트엔드: 대시보드에 상태별 색상 표시 (빨강/초록)

---

## 🔍 현재 상황 분석

### 데이터베이스 현황
- **조례(ordinances)**: ~400개
- **상위법령(laws)**: ~500개
- **조례-법령 매핑(ordinance_law_mappings)**: ~600개
- **법령 변경 이력(law_changes)**: ~1,762개

### 현재 대시보드 구조
**위치**: `frontend/src/pages/Dashboard.tsx`

**현재 구성**:
```
┌─────────────────────────────────────────────┐
│  통계 카드 (4개)                              │
│  [자치법규] [상위법령] [최근개정] [검토필요]   │
└─────────────────────────────────────────────┘
┌─────────────────────────────────────────────┐
│  최근 법령 개정 (5건)                         │
└─────────────────────────────────────────────┘
┌─────────────────────────────────────────────┐
│  검토 대기 (5건)                              │
└─────────────────────────────────────────────┘
```

**현재 API 엔드포인트**:
- `GET /api/v1/dashboard/summary` - 통계 요약
- `GET /api/v1/dashboard/recent-amendments` - 최근 개정 5건
- `GET /api/v1/dashboard/pending-reviews` - 검토 대기 5건

---

## 🚀 구현 계획

### Phase 1: 백엔드 구현

#### 1-1. 새 API 엔드포인트 추가

**파일**: `backend/api/v1/dashboard.py`

```python
@router.get("/revision-needed", response_model=RevisionNeededListResponse)
async def get_revision_needed(
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, regex="^(NEEDS_REVISION|UNDER_REVIEW|COMPLETED)$"),
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    조례 개정 상태별 항목 조회

    로직:
    - ordinances와 laws를 ordinance_law_mappings로 JOIN
    - 상태 자동 계산:
      * ordinance.revision_date < law.proclaimed_date → NEEDS_REVISION (빨강)
      * ordinance.revision_date >= law.proclaimed_date → COMPLETED (초록)
    """
    service = DashboardService(db)
    return await service.get_revision_needed(limit, status, department)
```

#### 1-2. 새 스키마 정의

**파일**: `backend/schemas/dashboard.py`

```python
class RevisionNeededItem(BaseModel):
    """조례 개정 상태 항목"""
    ordinance_id: int
    ordinance_name: str
    ordinance_revision_date: Optional[date]  # 조례 마지막 개정일
    law_id: int
    law_name: str
    law_type: str  # 법률/대통령령/총리령/부령
    law_proclaimed_date: Optional[date]  # 상위법령 공포일
    days_diff: int  # 날짜 차이 (일수)
    revision_status: str  # NEEDS_REVISION/COMPLETED
    department: Optional[str]  # 소관부서

    class Config:
        from_attributes = True


class RevisionNeededListResponse(BaseModel):
    """조례 개정 상태 목록 응답"""
    total: int
    needs_revision_count: int  # 빨강 (개정 필요)
    completed_count: int  # 초록 (개정 완료)
    items: List[RevisionNeededItem]
```

#### 1-3. DashboardSummary 업데이트

**파일**: `backend/schemas/dashboard.py`

기존 DashboardSummary 스키마에 필드 추가:
```python
class DashboardSummary(BaseModel):
    total_ordinances: int
    total_parent_laws: int
    recent_amendments: int
    need_revision_count: int  # 기존 필드
    revision_needs_action_count: int  # 🆕 새 필드 (개정 필요 - 빨강)
    revision_completed_count: int  # 🆕 새 필드 (개정 완료 - 초록)
```

#### 1-4. 비즈니스 로직 구현

**파일**: `backend/services/dashboard_service.py`

두 개의 메서드 추가:
1. `get_revision_needed()` - 조례 개정 상태별 목록 조회
2. `get_summary()` 업데이트 - 상태별 카운트 계산 추가

핵심 SQL 로직:
```sql
SELECT
    o.id, o.name, o.revision_date, o.department,
    l.id, l.law_name, l.law_type, l.proclaimed_date,
    (l.proclaimed_date - o.revision_date) as days_diff,
    CASE
        WHEN o.revision_date < l.proclaimed_date THEN 'NEEDS_REVISION'
        ELSE 'COMPLETED'
    END as revision_status
FROM ordinances o
INNER JOIN ordinance_law_mappings m ON o.id = m.ordinance_id
INNER JOIN laws l ON m.law_id = l.id
WHERE o.revision_date IS NOT NULL
  AND l.proclaimed_date IS NOT NULL
ORDER BY
    CASE
        WHEN o.revision_date < l.proclaimed_date THEN 1
        ELSE 2
    END,
    ABS(l.proclaimed_date - o.revision_date) DESC
LIMIT 10
```

상태 분류 (자동):
- `NEEDS_REVISION` (🔴 빨강): ordinance.revision_date < law.proclaimed_date
- `COMPLETED` (🟢 초록): ordinance.revision_date >= law.proclaimed_date
- `UNDER_REVIEW` (🟡 노랑): 향후 확장용 (현재 미사용)

---

### Phase 2: 프론트엔드 구현

#### 2-1. API 타입 정의

**파일**: `frontend/src/types/api.ts`

```typescript
export interface RevisionNeededItem {
  ordinance_id: number;
  ordinance_name: string;
  ordinance_revision_date: string | null;
  law_id: number;
  law_name: string;
  law_type: string;
  law_proclaimed_date: string | null;
  days_diff: number;
  revision_status: 'NEEDS_REVISION' | 'UNDER_REVIEW' | 'COMPLETED';
  department: string | null;
}

export interface RevisionNeededListResponse {
  total: number;
  needs_revision_count: number;  // 빨강 (개정 필요)
  completed_count: number;  // 초록 (개정 완료)
  items: RevisionNeededItem[];
}

export interface DashboardSummary {
  total_ordinances: number;
  total_parent_laws: number;
  recent_amendments: number;
  need_revision_count: number;
  revision_needs_action_count: number; // 🆕 개정 필요 (빨강)
  revision_completed_count: number; // 🆕 개정 완료 (초록)
}
```

#### 2-2. API 함수 추가

**파일**: `frontend/src/services/api.ts`

```typescript
export const getRevisionNeeded = async (
  limit: number = 10,
  status?: 'NEEDS_REVISION' | 'UNDER_REVIEW' | 'COMPLETED',
  department?: string
): Promise<RevisionNeededListResponse> => {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (status) params.append('status', status);
  if (department) params.append('department', department);

  const response = await api.get(`/dashboard/revision-needed?${params}`);
  return response.data;
};
```

#### 2-3. Dashboard.tsx 개선

**파일**: `frontend/src/pages/Dashboard.tsx`

**개선 사항**:
1. 5번째 통계 카드 추가: "개정 필요" (빨간색 강조, NEEDS_REVISION 카운트)
2. 새 섹션 추가: "조례 개정 상태 (상위법령 개정 추적)"
3. React Query 훅 추가: `useQuery(['dashboard', 'revision-needed'])`
4. 상태 태그 렌더링:
   - 🔴 NEEDS_REVISION (빨강) - 개정 필요
   - 🟢 COMPLETED (초록) - 개정 완료
5. 테이블 컬럼: 상태 | 조례명 | 조례개정일 | 상위법령 | 법령공포일 | 날짜차이 | 소관부서

**새로운 대시보드 구조**:
```
┌─────────────────────────────────────────────────────────┐
│  통계 카드 (5개)                                          │
│  [자치법규] [상위법령] [최근개정] [검토필요] [🆕개정필요] │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  🆕 조례 개정 상태 (상위법령 개정 추적)                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 상태  | 조례명 | 조례개정일 | 상위법령 | 법령공포일│   │
│  │  🔴   | ...   | 2022-01-01 | ...     | 2024-06-01│   │
│  │  🔴   | ...   | 2021-03-15 | ...     | 2024-01-10│   │
│  │  🟢   | ...   | 2024-08-01 | ...     | 2024-03-20│   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 📝 구현 단계 (Step-by-Step)

### Step 1: 백엔드 스키마 추가
- [ ] `backend/schemas/dashboard.py`에 `RevisionNeededItem`, `RevisionNeededListResponse` 추가
  - `revision_status: str` 필드 (NEEDS_REVISION/COMPLETED)
  - `days_diff: int` 필드 (날짜 차이)
- [ ] `DashboardSummary`에 필드 추가:
  - `revision_needs_action_count: int` (빨강 카운트)
  - `revision_completed_count: int` (초록 카운트)

### Step 2: 백엔드 서비스 로직
- [ ] `backend/services/dashboard_service.py`에 `get_revision_needed()` 메서드 구현
  - CASE 문으로 상태 자동 계산
  - 상태별 필터링 지원
- [ ] `get_summary()`에 상태별 카운트 계산 로직 추가

### Step 3: 백엔드 API 엔드포인트
- [ ] `backend/api/v1/dashboard.py`에 `GET /revision-needed` 엔드포인트 추가
  - status 파라미터: NEEDS_REVISION/COMPLETED

### Step 4: 프론트엔드 타입 정의
- [ ] `frontend/src/types/api.ts`에 타입 추가
  - `revision_status` 타입 정의

### Step 5: 프론트엔드 API 함수
- [ ] `frontend/src/services/api.ts`에 `getRevisionNeeded()` 함수 추가

### Step 6: 대시보드 UI 개선
- [ ] `Dashboard.tsx`에 5번째 통계 카드 추가 (빨간색 강조)
- [ ] "조례 개정 상태" 섹션 및 테이블 추가
- [ ] 상태별 색상 태그 렌더링 (🔴 빨강 / 🟢 초록)
- [ ] React Query 훅 추가

### Step 7: 테스트 및 검증
- [ ] API 엔드포인트 테스트
- [ ] 대시보드 UI 확인
- [ ] 상태 자동 계산 로직 검증

---

## 📂 주요 파일 목록

### 백엔드
- `backend/schemas/dashboard.py` - 응답 스키마 정의
- `backend/services/dashboard_service.py` - 비즈니스 로직
- `backend/api/v1/dashboard.py` - API 엔드포인트
- `backend/models/ordinance.py` - Ordinance 모델 (참조용)
- `backend/models/law.py` - Law 모델 (참조용)
- `backend/models/ordinance_law_mapping.py` - 매핑 모델 (참조용)

### 프론트엔드
- `frontend/src/pages/Dashboard.tsx` - 메인 대시보드
- `frontend/src/types/api.ts` - TypeScript 타입 정의
- `frontend/src/services/api.ts` - API 함수

---

## ✅ 검증 방법

### 1. API 엔드포인트 테스트

```bash
# 1. 백엔드 서버 실행 확인
curl http://localhost:8000/api/v1/dashboard/summary

# 2. 새 엔드포인트 테스트 (전체 조회)
curl http://localhost:8000/api/v1/dashboard/revision-needed?limit=10

# 3. 상태별 필터링 테스트
curl "http://localhost:8000/api/v1/dashboard/revision-needed?status=NEEDS_REVISION&limit=10"
curl "http://localhost:8000/api/v1/dashboard/revision-needed?status=COMPLETED&limit=10"
```

### 2. SQL 쿼리 직접 검증

```bash
# Docker 컨테이너에서 SQL 실행
docker compose exec db psql -U lawmatcher -d lawmatcher

# 상태별 건수 확인
SELECT
    CASE
        WHEN o.revision_date < l.proclaimed_date THEN 'NEEDS_REVISION'
        ELSE 'COMPLETED'
    END as status,
    COUNT(DISTINCT o.id) as count
FROM ordinances o
INNER JOIN ordinance_law_mappings m ON o.id = m.ordinance_id
INNER JOIN laws l ON m.law_id = l.id
WHERE o.revision_date IS NOT NULL
  AND l.proclaimed_date IS NOT NULL
GROUP BY status;

# 상위 10건 상세 조회 (상태 포함)
SELECT
    CASE
        WHEN o.revision_date < l.proclaimed_date THEN '🔴 NEEDS_REVISION'
        ELSE '🟢 COMPLETED'
    END as status,
    o.name as 조례명,
    o.revision_date as 조례개정일,
    l.law_name as 상위법령,
    l.proclaimed_date as 법령공포일,
    (l.proclaimed_date - o.revision_date) as 날짜차이
FROM ordinances o
INNER JOIN ordinance_law_mappings m ON o.id = m.ordinance_id
INNER JOIN laws l ON m.law_id = l.id
WHERE o.revision_date IS NOT NULL
  AND l.proclaimed_date IS NOT NULL
ORDER BY
    CASE WHEN o.revision_date < l.proclaimed_date THEN 1 ELSE 2 END,
    ABS(l.proclaimed_date - o.revision_date) DESC
LIMIT 10;
```

### 3. 프론트엔드 UI 확인

1. http://localhost:3000 접속
2. 대시보드에서 확인:
   - ✅ 5번째 통계 카드 "개정 필요" 표시 (빨간색 강조)
   - ✅ "조례 개정 상태" 섹션 표시
   - ✅ 테이블에 상태 태그 (🔴 개정필요, 🟢 개정완료)
   - ✅ 상태별 정렬 (개정필요가 먼저)
   - ✅ 날짜 차이 표시
   - ✅ 조례명 클릭 시 상세 페이지 이동

---

## 🎨 UX/UI 개선 포인트

### 시각적 강조
- ✅ **상태별 색상 코딩 (자동 계산)**:
  - 🔴 NEEDS_REVISION (빨강) - 조례 개정 필요 (ordinance.revision_date < law.proclaimed_date)
  - 🟢 COMPLETED (초록) - 조례 개정 완료 (ordinance.revision_date >= law.proclaimed_date)
  - 🟡 UNDER_REVIEW (노랑) - 검토중 (향후 확장용, 현재 미사용)

### 정보 접근성
- ✅ **대시보드에서 즉시 확인**: 상위 10건을 대시보드에 바로 표시
- ✅ **자동 정렬**: 개정 필요 항목(빨강)이 먼저 표시
- ✅ **상태별 필터링**: NEEDS_REVISION / COMPLETED로 필터 가능

### 데이터 명확성
- ✅ **날짜 차이 표시**: "+120일" (법령이 최신), "-90일" (조례가 최신) 등
- ✅ **날짜 비교**: 조례 개정일과 법령 공포일을 나란히 표시
- ✅ **상위법령 정보**: 어떤 법령이 개정되었는지 명확히 표시
- ✅ **상태 명확성**: 태그를 통해 조례의 현재 상태를 한눈에 파악
