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


class OrdinanceArticleResponse(BaseModel):
    """Ordinance article response"""
    id: int
    article_no: str
    paragraph_no: Optional[str] = None
    item_no: Optional[str] = None
    content: str

    class Config:
        from_attributes = True


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
