"""
Ordinance schemas
"""
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel


class OrdinanceBase(BaseModel):
    """Ordinance base schema"""
    code: str
    name: str
    category: Optional[str] = None
    department: Optional[str] = None


class OrdinanceResponse(OrdinanceBase):
    """Ordinance response"""
    id: int
    enacted_date: Optional[date] = None
    enforced_date: Optional[date] = None
    revision_date: Optional[date] = None
    status: str
    serial_no: Optional[str] = None
    field_name: Optional[str] = None
    org_name: Optional[str] = None
    promulgation_no: Optional[str] = None
    revision_type: Optional[str] = None
    detail_link: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    parent_law_count: Optional[int] = None  # 상위법령 연결 개수
    no_parent_law: bool = False  # 상위법령 없음 확인 여부
    needs_revision: Optional[int] = None  # 개정여부 (1: 법령이 더 최신, 0: 조례가 더 최신)
    law_revision_types: Optional[List[str]] = None  # 상위법령 제개정구분 목록

    class Config:
        from_attributes = True


class OrdinanceSyncRequest(BaseModel):
    """법제처 API 동기화 요청"""
    org: str = "6110000"  # 서울특별시
    sborg: str = "3220000"  # 강남구


class OrdinanceSyncResponse(BaseModel):
    """법제처 API 동기화 응답"""
    success: bool
    total_fetched: int
    created: int
    updated: int
    message: str


class OrdinanceUploadResponse(BaseModel):
    """엑셀 업로드 응답"""
    success: bool
    total_rows: int
    updated: int
    not_found: int
    message: str


class OrdinanceListResponse(BaseModel):
    """Ordinance list response"""
    total: int
    page: int
    size: int
    items: List[OrdinanceResponse]



class LawResponse(BaseModel):
    """상위법령 마스터 응답 (API 기반)"""
    id: int
    law_serial_no: int  # 법령일련번호
    law_id: int  # 법령ID
    law_name: str  # 법령명한글
    law_abbr: Optional[str] = None  # 법령약칭명
    law_type: str  # 법령구분명 (법률/대통령령/총리령/부령)
    proclaimed_date: Optional[date] = None  # 공포일자
    proclaimed_no: Optional[int] = None  # 공포번호
    enforced_date: Optional[date] = None  # 시행일자
    revision_type: Optional[str] = None  # 제개정구분명
    dept_name: Optional[str] = None  # 소관부처명
    detail_link: Optional[str] = None  # 법령상세링크
    last_synced_at: Optional[datetime] = None
    ordinance_count: Optional[int] = None  # 연계 자치법규 개수

    class Config:
        from_attributes = True


class LawBriefResponse(BaseModel):
    """상위법령 간략 응답"""
    id: int
    law_name: str
    law_type: str
    proclaimed_date: Optional[date] = None
    enforced_date: Optional[date] = None

    class Config:
        from_attributes = True


class OrdinanceLawMappingResponse(BaseModel):
    """조례-법령 연계 응답"""
    id: int
    ordinance_id: int
    law_id: int
    related_articles: Optional[str] = None
    law: LawBriefResponse  # 법령 정보 포함

    class Config:
        from_attributes = True


class OrdinanceLawMappingCreate(BaseModel):
    """조례-법령 연계 생성"""
    law_id: int  # laws 테이블의 id
    related_articles: Optional[str] = None


class OrdinanceLawMappingUpdate(BaseModel):
    """조례-법령 연계 수정"""
    law_name: Optional[str] = None
    law_type: Optional[str] = None
    proclaimed_date: Optional[str] = None
    enforced_date: Optional[str] = None
    related_articles: Optional[str] = None


class ParentLawCreate(BaseModel):
    """상위법령 추가 (프론트엔드용)"""
    law_id: Optional[str] = None
    law_name: str
    law_type: str
    proclaimed_date: Optional[str] = None
    enforced_date: Optional[str] = None
    related_articles: Optional[str] = None


class LawSyncRequest(BaseModel):
    """법령 동기화 요청"""
    law_names: Optional[List[str]] = None  # 특정 법령명 목록 (없으면 전체)
    days: int = 30  # 최근 N일 공포분
    sborg: str = "3220000"  # 지자체 코드


class LawSyncResponse(BaseModel):
    """법령 동기화 응답"""
    success: bool
    synced_laws: int
    synced_mappings: int
    message: str


class AmendmentCheckRequest(BaseModel):
    """개정 감지 요청"""
    days: int = 30  # 최근 N일 공포분 검사


class AmendmentCheckResponse(BaseModel):
    """개정 감지 결과 응답"""
    law_name: str
    old_proclaimed_date: Optional[date] = None
    new_proclaimed_date: Optional[date] = None
    revision_type: Optional[str] = None
    affected_ordinance_count: int
    affected_ordinances: List[str]  # 조례명 목록



class LawSearchRequest(BaseModel):
    """법령명 검색 요청"""
    law_name: str


class LawSearchResponse(BaseModel):
    """법령명 검색 결과"""
    success: bool
    law_id: Optional[str] = None  # 법령ID (문자열)
    law_serial_no: Optional[str] = None  # 법령일련번호
    law_name: Optional[str] = None  # 정확한 법령명
    law_type: Optional[str] = None  # 법령구분명
    message: str


class OrdinanceCreate(BaseModel):
    """자치법규 수동 등록 요청"""
    name: str  # 자치법규명 (필수)
    category: str = "조례"  # 자치법규종류 (조례/규칙)
    department: Optional[str] = None  # 소관부서
    enacted_date: Optional[str] = None  # 공포일자 (YYYY-MM-DD)
    enforced_date: Optional[str] = None  # 시행일자 (YYYY-MM-DD)


class OrdinanceCreateResponse(BaseModel):
    """자치법규 등록 응답"""
    success: bool
    id: Optional[int] = None
    message: str


class LawInfoUpdateRequest(BaseModel):
    """상위법령 정보 일괄 업데이트 요청"""
    pass  # 파라미터 없음 - 모든 법령 업데이트


class LawInfoUpdateResponse(BaseModel):
    """상위법령 정보 업데이트 응답"""
    success: bool
    total_laws: int
    updated: int
    failed: int
    message: str


class OrdinanceSearchRequest(BaseModel):
    """자치법규 검색 요청 (법제처 API)"""
    query: str  # 검색어
    org: str = "6110000"  # 도/특별시/광역시 코드
    sborg: str = "3220000"  # 시/군/구 코드


class OrdinanceSearchResult(BaseModel):
    """자치법규 검색 결과 항목"""
    serial_no: str  # 자치법규일련번호
    name: str  # 자치법규명
    ordinance_id: str  # 자치법규ID
    enacted_date: Optional[str] = None  # 공포일자
    promulgation_no: Optional[str] = None  # 공포번호
    revision_type: Optional[str] = None  # 제개정구분명
    org_name: Optional[str] = None  # 지자체기관명
    category: Optional[str] = None  # 자치법규종류
    enforced_date: Optional[str] = None  # 시행일자
    detail_link: Optional[str] = None  # 자치법규상세링크
    field_name: Optional[str] = None  # 자치법규분야명


class OrdinanceSearchResponse(BaseModel):
    """자치법규 검색 응답"""
    success: bool
    total: int
    items: List[OrdinanceSearchResult]
    message: str


class OrdinanceRegisterFromApiRequest(BaseModel):
    """법제처 API 검색 결과로 자치법규 등록"""
    serial_no: str  # 자치법규일련번호
    name: str  # 자치법규명
    ordinance_id: str  # 자치법규ID
    enacted_date: Optional[str] = None
    promulgation_no: Optional[str] = None
    revision_type: Optional[str] = None
    org_name: Optional[str] = None
    category: Optional[str] = None
    enforced_date: Optional[str] = None
    detail_link: Optional[str] = None
    field_name: Optional[str] = None
    department: Optional[str] = None  # 소관부서 (수동 입력)


class OrdinanceInfoUpdateResponse(BaseModel):
    """자치법규 정보 일괄 업데이트 응답"""
    success: bool
    total_ordinances: int
    updated: int
    failed: int
    message: str


# ==================== LawChange 스키마 ====================

class LawChangeResponse(BaseModel):
    """법령 변경 이력 응답"""
    id: int
    law_id: int
    law_name: str  # law 테이블에서 조인
    law_type: Optional[str] = None
    sync_date: datetime
    sync_batch_id: Optional[str] = None
    api_status: str  # success, no_response, not_found
    api_message: Optional[str] = None
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    dept_name: Optional[str] = None
    dept_code: Optional[int] = None
    status: str  # pending, reviewing, approved, rejected
    processed_at: Optional[datetime] = None
    processed_by: Optional[str] = None
    process_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LawChangeListResponse(BaseModel):
    """법령 변경 이력 목록 응답"""
    total: int
    page: int
    size: int
    items: List[LawChangeResponse]


class LawChangeApproveRequest(BaseModel):
    """법령 변경 승인 요청"""
    process_note: Optional[str] = None  # 처리 메모
    processed_by: Optional[str] = None  # 처리자


class LawChangeRejectRequest(BaseModel):
    """법령 변경 반려 요청"""
    process_note: str  # 반려 사유 (필수)
    processed_by: Optional[str] = None  # 처리자


class LawChangeBulkApproveRequest(BaseModel):
    """법령 변경 일괄 승인 요청"""
    ids: List[int]  # 승인할 변경 ID 목록
    process_note: Optional[str] = None
    processed_by: Optional[str] = None


class LawChangeBulkRejectRequest(BaseModel):
    """법령 변경 일괄 반려 요청"""
    ids: List[int]  # 반려할 변경 ID 목록
    process_note: str  # 반려 사유 (필수)
    processed_by: Optional[str] = None


class LawChangeStatsResponse(BaseModel):
    """법령 변경 통계 응답"""
    total: int
    pending: int
    reviewing: int
    approved: int
    rejected: int
    by_dept: List[dict]  # 부서별 통계


class LawChangeSyncStatsResponse(BaseModel):
    """동기화별 통계 응답"""
    sync_batch_id: str
    sync_date: datetime
    total: int
    success: int
    no_response: int
    not_found: int
    pending: int
    approved: int


# ==================== OrdinanceReview 스키마 ====================

class OrdinanceReviewBase(BaseModel):
    """자치법규 검토이력 기본"""
    reviewer_type: str  # "DEPARTMENT" (부서담당자) | "GENERAL" (구청총괄)
    reviewer_name: Optional[str] = None
    reviewer_department: Optional[str] = None
    review_content: str
    review_result: Optional[str] = None  # 개정필요/개정불필요/검토중/보류


class OrdinanceReviewCreate(OrdinanceReviewBase):
    """자치법규 검토이력 생성"""
    pass


class OrdinanceReviewUpdate(BaseModel):
    """자치법규 검토이력 수정"""
    reviewer_name: Optional[str] = None
    reviewer_department: Optional[str] = None
    review_content: Optional[str] = None
    review_result: Optional[str] = None


class OrdinanceReviewResponse(OrdinanceReviewBase):
    """자치법규 검토이력 응답"""
    id: int
    ordinance_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrdinanceReviewListResponse(BaseModel):
    """자치법규 검토이력 목록 응답"""
    total: int
    items: List[OrdinanceReviewResponse]
