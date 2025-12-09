"""
자치법규 목록 조회 API 테스트
법제처 Open API - 자치법규 검색
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Windows 인코딩 설정
if sys.platform == 'win32':
    os.system('chcp 65001 >nul')

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

import httpx

# JSON 저장 디렉토리
OUTPUT_DIR = Path(PROJECT_ROOT) / "data" / "ordinances"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_json(data: dict, filename: str) -> str:
    """JSON 데이터를 파일로 저장"""
    filepath = OUTPUT_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(filepath)


def fetch_all_ordinances(query: str = None, org: str = None, sborg: str = None, knd: str = None) -> list:
    """
    자치법규 전체 데이터 가져오기 (페이지네이션 처리)

    Args:
        query: 검색 키워드
        org: 도/특별시/광역시 코드
        sborg: 시/군/구 코드
        knd: 법규 종류 (30001=조례, 30002=규칙 등)

    Returns:
        전체 자치법규 목록
    """
    api_key = os.getenv('MOLEG_API_KEY', 'test')
    base_url = "http://www.law.go.kr/DRF/lawSearch.do"

    all_ordinances = []
    page = 1
    max_display = 100  # API 최대값

    params = {
        'OC': api_key,
        'target': 'ordin',
        'type': 'JSON',
        'display': max_display,
        'nw': 1,  # 현행
    }

    if query:
        params['query'] = query
    if org:
        params['org'] = org
    if sborg:
        params['sborg'] = sborg
    if knd:
        params['knd'] = knd

    print(f"[INFO] 전체 데이터 수집 시작...")
    print(f"[INFO] 파라미터: query={query}, org={org}, sborg={sborg}, knd={knd}")

    with httpx.Client(timeout=60.0) as client:
        while True:
            params['page'] = page
            response = client.get(base_url, params=params)

            if response.text.strip().startswith('<!DOCTYPE'):
                print(f"[ERROR] 페이지 {page}: HTML 응답 (에러)")
                break

            data = response.json()
            ordin_search = data.get('OrdinSearch', {})

            if not ordin_search:
                break

            total_count = int(ordin_search.get('totalCnt', 0))
            ordinances = ordin_search.get('law', [])

            if isinstance(ordinances, dict):
                ordinances = [ordinances]

            if not ordinances:
                break

            all_ordinances.extend(ordinances)

            print(f"[PAGE {page}] {len(ordinances)}건 수집 (누적: {len(all_ordinances)}/{total_count})")

            # 모든 데이터 수집 완료
            if len(all_ordinances) >= total_count:
                break

            page += 1

            # API 부하 방지
            import time
            time.sleep(0.5)

    print(f"[DONE] 총 {len(all_ordinances)}건 수집 완료")
    return all_ordinances


def test_fetch_all_gangnam_ordinances():
    """강남구 자치법규 전체 데이터 수집 및 저장"""
    print("=" * 60)
    print("[TEST] 강남구 자치법규 전체 데이터 수집")
    print("=" * 60)
    print(f"[TIME] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 서울특별시 강남구 전체 자치법규 수집
        all_data = fetch_all_ordinances(org='6110000', sborg='3220000')

        if all_data:
            # JSON 파일로 저장
            result = {
                'meta': {
                    'query': '서울특별시 강남구',
                    'org': '6110000',
                    'sborg': '3220000',
                    'total_count': len(all_data),
                    'fetched_at': datetime.now().isoformat(),
                },
                'ordinances': all_data
            }

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"gangnam_all_{timestamp}.json"
            saved_path = save_json(result, filename)

            print(f"\n[SAVED] {saved_path}")
            print(f"[INFO] 총 {len(all_data)}건 저장 완료")

            # 종류별 통계
            types = {}
            for ordin in all_data:
                ordin_type = ordin.get('자치법규종류', '기타')
                types[ordin_type] = types.get(ordin_type, 0) + 1

            print("\n[STATS] 종류별 통계:")
            for t, count in sorted(types.items(), key=lambda x: -x[1]):
                print(f"  - {t}: {count}건")

            return True
        else:
            print("[FAIL] 데이터 수집 실패")
            return False

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


# def test_ordinance_list_api():
#     """자치법규 목록 조회 테스트 - 강남구 검색"""
#     print("=" * 60)
#     print("[TEST] 자치법규 목록 조회 API 테스트")
#     print("=" * 60)
#     print(f"[TIME] 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

#     # API 키 (OC 값)
#     api_key = os.getenv('MOLEG_API_KEY', 'test')
#     base_url = "http://www.law.go.kr/DRF/lawSearch.do"

#     params = {
#         'OC': api_key,
#         'target': 'ordin',
#         'type': 'JSON',
#         'query': '강남구',
#         'display': 20,
#         'page': 1,
#         'sort': 'ddes',  # 공포일자 내림차순
#         'nw': 1,  # 현행
#     }

#     print(f"\n[INFO] API Key (OC): {api_key}")
#     print(f"[INFO] Base URL: {base_url}")
#     print(f"[INFO] 검색어: {params['query']}")
#     print("-" * 60)

#     try:
#         with httpx.Client(timeout=30.0) as client:
#             response = client.get(base_url, params=params)

#             print(f"\n[RESPONSE] Status Code: {response.status_code}")
#             print(f"[RESPONSE] Content-Type: {response.headers.get('content-type', 'N/A')}")
#             print(f"[RESPONSE] Content Length: {len(response.text)} bytes")

#             # HTML 응답 체크 (에러 페이지)
#             if response.text.strip().startswith('<!DOCTYPE') or response.text.strip().startswith('<html'):
#                 print("\n[WARNING] HTML 응답 수신 (에러 페이지일 수 있음)")
#                 print("[PREVIEW] 처음 500자:")
#                 print("-" * 60)
#                 print(response.text[:500])
#                 print("-" * 60)
#                 return False

#             # JSON 파싱
#             data = response.json()
#             print("\n[SUCCESS] JSON 응답 수신!")

#             # JSON 파일로 저장
#             timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#             filename = f"gangnam_search_{timestamp}.json"
#             saved_path = save_json(data, filename)
#             print(f"[SAVED] JSON 파일 저장: {saved_path}")

#             # 응답 구조 확인
#             print(f"\n[INFO] Top-level keys: {list(data.keys())}")

#             # OrdinSearch 구조
#             ordin_search = data.get('OrdinSearch', {})
#             if ordin_search:
#                 total_count = ordin_search.get('totalCnt', 0)
#                 print(f"[INFO] 총 검색 결과: {total_count}건")

#                 ordinances = ordin_search.get('law', [])
#                 if isinstance(ordinances, dict):
#                     ordinances = [ordinances]

#                 print(f"[INFO] 현재 페이지 결과: {len(ordinances)}건")

#                 if ordinances:
#                     print("\n[SAMPLE] 자치법규 목록 (처음 5개):")
#                     print("-" * 60)
#                     for i, ordin in enumerate(ordinances[:5]):
#                         print(f"  [{i+1}] {ordin.get('자치법규명', 'N/A')}")
#                         print(f"      - 자치법규ID: {ordin.get('자치법규ID', 'N/A')}")
#                         print(f"      - 지자체: {ordin.get('지자체기관명', 'N/A')}")
#                         print(f"      - 종류: {ordin.get('자치법규종류', 'N/A')}")
#                         print(f"      - 공포일자: {ordin.get('공포일자', 'N/A')}")
#                         print(f"      - 시행일자: {ordin.get('시행일자', 'N/A')}")
#                     print("-" * 60)

#                 return True
#             else:
#                 print("[WARNING] OrdinSearch 키가 없습니다.")
#                 print(f"[DEBUG] 응답 데이터: {str(data)[:500]}")
#                 return False

#     except httpx.HTTPError as e:
#         print(f"\n[ERROR] HTTP 오류: {e}")
#         return False
#     except Exception as e:
#         print(f"\n[ERROR] 예외 발생: {type(e).__name__}: {e}")
#         import traceback
#         traceback.print_exc()
#         return False


# def test_ordinance_by_region():
#     """지역별 자치법규 조회 테스트 - 서울특별시 강남구"""
#     print("\n\n" + "=" * 60)
#     print("[TEST] 지역별 자치법규 조회 테스트")
#     print("=" * 60)

#     api_key = os.getenv('MOLEG_API_KEY', 'test')
#     base_url = "http://www.law.go.kr/DRF/lawSearch.do"

#     # 서울특별시: 6110000, 강남구: 3220000
#     params = {
#         'OC': api_key,
#         'target': 'ordin',
#         'type': 'JSON',
#         'org': '6110000',      # 서울특별시
#         'sborg': '3220000',    # 강남구
#         'display': 10,
#         'page': 1,
#         'nw': 1,
#     }

#     print(f"[INFO] 검색 조건: 서울특별시 강남구 (org={params['org']}, sborg={params['sborg']})")
#     print("-" * 60)

#     try:
#         with httpx.Client(timeout=30.0) as client:
#             response = client.get(base_url, params=params)

#             print(f"[RESPONSE] Status Code: {response.status_code}")

#             if response.text.strip().startswith('<!DOCTYPE') or response.text.strip().startswith('<html'):
#                 print("[WARNING] HTML 응답 - 에러 페이지")
#                 return False

#             data = response.json()

#             # JSON 파일로 저장
#             timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#             filename = f"gangnam_region_{timestamp}.json"
#             saved_path = save_json(data, filename)
#             print(f"[SAVED] JSON 파일 저장: {saved_path}")

#             ordin_search = data.get('OrdinSearch', {})

#             if ordin_search:
#                 total_count = ordin_search.get('totalCnt', 0)
#                 ordinances = ordin_search.get('law', [])
#                 if isinstance(ordinances, dict):
#                     ordinances = [ordinances]

#                 print(f"[SUCCESS] 서울특별시 강남구 자치법규: 총 {total_count}건, 현재 페이지 {len(ordinances)}건")

#                 if ordinances:
#                     print("\n[SAMPLE] 강남구 자치법규 (처음 3개):")
#                     for i, ordin in enumerate(ordinances[:3]):
#                         print(f"  [{i+1}] {ordin.get('자치법규명', 'N/A')} ({ordin.get('자치법규종류', '')})")

#                 return True
#             return False

#     except Exception as e:
#         print(f"[ERROR] {type(e).__name__}: {e}")
#         return False


# def test_ordinance_by_type():
#     """자치법규 종류별 조회 테스트 - 조례만 검색"""
#     print("\n\n" + "=" * 60)
#     print("[TEST] 자치법규 종류별 조회 테스트 (조례)")
#     print("=" * 60)

#     api_key = os.getenv('MOLEG_API_KEY', 'test')
#     base_url = "http://www.law.go.kr/DRF/lawSearch.do"

#     params = {
#         'OC': api_key,
#         'target': 'ordin',
#         'type': 'JSON',
#         'query': '강남구',
#         'knd': '30001',  # 조례
#         'display': 10,
#         'page': 1,
#         'nw': 1,
#     }

#     print(f"[INFO] 검색 조건: '강남구' + 조례(knd=30001)")
#     print("-" * 60)

#     try:
#         with httpx.Client(timeout=30.0) as client:
#             response = client.get(base_url, params=params)

#             if response.text.strip().startswith('<!DOCTYPE'):
#                 print("[WARNING] HTML 응답 - 에러 페이지")
#                 return False

#             data = response.json()

#             # JSON 파일로 저장
#             timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#             filename = f"gangnam_ordinance_{timestamp}.json"
#             saved_path = save_json(data, filename)
#             print(f"[SAVED] JSON 파일 저장: {saved_path}")

#             ordin_search = data.get('OrdinSearch', {})

#             if ordin_search:
#                 total_count = ordin_search.get('totalCnt', 0)
#                 ordinances = ordin_search.get('law', [])
#                 if isinstance(ordinances, dict):
#                     ordinances = [ordinances]

#                 print(f"[SUCCESS] 강남구 조례: 총 {total_count}건")

#                 if ordinances:
#                     print("\n[SAMPLE] 강남구 조례 (처음 3개):")
#                     for i, ordin in enumerate(ordinances[:3]):
#                         print(f"  [{i+1}] {ordin.get('자치법규명', 'N/A')}")

#                 return True
#             return False

#     except Exception as e:
#         print(f"[ERROR] {type(e).__name__}: {e}")
#         return False


def fetch_ordinance_fields(org: str) -> dict:
    """
    자치법규 분야/분류 조회

    Args:
        org: 기관코드 (예: 서울시=6110000)

    Returns:
        분야/분류 데이터
    """
    api_key = os.getenv('MOLEG_API_KEY', 'test')
    base_url = "http://www.law.go.kr/DRF/lawSearch.do"

    params = {
        'OC': api_key,
        'target': 'ordinfd',  # 자치법규 분야
        'org': org,
        'type': 'JSON',
    }

    print(f"[INFO] 자치법규 분야/분류 조회: org={org}")

    with httpx.Client(timeout=30.0) as client:
        response = client.get(base_url, params=params)

        if response.text.strip().startswith('<!DOCTYPE'):
            print("[ERROR] HTML 응답 (에러)")
            return {}

        return response.json()


def test_fetch_ordinance_fields():
    """자치법규 분야/분류 조회 테스트 - 서울특별시"""
    print("=" * 60)
    print("[TEST] 자치법규 분야/분류 조회 API 테스트")
    print("=" * 60)
    print(f"[TIME] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 서울특별시 분야/분류 조회
        org_code = '3220000'
        data = fetch_ordinance_fields(org_code)

        if data:
            # JSON 파일로 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"seoul_fields_{timestamp}.json"
            saved_path = save_json(data, filename)

            print(f"\n[SAVED] {saved_path}")
            print(f"[INFO] Top-level keys: {list(data.keys())}")

            # 응답 구조 분석 (ordinFdList.ordinFd 형식)
            ordin_fd_list = data.get('ordinFdList', {})
            fields = ordin_fd_list.get('ordinFd', [])

            if fields:
                if isinstance(fields, dict):
                    fields = [fields]

                print(f"\n[FIELDS] 분야/분류 목록 ({len(fields)}개):")
                print("-" * 60)
                for field in fields:
                    seq = field.get('분류seq', '')
                    name = field.get('분류명', 'N/A')
                    count = field.get('해당자치법규갯수', 0)
                    print(f"  [{seq}] {name}: {count}건")
                print("-" * 60)

                return True
            else:
                print("[WARNING] ordinFd 데이터가 없습니다.")
                print(f"[DEBUG] 응답: {str(data)[:500]}")
                return False
        else:
            print("[FAIL] 데이터 조회 실패")
            return False

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("       자치법규 API 테스트 - 강남구 검색")
    print("=" * 60 + "\n")

    results = {}

    # 1. 기본 검색 테스트
    # results['basic_search'] = test_ordinance_list_api()

    # 2. 지역별 검색 테스트
    # results['region_search'] = test_ordinance_by_region()

    # 3. 종류별 검색 테스트
    # results['type_search'] = test_ordinance_by_type()

    # 4. 전체 데이터 수집 테스트
    # results['fetch_all'] = test_fetch_all_gangnam_ordinances()

    # 5. 분야/분류 조회 테스트
    results['ordinance_fields'] = test_fetch_ordinance_fields()

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
        print("\n[SUCCESS] 모든 테스트 통과!")
        return 0
    else:
        print("\n[WARNING] 일부 테스트 실패. API 응답을 확인하세요.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
