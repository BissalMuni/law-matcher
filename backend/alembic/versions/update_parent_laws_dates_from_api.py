"""update parent_laws dates from lnkOrg API

Revision ID: update_parent_laws_dates
Revises: add_dates_to_parent_laws
Create Date: 2025-12-07

"""
from typing import Sequence, Union
import os
import httpx
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session


# revision identifiers, used by Alembic.
revision: str = 'update_parent_laws_dates'
down_revision: Union[str, None] = 'add_dates_to_parent_laws'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def fetch_lnk_org_data(api_key: str, sborg: str = "3220000") -> dict:
    """
    lnkOrg API에서 상위법령 연계 데이터를 가져옴

    Returns:
        {(ordinance_serial_no, law_id): {"proclaimed_date": date, "enforced_date": date}}
    """
    base_url = "http://www.law.go.kr/DRF/lawSearch.do"
    all_items = {}
    page = 1
    max_display = 100

    with httpx.Client(timeout=60.0) as client:
        while True:
            params = {
                "OC": api_key,
                "target": "lnkOrg",
                "org": sborg,
                "type": "JSON",
                "display": max_display,
                "page": page,
            }

            response = client.get(base_url, params=params)

            if response.text.strip().startswith('<!DOCTYPE'):
                break

            data = response.json()
            lnk_org_search = data.get("lnkOrgSearch", {})

            if not lnk_org_search:
                break

            items = lnk_org_search.get("law", [])
            if isinstance(items, dict):
                items = [items]

            if not items:
                break

            for item in items:
                serial_no = item.get("자치법규일련번호", "")
                law_id = item.get("법령ID", "")

                if serial_no and law_id:
                    proclaimed_date = None
                    enforced_date = None

                    if item.get("공포일자"):
                        try:
                            proclaimed_date = datetime.strptime(item["공포일자"], "%Y%m%d").date()
                        except ValueError:
                            pass

                    if item.get("시행일자"):
                        try:
                            enforced_date = datetime.strptime(item["시행일자"], "%Y%m%d").date()
                        except ValueError:
                            pass

                    all_items[(serial_no, law_id)] = {
                        "proclaimed_date": proclaimed_date,
                        "enforced_date": enforced_date,
                    }

            total_cnt = int(lnk_org_search.get("totalCnt", 0))
            if len(all_items) >= total_cnt:
                break

            page += 1

    return all_items


def upgrade() -> None:
    """기존 parent_laws 데이터에 lnkOrg API에서 가져온 날짜 정보 업데이트"""
    api_key = os.getenv("MOLEG_API_KEY", "test")
    sborg = os.getenv("MOLEG_SBORG", "3220000")  # 기본: 강남구

    # API에서 데이터 가져오기
    print(f"Fetching lnkOrg data for sborg={sborg}...")
    lnk_data = fetch_lnk_org_data(api_key, sborg)
    print(f"Fetched {len(lnk_data)} records from lnkOrg API")

    if not lnk_data:
        print("No data fetched from API. Skipping update.")
        return

    # DB 연결
    bind = op.get_bind()
    session = Session(bind=bind)

    # ordinances와 parent_laws 조인하여 업데이트
    # parent_laws.ordinance_id -> ordinances.id -> ordinances.serial_no
    result = session.execute(sa.text("""
        SELECT pl.id, pl.law_id, o.serial_no
        FROM parent_laws pl
        JOIN ordinances o ON pl.ordinance_id = o.id
        WHERE pl.proclaimed_date IS NULL OR pl.enforced_date IS NULL
    """))

    updated_count = 0
    for row in result:
        parent_law_id = row[0]
        law_id = row[1]
        serial_no = row[2]

        if not serial_no:
            continue

        key = (serial_no, law_id)
        if key in lnk_data:
            dates = lnk_data[key]

            # 업데이트 쿼리
            update_parts = []
            params = {"id": parent_law_id}

            if dates["proclaimed_date"]:
                update_parts.append("proclaimed_date = :proclaimed_date")
                params["proclaimed_date"] = dates["proclaimed_date"]

            if dates["enforced_date"]:
                update_parts.append("enforced_date = :enforced_date")
                params["enforced_date"] = dates["enforced_date"]

            if update_parts:
                session.execute(
                    sa.text(f"UPDATE parent_laws SET {', '.join(update_parts)} WHERE id = :id"),
                    params
                )
                updated_count += 1

    session.commit()
    print(f"Updated {updated_count} parent_laws records with date information")


def downgrade() -> None:
    """날짜 정보 초기화 (NULL로)"""
    bind = op.get_bind()
    session = Session(bind=bind)

    session.execute(sa.text("""
        UPDATE parent_laws
        SET proclaimed_date = NULL, enforced_date = NULL
    """))

    session.commit()
