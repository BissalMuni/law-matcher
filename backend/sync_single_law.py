"""
단일 법령 조문 동기화 스크립트
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.models.law import Law
from backend.services.article_service import ArticleService
from backend.external.moleg_client import MolegClient
from backend.core.config import settings


async def sync_single_law(law_id: int):
    """단일 법령 조문 동기화"""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as db:
        # 법령 조회
        law = await db.get(Law, law_id)
        if not law:
            print(f"❌ 법령을 찾을 수 없습니다: ID={law_id}")
            return

        print(f"\n📊 법령 정보:")
        print(f"   - ID: {law.id}")
        print(f"   - 법령명: {law.law_name}")
        print(f"   - 법령일련번호: {law.law_serial_no}")
        print(f"   - 법령ID: {law.law_id}")
        print()

        # MolegClient 생성
        moleg_client = MolegClient(api_key=settings.MOLEG_API_KEY)

        # ArticleService 생성
        service = ArticleService(db=db, moleg_client=moleg_client)

        # 조문 동기화
        print(f"📥 조문 동기화 시작...\n")

        try:
            result = await service.sync_articles_for_law(
                law_id=law.id,
                force=True,
            )

            print(f"✅ 동기화 성공!")
            print(f"   - 총 조문: {result['synced_articles']}개")
            print(f"   - 신규: {result['created']}개")
            print(f"   - 수정: {result['updated']}개")
            print(f"   - 삭제: {result['deleted']}개")

        except Exception as e:
            import traceback
            print(f"❌ 동기화 실패: {str(e)}")
            traceback.print_exc()

    await engine.dispose()


if __name__ == "__main__":
    # 국민건강증진법 ID: 472
    asyncio.run(sync_single_law(472))
