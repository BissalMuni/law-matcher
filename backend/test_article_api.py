#!/usr/bin/env python
"""
Article API 엔드포인트 테스트 스크립트
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.core.database import async_session
from backend.models.user import User
from backend.models.law import Law
from backend.models.article import Article
from backend.services.article_service import ArticleService
from backend.external.moleg_client import MolegClient
from backend.core.config import settings


async def test_article_endpoints():
    """Article API 엔드포인트 기능 테스트"""

    print("=" * 80)
    print("📊 Article API 기능 테스트")
    print("=" * 80)

    async with async_session() as db:
        # 1. 데이터베이스 테이블 확인
        print("\n[1] 데이터베이스 테이블 확인")
        print("-" * 80)

        article_count = await db.scalar(select(func.count()).select_from(Article))
        print(f"✅ articles 테이블: {article_count}개 레코드")

        # 2. ArticleService 초기화
        print("\n[2] ArticleService 초기화")
        print("-" * 80)

        moleg_client = MolegClient(api_key=settings.MOLEG_API_KEY)
        service = ArticleService(db=db, moleg_client=moleg_client)
        print("✅ ArticleService 생성 완료")

        # 3. 조문 목록 조회 테스트
        print("\n[3] 조문 목록 조회 테스트")
        print("-" * 80)

        from backend.schemas.article import ArticleListParams

        params = ArticleListParams(
            page=1,
            size=5,
        )

        try:
            result = await service.get_articles(params)
            print(f"✅ 조회 성공: {result.total}건 중 {len(result.items)}건 표시")

            if result.items:
                first_article = result.items[0]
                print(f"\n   첫 번째 조문:")
                print(f"   - ID: {first_article.id}")
                print(f"   - 조문번호: {first_article.article_no}")
                print(f"   - 제목: {first_article.article_title}")
                print(f"   - 법령 ID: {first_article.law_id}")
        except Exception as e:
            print(f"❌ 조회 실패: {e}")

        # 4. 특정 조문 상세 조회 테스트
        print("\n[4] 조문 상세 조회 테스트")
        print("-" * 80)

        # 첫 번째 조문이 있으면 조회
        first_article_obj = await db.scalar(
            select(Article).limit(1)
        )

        if first_article_obj:
            try:
                article_detail = await service.get_article_by_id(first_article_obj.id)
                print(f"✅ 조회 성공: ID {article_detail.id}")
                print(f"   - 조문번호: {article_detail.article_no}")
                print(f"   - 제목: {article_detail.article_title}")
                print(f"   - 내용 길이: {len(article_detail.article_content)}자")
                print(f"   - Content Hash: {article_detail.content_hash[:16]}...")
            except Exception as e:
                print(f"❌ 조회 실패: {e}")
        else:
            print("⚠️  테스트할 조문이 없습니다.")

        # 5. 변경 이력 조회 테스트
        print("\n[5] 변경 이력 조회 테스트")
        print("-" * 80)

        if first_article_obj:
            try:
                changes = await service.get_article_changes(first_article_obj.id)
                print(f"✅ 조회 성공: {len(changes)}건의 변경 이력")

                if changes:
                    latest_change = changes[0]
                    print(f"\n   최근 변경:")
                    print(f"   - 변경일: {latest_change.change_date}")
                    print(f"   - 변경 타입: {latest_change.change_type}")
                    print(f"   - 감지일: {latest_change.detected_at}")
            except Exception as e:
                print(f"❌ 조회 실패: {e}")

        # 6. 법령 목록 확인 (동기화 테스트용)
        print("\n[6] 법령 목록 확인")
        print("-" * 80)

        laws = await db.execute(select(Law).limit(3))
        laws = laws.scalars().all()

        print(f"✅ 총 {len(laws)}개 법령 확인:")
        for law in laws:
            print(f"   - ID: {law.id}, 이름: {law.law_name}")

        # 7. 조문 동기화 기능 확인 (실제 실행하지 않음)
        print("\n[7] 조문 동기화 기능 확인")
        print("-" * 80)
        print("ℹ️  동기화는 수동으로 POST /articles/sync 엔드포인트를 호출하여 테스트하세요.")
        print("   Swagger UI: http://localhost:8000/docs")

    print("\n" + "=" * 80)
    print("✅ 테스트 완료!")
    print("=" * 80)
    print("\n다음 단계:")
    print("1. Swagger UI (http://localhost:8000/docs)에서 인증 후 API 테스트")
    print("2. Frontend에서 API 통합 테스트")
    print("3. E2E 시나리오 테스트")
    print()


if __name__ == "__main__":
    asyncio.run(test_article_endpoints())
