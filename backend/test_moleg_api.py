"""
법제처 API 응답 테스트
"""
import asyncio
import json
from backend.external.moleg_client import MolegClient
from backend.core.config import settings


async def test_api():
    """법제처 API 테스트"""
    client = MolegClient(api_key=settings.MOLEG_API_KEY)

    # 테스트: law_serial_no = 269929 (국민건강증진법)
    law_serial_no = "269929"

    print(f"📡 법령 상세 조회 테스트: MST={law_serial_no}\n")

    try:
        # Raw API 호출
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            params = {
                "OC": settings.MOLEG_API_KEY,
                "target": "law",
                "MST": law_serial_no,
                "type": "JSON",
            }

            response = await http_client.get(
                "https://www.law.go.kr/DRF/lawService.do",
                params=params,
            )
            response.raise_for_status()

            data = response.json()

            print("📄 API 응답 구조:")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
            print("\n\n")

            if "법령" in data:
                law_data = data["법령"]
                print(f"법령명: {law_data.get('법령명_한글', 'N/A')}")
                print(f"법령종류: {law_data.get('법령종류', 'N/A')}")
                print(f"조문 타입: {type(law_data.get('조문'))}")
                print(f"조문 데이터:")
                print(json.dumps(law_data.get("조문", []), ensure_ascii=False, indent=2)[:1000])

    except Exception as e:
        import traceback
        print(f"❌ 오류 발생: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_api())
