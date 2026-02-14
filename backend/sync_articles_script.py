"""
조문 동기화 스크립트 - 법제처 API에서 조문 데이터 가져오기
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from backend.models.law import Law
from backend.services.article_service import ArticleService
from backend.external.moleg_client import MolegClient
from backend.core.config import settings


async def sync_articles():
    """조문 동기화 실행"""
    # 데이터베이스 연결
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as db:
        # 법령 조회 (처음 5개만)
        result = await db.execute(
            select(Law).order_by(Law.id).limit(5)
        )
        laws = result.scalars().all()

        print(f"\n📊 총 {len(laws)}개 법령의 조문을 동기화합니다.\n")

        # MolegClient 생성
        moleg_client = MolegClient(api_key=settings.MOLEG_API_KEY)

        # ArticleService 생성
        service = ArticleService(db=db, moleg_client=moleg_client)

        # 각 법령별로 동기화
        total_synced = 0
        total_created = 0
        total_updated = 0

        for i, law in enumerate(laws, 1):
            print(f"[{i}/{len(laws)}] {law.law_name} (ID: {law.id}) 동기화 중...")

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
                print(f"     상세 오류:")
                traceback.print_exc()
                print()
                continue

        print(f"\n🎉 동기화 완료!")
        print(f"   - 총 조문: {total_synced}개")
        print(f"   - 신규: {total_created}개")
        print(f"   - 수정: {total_updated}개")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(sync_articles())
