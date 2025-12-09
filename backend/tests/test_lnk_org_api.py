"""
법제처 API 테스트 - 연계 조례 지자체별 목록 조회
API: http://www.law.go.kr/DRF/lawSearch.do?target=lnkOrg
"""
import os
import sys
import json
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

import requests


# API 설정
BASE_URL = "http://www.law.go.kr/DRF/lawSearch.do"
OC = os.getenv("LAW_API_OC", "minh0313")


def test_fetch_lnk_org_json():
    """연계 조례 목록 JSON 조회 테스트"""
    print("=" * 60)
    print("[TEST] 연계 조례 목록 조회 테스트 (JSON)")
    print("=" * 60)
    print(f"[TIME] 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[DIR] 작업 디렉토리: {os.getcwd()}\n")

    try:
        # 1. API 호출 설정
        org_code = "3220000"  # 부산광역시 동구
        params = {
            "OC": OC,
            "target": "lnkOrg",
            "org": org_code,
            "type": "JSON",
            "display": 20,
            "page": 1
        }

        print(f"[1] API 호출 설정")
        print(f"    - OC: {OC}")
        print(f"    - 지자체 코드: {org_code}")
        print(f"    - 출력 형식: JSON")
        print(f"    - 요청 URL: {BASE_URL}")
        print()

        # 2. API 호출
        print("[2] API 호출 중...")
        response = requests.get(BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        print(f"[OK] 응답 수신 완료 (Status: {response.status_code})")
        print(f"    - 응답 크기: {len(response.content):,} bytes")
        print()

        # 3. JSON 파싱
        print("[3] JSON 파싱 중...")
        data = response.json()
        print("[OK] JSON 파싱 성공")
        print()

        # 4. 결과 분석
        print("=" * 60)
        print("[RESULT] 조회 결과")
        print("=" * 60)

        lnk_org_search = data.get("lnkOrgSearch", {})
        total_cnt = lnk_org_search.get("totalCnt", 0)
        page = lnk_org_search.get("page", 1)
        laws = lnk_org_search.get("law", [])

        print(f"[INFO] 총 건수: {total_cnt}건")
        print(f"[INFO] 현재 페이지: {page}")
        print(f"[INFO] 조회된 항목: {len(laws)}건")
        print()

        # 5. 샘플 데이터 출력
        if laws:
            print("[SAMPLE] 처음 5개 항목:")
            print("-" * 60)
            for i, law in enumerate(laws[:5]):
                print(f"  [{i+1}] {law.get('자치법규명', 'N/A')}")
                print(f"      - 자치법규ID: {law.get('자치법규ID', 'N/A')}")
                print(f"      - 자치법규일련번호: {law.get('자치법규일련번호', 'N/A')}")
                print(f"      - 상위법령: {law.get('법령명한글', 'N/A')} (ID: {law.get('법령ID', 'N/A')})")
                print(f"      - 공포일자: {law.get('공포일자', 'N/A')}")
                print(f"      - 시행일자: {law.get('시행일자', 'N/A')}")
                print(f"      - 제개정구분: {law.get('제개정구분명', 'N/A')}")
                print()
            print("-" * 60)

        # 6. 상위법령 통계
        print("\n[STATS] 상위법령 통계:")
        parent_laws = {}
        for law in laws:
            parent_name = law.get("법령명한글", "Unknown")
            parent_laws[parent_name] = parent_laws.get(parent_name, 0) + 1

        for name, count in sorted(parent_laws.items(), key=lambda x: -x[1])[:10]:
            print(f"    - {name}: {count}건")

        return True

    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] API 호출 실패: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"\n[ERROR] JSON 파싱 실패: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fetch_all_pages():
    """전체 페이지 조회 테스트"""
    print("\n\n" + "=" * 60)
    print("[TEST] 페이지네이션 테스트 (전체 페이지)")
    print("=" * 60)

    try:
        org_code = "3220000"
        all_laws = []
        page = 1

        while True:
            params = {
                "OC": OC,
                "target": "lnkOrg",
                "org": org_code,
                "type": "JSON",
                "display": 100,  # max
                "page": page
            }

            print(f"[PAGE {page}] 조회 중...")
            response = requests.get(BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            laws = data.get("lnkOrgSearch", {}).get("law", [])
            all_laws.extend(laws)
            print(f"    - 조회: {len(laws)}건 (누적: {len(all_laws)}건)")

            if len(laws) < 100:
                print("    - 마지막 페이지 도달")
                break

            page += 1

        print(f"\n[RESULT] 총 {len(all_laws)}건 조회 완료")

        # 중복 확인 (같은 조례가 여러 상위법령과 연계될 수 있음)
        unique_ordinances = set()
        for law in all_laws:
            unique_ordinances.add(law.get("자치법규일련번호"))
        print(f"[INFO] 고유 자치법규 수: {len(unique_ordinances)}개")

        return True

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return False


def test_save_to_file():
    """결과를 파일로 저장 테스트 (JSON + HTML)"""
    print("\n\n" + "=" * 60)
    print("[TEST] 결과 파일 저장 테스트 (JSON + HTML)")
    print("=" * 60)

    try:
        org_code = "3220000"

        # 1. JSON 저장
        params_json = {
            "OC": OC,
            "target": "lnkOrg",
            "org": org_code,
            "type": "JSON",
            "display": 100,
            "page": 1
        }

        response = requests.get(BASE_URL, params=params_json, timeout=30)
        response.raise_for_status()
        data = response.json()

        json_path = os.path.join(PROJECT_ROOT, "test_lnkOrg_result.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] JSON 저장 완료: {json_path}")
        print(f"    - 파일 크기: {os.path.getsize(json_path):,} bytes")

        # 2. HTML 저장
        params_html = {
            "OC": OC,
            "target": "lnkOrg",
            "org": org_code,
            "type": "HTML",
            "display": 100,
            "page": 1
        }

        response = requests.get(BASE_URL, params=params_html, timeout=30)
        response.raise_for_status()

        html_path = os.path.join(PROJECT_ROOT, "test_lnkOrg_result.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(response.text)

        print(f"[OK] HTML 저장 완료: {html_path}")
        print(f"    - 파일 크기: {os.path.getsize(html_path):,} bytes")

        return True

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return False


def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("    법제처 API 테스트 - 연계 조례 지자체별 목록 조회")
    print("=" * 60 + "\n")

    results = {}

    # 1. JSON 조회 테스트
    results['json_fetch'] = test_fetch_lnk_org_json()

    # 2. 페이지네이션 테스트
    results['pagination'] = test_fetch_all_pages()

    # 3. 파일 저장 테스트
    results['save_file'] = test_save_to_file()

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
        print("\n[WARNING] 일부 테스트 실패.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
