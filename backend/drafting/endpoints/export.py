"""POST /drafting/export — 완성 조례를 DOCX/PDF 바이트로 내보낸다 (온디맨드)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel

from backend.drafting.renderer import ExportSection, render_docx, render_pdf

router = APIRouter()


class ExportSectionInput(BaseModel):
    article_label: str
    title: str
    body: str
    order: int


class ExportRequest(BaseModel):
    project_title: str
    municipality: str
    sections: list[ExportSectionInput]
    format: Literal["docx", "pdf"]


_MEDIA = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


@router.post("/export")
def export_endpoint(body: ExportRequest) -> Response:
    sections = [
        ExportSection(s.article_label, s.title, s.body, s.order) for s in body.sections
    ]
    if body.format == "docx":
        data = render_docx(body.project_title, body.municipality, sections)
    else:
        data = render_pdf(body.project_title, body.municipality, sections)
    return Response(content=data, media_type=_MEDIA[body.format])
