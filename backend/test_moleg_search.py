"""
법제처 API 검색 테스트
"""
import asyncio
import json
from backend.external.moleg_client import MolegClient
from backend.core.config import settings


async def test_search():
    """법제처 API 검색 테스트"""
    client = MolegClient(api_key=settings.MOLEG_API_KEY)

    print("📡 법령 검색 테스트: 국민건강증진법\n")

    try:
        # Raw API 호출
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            params = {
                "OC": settings.MOLEG_API_KEY,
                "target": "law",
                "query": "국민건강증진법",
                "type": "JSON",
            }

            response = await http_client.get(
                "https://www.law.go.kr/DRF/lawSearch.do",
                params=params,
            )
            response.raise_for_status()

            data = response.json()

            print("📄 API 응답:")
            if "LawSearch" in data:
                laws = data["LawSearch"].get("law", [])
                print(f"검색 결과: {len(laws)}개\n")

                for i, law in enumerate(laws[:3], 1):
                    print(f"[{i}] {law.get('법령명한글', 'N/A')}")
                    print(f"    법령ID: {law.get('법령ID', 'N/A')}")
                    print(f"    법령일련번호: {law.get('법령일련번호', 'N/A')}")
                    print(f"    현행연혁코드(MST): {law.get('현행연혁코드', 'N/A')}")
                    print(f"    법령종류: {law.get('법령종류', 'N/A')}")
                    print()

    except Exception as e:
        import traceback
        print(f"❌ 오류 발생: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_search())
