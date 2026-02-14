"""
법령 데이터 업데이트 및 조문 동기화 스크립트
"""
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from backend.models.law import Law
from backend.services.article_service import ArticleService
from backend.external.moleg_client import MolegClient
from backend.core.config import settings


async def update_and_sync():
    """법령 업데이트 및 조문 동기화"""
    # 데이터베이스 연결
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as db:
        # MolegClient 생성
        moleg_client = MolegClient(api_key=settings.MOLEG_API_KEY)

        # 업데이트할 법령 목록 (검색어)
        law_queries = [
            "국민건강증진법",
            "지방자치법",
            "지방공무원법",
        ]

        print(f"\n📊 {len(law_queries)}개 법령을 검색하고 업데이트합니다.\n")

        updated_laws = []

        for query in law_queries:
            print(f"🔍 '{query}' 검색 중...")

            try:
                # 법제처 API에서 검색
                import httpx
                async with httpx.AsyncClient(timeout=30.0) as http_client:
                    params = {
                        "OC": settings.MOLEG_API_KEY,
                        "target": "law",
                        "query": query,
                        "type": "JSON",
                    }

                    response = await http_client.get(
                        "https://www.law.go.kr/DRF/lawSearch.do",
                        params=params,
                    )
                    response.raise_for_status()
                    data = response.json()

                    laws_data = data.get("LawSearch", {}).get("law", [])
                    if not laws_data:
                        print(f"   ❌ 검색 결과 없음\n")
                        continue

                    # 첫 번째 결과만 사용 (가장 관련성 높은 법령)
                    law_info = laws_data[0]

                    law_name = law_info.get("법령명한글", "")
                    law_serial_no = int(law_info.get("법령일련번호", 0))
                    law_id_str = law_info.get("법령ID", "")

                    # 숫자로 변환 (앞에 0이 있을 수 있음)
                    try:
                        law_id_int = int(law_id_str)
                    except:
                        law_id_int = 0

                    print(f"   ✅ 찾음: {law_name}")
                    print(f"      - 법령ID: {law_id_str}")
                    print(f"      - 법령일련번호: {law_serial_no}")

                    # DB에서 동일한 법령 찾기 (이름으로 검색)
                    result = await db.execute(
                        select(Law).where(Law.law_name == law_name)
                    )
                    existing_law = result.scalars().first()

                    if existing_law:
                        # 업데이트
                        print(f"      - DB 업데이트 (ID: {existing_law.id})")
                        existing_law.law_serial_no = law_serial_no
                        existing_law.law_id = law_id_int
                        existing_law.law_type = law_info.get("법령종류코드명", existing_law.law_type)
                        existing_law.updated_at = datetime.utcnow()
                        updated_laws.append(existing_law)
                    else:
                        # 새로 생성
                        print(f"      - DB 새로 생성")
                        new_law = Law(
                            law_serial_no=law_serial_no,
                            law_id=law_id_int,
                            law_name=law_name,
                            law_type=law_info.get("법령종류코드명", "법률"),
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        db.add(new_law)
                        await db.flush()  # ID 생성
                        updated_laws.append(new_law)

                    await db.commit()
                    print()

            except Exception as e:
                import traceback
                print(f"   ❌ 오류: {str(e)}")
                traceback.print_exc()
                print()
                continue

        print(f"\n✅ {len(updated_laws)}개 법령 업데이트 완료!\n")
        print("=" * 60)
        print("\n📥 조문 동기화 시작...\n")

        # ArticleService 생성
        service = ArticleService(db=db, moleg_client=moleg_client)

        # 각 법령의 조문 동기화
        total_synced = 0
        total_created = 0
        total_updated = 0

        for i, law in enumerate(updated_laws, 1):
            print(f"[{i}/{len(updated_laws)}] {law.law_name} (ID: {law.id}) 동기화 중...")

            try:
                result = await service.sync_articles_for_law(
                    law_id=law.id,
                    force=True,
                )

                print(f"  ✅ 성공: {result['synced_articles']}개 조문 동기화")
                print(f"     - 신규: {result['created']}개")
                print(f"     - 수정: {result['updated']}개")
                print(f"     - 삭제: {result['deleted']}개\n")

                total_synced += result["synced_articles"]
                total_created += result["created"]
                total_updated += result["updated"]

            except Exception as e:
                import traceback
                print(f"  ❌ 실패: {str(e)}")
                traceback.print_exc()
                print()
                continue

        print(f"\n🎉 동기화 완료!")
        print(f"   - 총 조문: {total_synced}개")
        print(f"   - 신규: {total_created}개")
        print(f"   - 수정: {total_updated}개")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(update_and_sync())
