## Law-Matcher 조례 개정 필요 판단 로직 개선 구현 계획
# 개요
목표: 단순 날짜 비교에서 관련 조문 기반 필터링으로 전환하여 False Positive 50-70% 감소

문제: 현재 조례.revision_date < 법령.proclaimed_date 비교만으로 판단하여, 법령의 무관한 조항만 개정된 경우에도 "개정 필요"로 잘못 표시됨

해결:

OrdinanceLawMapping.related_articles (관련 조문) 활용
Law.revision_type (전부개정/일부개정) 가중치 적용
긴급도(revision_urgency) 자동 계산
# Critical Files
신규 생성 (P0)
backend/services/amendment_analysis_service.py - 핵심 분석 로직
backend/tests/test_amendment_analysis_service.py - 단위 테스트
수정 (P0)
backend/services/dashboard_service.py (라인 149-251) - get_revision_needed()
backend/schemas/dashboard.py (라인 49-64) - RevisionNeededItem
수정 (P1)
backend/services/amendment_service.py (라인 61-75) - analyze_impact()
backend/schemas/amendment.py (라인 38-44) - ImpactAnalysisResponse
# 구현 단계
Step 1: AmendmentAnalysisService 생성 (P0, 2-3시간)
파일: backend/services/amendment_analysis_service.py

핵심 메서드
1. parse_article_numbers(article_str) → Set[str]

def parse_article_numbers(self, article_str: str) -> Set[str]:
    """
    "제3조, 제5조, 제10조~제15조" → {"3", "5", "10", "11", ..., "15"}

    로직:
    - 정규식으로 "제(\d+)조" 패턴 추출
    - "제10조~제15조" 범위 처리
    """
    if not article_str:
        return set()

    articles = set()
    parts = re.split(r'[,\s]+', article_str.strip())

    for part in parts:
        # 범위: "제10조~제15조"
        range_match = re.search(r'제(\d+)조\s*[~\-]\s*제?(\d+)조?', part)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            articles.update(str(i) for i in range(start, end + 1))
            continue

        # 단일: "제3조"
        single_match = re.search(r'제(\d+)조', part)
        if single_match:
            articles.add(single_match.group(1))

    return articles
2. extract_amended_articles(law) → Set[str]

async def extract_amended_articles(self, law: Law) -> Set[str]:
    """
    법령 개정 조항 추출 (현재 제약사항: LawSnapshot 미활용)

    휴리스틱:
    - 전부개정 → {"ALL"}
    - 일부개정 → {} (향후 LawChange 활용)
    """
    if law.revision_type == "전부개정":
        return {"ALL"}
    return set()
3. should_ordinance_be_revised(ordinance, law, mapping) → (bool, str, str)

async def should_ordinance_be_revised(
    self, ordinance, law, mapping
) -> Tuple[bool, str, str]:
    """
    조례 개정 필요성 판단

    Returns: (should_revise, reason, urgency)

    로직:
    1. 날짜 선행 확인: ordinance.revision_date >= law.proclaimed_date → (False, ...)
    2. 전부개정 → (True, "전부개정", "HIGH")
    3. 폐지 → (True, "폐지", "HIGH")
    4. 제정 → (False, "신규 제정", "LOW")
    5. 일부개정:
       a. related_articles 없음 → (True, "확인 필요", "MEDIUM")
       b. 개정 조항과 교집합 있음 → (True, "관련 조문 개정", "MEDIUM")
       c. 교집합 없음 → (False, "무관한 조항", "LOW")
    """
    # 1. 날짜 선행
    if ordinance.revision_date and law.proclaimed_date:
        if ordinance.revision_date >= law.proclaimed_date:
            return (False, "이미 개정됨", "LOW")

    # 2. 폐지
    if law.revision_type == "폐지":
        return (True, "상위법령 폐지", "HIGH")

    # 3. 전부개정
    if law.revision_type == "전부개정":
        return (True, "상위법령 전부개정", "HIGH")

    # 4. 제정
    if law.revision_type == "제정":
        return (False, "신규 제정", "LOW")

    # 5. 일부개정
    if law.revision_type == "일부개정":
        if not mapping.related_articles:
            return (True, "관련 조문 정보 없음", "MEDIUM")

        ordinance_articles = self.parse_article_numbers(mapping.related_articles)
        amended_articles = await self.extract_amended_articles(law)

        if "ALL" in amended_articles:
            return (True, "전부개정", "HIGH")

        if not amended_articles:
            return (True, "일부개정 (개정 조문 미상)", "MEDIUM")

        intersection = ordinance_articles & amended_articles
        if intersection:
            affected = ", ".join(sorted(intersection, key=int))
            return (True, f"관련 조문 개정 (제{affected}조)", "MEDIUM")
        else:
            return (False, "무관한 조항", "LOW")

    return (True, f"알 수 없는 유형: {law.revision_type}", "MEDIUM")
4. calculate_revision_urgency(law, days_since_proclaimed) → str

def calculate_revision_urgency(self, law, days_since_proclaimed) -> str:
    """
    경과 기간 기반 긴급도 재계산

    - 전부개정 + 30일 이내 → HIGH
    - 전부개정 + 31-90일 → MEDIUM
    - 일부개정 + 90일 이내 → MEDIUM
    - 기타 → LOW
    """
    if law.revision_type == "전부개정":
        if days_since_proclaimed <= 30:
            return "HIGH"
        elif days_since_proclaimed <= 90:
            return "MEDIUM"

    if law.revision_type == "폐지":
        return "HIGH" if days_since_proclaimed <= 60 else "MEDIUM"

    if law.revision_type == "일부개정":
        return "MEDIUM" if days_since_proclaimed <= 90 else "LOW"

    return "LOW"
5. generate_revision_reason(law, ordinance, mapping, should_revise, base_reason) → str

def generate_revision_reason(self, law, ordinance, mapping, should_revise, base_reason) -> str:
    """
    사람이 읽기 쉬운 판단 이유 생성

    예: "「도로교통법」이(가) 2024-01-15에 전부개정되었습니다. 조례가 참조하는 조문: 제3조, 제5조 상위법령 전부개정 → 조례 개정 검토가 필요합니다."
    """
    law_name = law.law_name
    proclaimed_date = law.proclaimed_date.strftime('%Y-%m-%d') if law.proclaimed_date else '알 수 없는 날짜'

    parts = [
        f"「{law_name}」이(가) {proclaimed_date}에 {law.revision_type or '개정'}되었습니다."
    ]

    if mapping.related_articles:
        parts.append(f"조례가 참조하는 조문: {mapping.related_articles}")

    parts.append(base_reason)
    parts.append("→ 조례 개정 검토가 필요합니다." if should_revise else "→ 조례 개정이 필요하지 않습니다.")

    return " ".join(parts)
테스트 케이스:


# test_amendment_analysis_service.py

def test_parse_single_articles():
    service = AmendmentAnalysisService(None)
    assert service.parse_article_numbers("제3조, 제5조") == {"3", "5"}

def test_parse_range():
    service = AmendmentAnalysisService(None)
    assert service.parse_article_numbers("제10조~제15조") == {"10", "11", "12", "13", "14", "15"}

def test_parse_mixed():
    service = AmendmentAnalysisService(None)
    result = service.parse_article_numbers("제3조, 제5조, 제10조~제12조")
    assert result == {"3", "5", "10", "11", "12"}
Step 2: DashboardService 수정 (P0, 2-3시간)
파일: backend/services/dashboard_service.py

수정 위치: get_revision_needed() 메서드 (라인 149-251)

변경 전략:

기존 쿼리 로직 유지 (성능)
결과를 AmendmentAnalysisService로 후처리
should_ordinance_be_revised() 결과로 필터링
핵심 코드:


async def get_revision_needed(
    self,
    limit: int = 10,
    status: Optional[str] = None,
    department: Optional[str] = None
) -> dict:
    """Get revision-needed items (개선: 관련 조문 필터링)"""
    from backend.services.amendment_analysis_service import AmendmentAnalysisService
    from sqlalchemy import and_

    # 기존 쿼리 (라인 156-205) - 유지
    # ...
    result = await self.db.execute(query)
    rows = result.all()

    # === 새로운 필터링 로직 ===
    analysis_service = AmendmentAnalysisService(self.db)
    filtered_items = []

    for row in rows:
        # Ordinance, Law 객체 조회
        ordinance = await self.db.get(Ordinance, row.ordinance_id)
        law = await self.db.get(Law, row.law_id)

        # Mapping 조회
        mapping_result = await self.db.execute(
            select(OrdinanceLawMapping).where(
                and_(
                    OrdinanceLawMapping.ordinance_id == row.ordinance_id,
                    OrdinanceLawMapping.law_id == row.law_id
                )
            )
        )
        mapping = mapping_result.scalar_one_or_none()
        if not mapping:
            continue

        # 개정 필요성 판단
        should_revise, reason, urgency = await analysis_service.should_ordinance_be_revised(
            ordinance, law, mapping
        )

        # 필터링: status가 NEEDS_REVISION인데 실제로는 불필요한 경우 제외
        if status == "NEEDS_REVISION" and not should_revise:
            continue

        # 경과 일수 기반 긴급도 재계산
        if law.proclaimed_date:
            days_diff = (datetime.utcnow().date() - law.proclaimed_date).days
            urgency = analysis_service.calculate_revision_urgency(law, days_diff)

        # 상세 사유 생성
        detailed_reason = analysis_service.generate_revision_reason(
            law, ordinance, mapping, should_revise, reason
        )

        filtered_items.append({
            "ordinance_id": row.ordinance_id,
            "ordinance_name": row.ordinance_name,
            "ordinance_revision_date": row.ordinance_revision_date,
            "law_id": row.law_id,
            "law_name": row.law_name,
            "law_type": row.law_type,
            "law_proclaimed_date": row.law_proclaimed_date,
            "days_diff": row.days_diff,
            "revision_status": "NEEDS_REVISION" if should_revise else "COMPLETED",
            "revision_urgency": urgency,  # 새 필드
            "revision_reason": detailed_reason,  # 새 필드
            "department": row.department,
        })

    filtered_items = filtered_items[:limit]

    needs_revision_count = sum(1 for item in filtered_items if item["revision_status"] == "NEEDS_REVISION")
    completed_count = len(filtered_items) - needs_revision_count

    return {
        "total": len(filtered_items),
        "needs_revision_count": needs_revision_count,
        "completed_count": completed_count,
        "items": filtered_items,
    }
성능 고려:

N+1 문제 발생 가능 (각 row마다 DB 조회)
해결: eager loading (selectinload) 적용 권장
현재는 단순 구현 우선, 향후 최적화
Step 3: 스키마 수정 (P1, 1시간)
1. dashboard.py
파일: backend/schemas/dashboard.py

수정 위치: RevisionNeededItem 클래스 (라인 49-64)

추가 필드:


class RevisionNeededItem(BaseModel):
    """Revision needed item"""
    ordinance_id: int
    ordinance_name: str
    ordinance_revision_date: Optional[date]
    law_id: int
    law_name: str
    law_type: str
    law_proclaimed_date: Optional[date]
    days_diff: int
    revision_status: str
    department: Optional[str]

    # 새 필드
    revision_urgency: Optional[str] = None  # HIGH/MEDIUM/LOW
    revision_reason: Optional[str] = None   # 판단 이유

    class Config:
        from_attributes = True
2. amendment.py
파일: backend/schemas/amendment.py

수정 위치: ImpactAnalysisResponse 클래스 (라인 38-44)

추가 스키마:


class OrdinanceImpactDetail(BaseModel):
    """개별 조례 영향도 상세"""
    ordinance_id: int
    ordinance_name: str
    should_revise: bool
    urgency: str
    reason: str


class ImpactAnalysisResponse(BaseModel):
    """Impact analysis response"""
    amendment_id: int
    affected_ordinances: int
    need_revision_count: int
    reviews_created: int
    details: List[OrdinanceImpactDetail] = []  # 새 필드
Step 4: AmendmentService 수정 (P1, 2시간)
파일: backend/services/amendment_service.py

수정 위치: analyze_impact() 메서드 (라인 61-75)

현재 상태: TODO 주석만 있음

구현 로직:


async def analyze_impact(self, amendment_id: int) -> dict:
    """
    Run impact analysis for amendment

    1. Get ordinances linked to this law
    2. Analyze revision necessity
    3. Create AmendmentReview records
    """
    from backend.services.amendment_analysis_service import AmendmentAnalysisService

    # 1. Get amendment & law
    amendment = await self.get_by_id(amendment_id)
    if not amendment.source_law_id:
        return {"amendment_id": amendment_id, "error": "source_law_id 없음"}

    law = await self.db.get(Law, amendment.source_law_id)
    if not law:
        return {"amendment_id": amendment_id, "error": "법령 없음"}

    # 2. Get all ordinances linked to this law
    mappings_result = await self.db.execute(
        select(OrdinanceLawMapping).where(OrdinanceLawMapping.law_id == law.id)
    )
    mappings = mappings_result.scalars().all()

    # 3. Analyze each ordinance
    analysis_service = AmendmentAnalysisService(self.db)
    affected_ordinances = []
    need_revision_count = 0
    reviews_created = 0

    for mapping in mappings:
        ordinance = await self.db.get(Ordinance, mapping.ordinance_id)
        if not ordinance:
            continue

        # Analyze
        should_revise, reason, urgency = await analysis_service.should_ordinance_be_revised(
            ordinance, law, mapping
        )

        if should_revise:
            need_revision_count += 1

        affected_ordinances.append({
            "ordinance_id": ordinance.id,
            "ordinance_name": ordinance.name,
            "should_revise": should_revise,
            "urgency": urgency,
            "reason": reason,
        })

        # 4. Create or update AmendmentReview
        existing = await self.db.execute(
            select(AmendmentReview).where(
                AmendmentReview.amendment_id == amendment_id,
                AmendmentReview.ordinance_id == ordinance.id
            )
        )
        review = existing.scalar_one_or_none()

        if review:
            review.need_revision = should_revise
            review.revision_urgency = urgency
            review.reason = analysis_service.generate_revision_reason(
                law, ordinance, mapping, should_revise, reason
            )
        else:
            review = AmendmentReview(
                amendment_id=amendment_id,
                ordinance_id=ordinance.id,
                need_revision=should_revise,
                revision_urgency=urgency,
                reason=analysis_service.generate_revision_reason(
                    law, ordinance, mapping, should_revise, reason
                ),
                status="PENDING"
            )
            self.db.add(review)
            reviews_created += 1

    await self.db.commit()

    # 5. Mark amendment as processed
    amendment.processed = True
    await self.db.commit()

    return {
        "amendment_id": amendment_id,
        "affected_ordinances": len(affected_ordinances),
        "need_revision_count": need_revision_count,
        "reviews_created": reviews_created,
        "details": affected_ordinances,
    }
검증 방법
1. 단위 테스트 실행

# AmendmentAnalysisService 테스트
pytest backend/tests/test_amendment_analysis_service.py -v

# 예상 결과: 10+ 테스트 PASS
2. API 테스트
대시보드 - 개정 필요 목록

curl http://localhost:8000/api/v1/dashboard/revision-needed?status=NEEDS_REVISION&limit=10 | python3 -m json.tool

# 예상 응답
{
  "total": 15,
  "needs_revision_count": 8,
  "completed_count": 7,
  "items": [
    {
      "ordinance_id": 1,
      "ordinance_name": "강남구 도로교통 조례",
      "law_name": "도로교통법",
      "revision_status": "NEEDS_REVISION",
      "revision_urgency": "HIGH",
      "revision_reason": "「도로교통법」이(가) 2024-01-15에 전부개정되었습니다. ..."
    }
  ]
}
개정 영향도 분석

curl -X POST http://localhost:8000/api/v1/amendments/123/analyze | python3 -m json.tool

# 예상 응답
{
  "amendment_id": 123,
  "affected_ordinances": 8,
  "need_revision_count": 5,
  "reviews_created": 5,
  "details": [
    {
      "ordinance_id": 1,
      "ordinance_name": "강남구 도로교통 조례",
      "should_revise": true,
      "urgency": "HIGH",
      "reason": "상위법령 전부개정"
    }
  ]
}
3. 데이터베이스 확인
False Positive 감소 확인

-- 기존 로직으로 개정 필요로 판단된 조례 수
SELECT COUNT(DISTINCT o.id)
FROM ordinances o
JOIN ordinance_law_mappings olm ON o.id = olm.ordinance_id
JOIN laws l ON olm.law_id = l.id
WHERE o.revision_date < l.proclaimed_date;
-- 예상: 100건

-- 새 로직으로 실제 개정 필요한 조례 수
SELECT COUNT(*)
FROM amendment_reviews
WHERE need_revision = true AND status = 'PENDING';
-- 예상: 60건

-- 감소율: 40%
AmendmentReview 생성 확인

SELECT
    ar.id,
    o.name AS ordinance_name,
    ar.need_revision,
    ar.revision_urgency,
    ar.reason
FROM amendment_reviews ar
JOIN ordinances o ON ar.ordinance_id = o.id
WHERE ar.amendment_id = 123
ORDER BY ar.revision_urgency DESC;
4. 프론트엔드 확인
브라우저에서 http://localhost:3000/dashboard 접속:

Revision Status Table에 새 필드(revision_urgency, revision_reason) 표시
필터링으로 False Positive 감소 확인
# 예상 효과
False Positive 감소
기존: 100개 중 60개 "개정 필요" → 실제 필요: 35개 (False Positive: 25개, 42%)
개선 후: 100개 중 35개만 "개정 필요" → False Positive 감소율: 40-50%
성능
기존: 100ms (단순 날짜 비교)
개선 후: 200-300ms (분석 로직 추가)
허용 범위 내 (향후 eager loading으로 최적화 가능)
사용자 경험
담당자가 검토할 항목 40% 감소 → 업무 효율성 향상
긴급도 표시로 우선순위 명확화
판단 이유 표시로 검토 시간 단축
# 향후 개선 방향
단기 (1-2개월)
LawChange 활용: new_values에서 개정 조문 추출
eager loading: N+1 문제 해결
사용자 피드백: "정확함/부정확함" 버튼 추가
중기 (3-6개월)
LawSnapshot 활용: 개정 전후 diff 분석
배치 처리: Celery로 백그라운드 분석
캐싱: Redis로 분석 결과 캐싱
장기 (6개월+)
LLM 통합: Claude/GPT로 의미론적 분석
ML 모델: 사용자 피드백 기반 학습
자동 개정안 생성: LLM으로 조례 개정안 초안 작성
# 구현 체크리스트
[ ] Step 1: AmendmentAnalysisService 생성 (2-3h)

[ ] parse_article_numbers() 구현
[ ] extract_amended_articles() 구현
[ ] should_ordinance_be_revised() 구현
[ ] calculate_revision_urgency() 구현
[ ] generate_revision_reason() 구현
[ ] 단위 테스트 작성 (10+ 케이스)
[ ] Step 2: DashboardService 수정 (2-3h)

[ ] get_revision_needed() 분석 로직 통합
[ ] 필터링 구현
[ ] 새 필드 추가
[ ] Step 3: 스키마 수정 (1h)

[ ] dashboard.py - RevisionNeededItem 수정
[ ] amendment.py - ImpactAnalysisResponse 수정
[ ] Step 4: AmendmentService 수정 (2h)

[ ] analyze_impact() 구현
[ ] AmendmentReview 자동 생성
[ ] Step 5: 검증 (2-3h)

[ ] 단위 테스트 실행
[ ] API 테스트
[ ] DB 확인
[ ] False Positive 감소율 측정
총 예상 시간: 9-12시간 (1.5-2일)