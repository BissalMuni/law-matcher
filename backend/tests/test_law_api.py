"""
법제처 API 테스트 - 지방세법 조회
.law-api/test_law_fetcher.py를 참조하여 작성
"""
import os
import sys
import asyncio
from datetime import datetime

# Windows 인코딩 설정
if sys.platform == 'win32':
    os.system('chcp 65001 >nul')

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))


def test_fetch_local_tax_law_sync():
    """지방세법 조회 테스트 (동기 버전)"""
    print("=" * 60)
    print("[TEST] 지방세법 조회 테스트 (동기)")
    print("=" * 60)
    print(f"[TIME] 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[DIR] 작업 디렉토리: {os.getcwd()}\n")

    try:
        # 1. LawAPIService import
        print("[1] LawAPIService 모듈 import 중...")
        from backend.services.law_api_service import LawAPIService
        print("[OK] import 성공\n")

        # 2. LawAPIService 초기화
        print("[2] LawAPIService 초기화 중...")
        service = LawAPIService(cache_dir="./cache/laws_test")
        print("[OK] 초기화 완료")
        print(f"    - API Key 설정: {'있음' if service.api_key else '없음'}")
        print(f"    - Base URL: {service.base_url}\n")

        # 3. 지방세법 조회 테스트
        print("[3] 지방세법 조회 실행")
        print("-" * 60)
        law_name = "지방세법"
        print(f"[INFO] 조회 법령: {law_name}")

        raw_data = service.fetch_law_sync(law_name)

        # 4. 결과 확인
        print("\n" + "=" * 60)
        print("[RESULT] Raw 데이터 조회 결과")
        print("=" * 60)

        if raw_data:
            print(f"[SUCCESS] {law_name} 조회 성공!")
            print(f"[INFO] 데이터 크기: {len(raw_data):,} bytes ({len(raw_data)/1024:.1f}KB)")

            # 미리보기
            preview_len = min(500, len(raw_data))
            print(f"\n[PREVIEW] 처음 {preview_len}자:")
            print("-" * 60)
            print(raw_data[:preview_len])
            print("-" * 60)
        else:
            print(f"[FAIL] {law_name} 조회 실패")
            return False

        # 5. 파싱 테스트
        print("\n" + "=" * 60)
        print("[TEST] 파싱 테스트")
        print("=" * 60)

        parsed = service.parse_law_response(raw_data)

        if parsed:
            print(f"[SUCCESS] 파싱 성공!")
            print(f"[INFO] 법령명: {parsed.law_name}")
            print(f"[INFO] 법령ID: {parsed.law_id}")
            print(f"[INFO] 공포일자: {parsed.proclaimed_date}")
            print(f"[INFO] 시행일자: {parsed.enforced_date}")
            print(f"[INFO] 소관부처: {parsed.ministry}")
            print(f"[INFO] 조문 수: {len(parsed.articles)}개")

            # 조문 샘플 출력
            if parsed.articles:
                print("\n[SAMPLE] 조문 샘플 (처음 3개):")
                print("-" * 60)
                for i, (key, content) in enumerate(list(parsed.articles.items())[:3]):
                    preview = content[:100] + "..." if len(content) > 100 else content
                    print(f"  [{key}] {preview}")
                print("-" * 60)
        else:
            print("[FAIL] 파싱 실패")
            return False

        # 6. 캐시 상태 확인
        print("\n[CACHE] 캐시 상태:")
        cache_status = service.get_cache_status()
        print(f"    - 캐시 디렉토리: {cache_status['cache_dir']}")
        print(f"    - 캐시된 법령: {cache_status['cached_laws']}")
        print(f"    - 총 캐시 수: {cache_status['total_cached']}")

        return True

    except Exception as e:
        print("\n" + "=" * 60)
        print("[ERROR] 테스트 중 오류 발생")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_fetch_local_tax_law_async():
    """지방세법 조회 테스트 (비동기 버전)"""
    print("\n\n" + "=" * 60)
    print("[TEST] 지방세법 조회 테스트 (비동기)")
    print("=" * 60)

    try:
        from backend.services.law_api_service import LawAPIService

        service = LawAPIService(cache_dir="./cache/laws_test")
        law_name = "지방세법"

        print(f"[INFO] 조회 법령: {law_name}")

        # 비동기 조회 및 파싱
        parsed = await service.fetch_and_parse(law_name)

        if parsed:
            print(f"[SUCCESS] 비동기 조회 및 파싱 성공!")
            print(f"[INFO] 법령명: {parsed.law_name}")
            print(f"[INFO] 조문 수: {len(parsed.articles)}개")
            return True
        else:
            print("[FAIL] 비동기 조회 실패")
            return False

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fetch_and_parse_sync():
    """fetch_and_parse_sync 통합 테스트"""
    print("\n\n" + "=" * 60)
    print("[TEST] fetch_and_parse_sync 통합 테스트")
    print("=" * 60)

    try:
        from backend.services.law_api_service import LawAPIService

        service = LawAPIService(cache_dir="./cache/laws_test")
        law_name = "지방세법"

        print(f"[INFO] 조회 법령: {law_name}")

        # 통합 함수로 조회 및 파싱
        parsed = service.fetch_and_parse_sync(law_name)

        if parsed:
            print(f"[SUCCESS] 통합 함수 테스트 성공!")
            print(f"[INFO] 법령명: {parsed.law_name}")
            print(f"[INFO] 법령ID: {parsed.law_id}")
            print(f"[INFO] 조문 수: {len(parsed.articles)}개")
            print(f"[INFO] 원본 크기: {parsed.raw_size:,} bytes")
            return True
        else:
            print("[FAIL] 통합 함수 테스트 실패")
            return False

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("       법제처 API 테스트 - 지방세법 조회")
    print("=" * 60 + "\n")

    results = {}

    # 1. 동기 테스트
    results['sync'] = test_fetch_local_tax_law_sync()

    # 2. 통합 함수 테스트
    results['fetch_and_parse'] = test_fetch_and_parse_sync()

    # 3. 비동기 테스트
    results['async'] = asyncio.run(test_fetch_local_tax_law_async())

    # 최종 결과
    print("\n\n" + "=" * 60)
    print("[FINAL] 최종 테스트 결과")
    print("=" * 60)

    for test_name, success in results.items():
        status = "PASS" if success else "FAIL"
        icon = "O" if success else "X"
        print(f"  [{icon}] {test_name}: {status}")

    total = len(results)
    passed = sum(1 for s in results.values() if s)
    print(f"\n[TOTAL] {passed}/{total} 테스트 통과")

    if all(results.values()):
        print("\n[SUCCESS] 모든 테스트 통과! API가 정상 작동합니다.")
        return 0
    else:
        print("\n[WARNING] 일부 테스트 실패. API 키 또는 네트워크 연결을 확인하세요.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
