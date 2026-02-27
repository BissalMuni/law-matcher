"""
법제처 OPEN API 테스트: 제개정이유내용 확인
lawService.do?target=law API에서 제개정이유내용 필드를 조회하는 테스트
"""
import urllib.request
import json
import sys
import re
from urllib.parse import urlencode
from collections import Counter

API_KEY = "minh0313"
BASE_URL = "https://www.law.go.kr/DRF"


def fetch_json(endpoint, params):
    """URL 호출 후 JSON 파싱"""
    url = f"{BASE_URL}/{endpoint}?{urlencode(params)}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def fetch_text(endpoint, params):
    """URL 호출 후 텍스트 반환"""
    url = f"{BASE_URL}/{endpoint}?{urlencode(params)}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def test_law_list():
    """먼저 법령 목록을 조회해서 테스트할 법령 MST를 가져옴"""
    print("=" * 60)
    print("[1] 법령 목록 조회 (최근 개정 법령)")
    print("=" * 60)

    params = {
        "OC": API_KEY,
        "target": "law",
        "type": "JSON",
        "display": 5,
        "page": 1,
    }

    data = fetch_json("lawSearch.do", params)
    laws = data.get("LawSearch", {}).get("law", [])

    if isinstance(laws, dict):
        laws = [laws]

    print(f"조회된 법령 수: {len(laws)}")
    for law in laws[:5]:
        print(f"  - {law.get('법령명한글', 'N/A')} | MST: {law.get('법령일련번호', 'N/A')} | 제개정구분: {law.get('제개정구분명', 'N/A')} | 공포일자: {law.get('공포일자', 'N/A')}")

    return laws


def test_law_detail_json(law_mst: str, law_name: str = ""):
    """법령 본문 조회 (JSON) - 제개정이유내용 확인"""
    print()
    print("=" * 60)
    print(f"[2] 법령 본문 조회 (JSON) - MST: {law_mst} ({law_name})")
    print("=" * 60)

    params = {
        "OC": API_KEY,
        "target": "law",
        "MST": law_mst,
        "type": "JSON",
    }

    data = fetch_json("lawService.do", params)

    # 전체 응답의 최상위 키 확인
    print(f"\n[최상위 키]: {list(data.keys())}")

    law_data = data.get("법령", {})
    print(f"[법령 하위 키]: {list(law_data.keys())}")

    # 기본정보
    basic_info = law_data.get("기본정보", {})
    print(f"\n[기본정보 키]: {list(basic_info.keys())}")
    print(f"  법령명: {basic_info.get('법령명_한글', 'N/A')}")
    print(f"  공포일자: {basic_info.get('공포일자', 'N/A')}")
    print(f"  시행일자: {basic_info.get('시행일자', 'N/A')}")
    print(f"  제개정구분: {basic_info.get('제개정구분', 'N/A')}")

    # 핵심: 제개정이유내용
    revision_reason = law_data.get("제개정이유내용")
    amendment_content = law_data.get("개정문내용")

    print(f"\n{'=' * 60}")
    print(f"[핵심] 제개정이유내용 존재 여부: {'있음' if revision_reason else '없음'}")
    print(f"{'=' * 60}")

    if revision_reason:
        reason_text = str(revision_reason)
        print(f"[제개정이유내용 타입]: {type(revision_reason).__name__}")
        print(f"[제개정이유내용 길이]: {len(reason_text)} chars")
        print(f"\n--- 제개정이유내용 (처음 2000자) ---")
        print(reason_text[:2000])
        if len(reason_text) > 2000:
            print(f"\n... (총 {len(reason_text)}자 중 2000자만 표시)")
    else:
        print("[제개정이유내용] 필드가 응답에 없음 (None)")
        print(f"[법령 데이터 전체 키 확인]: {list(law_data.keys())}")

    print(f"\n{'=' * 60}")
    print(f"[핵심] 개정문내용 존재 여부: {'있음' if amendment_content else '없음'}")
    print(f"{'=' * 60}")

    if amendment_content:
        content_text = str(amendment_content)
        print(f"[개정문내용 타입]: {type(amendment_content).__name__}")
        print(f"[개정문내용 길이]: {len(content_text)} chars")
        print(f"\n--- 개정문내용 (처음 2000자) ---")
        print(content_text[:2000])
        if len(content_text) > 2000:
            print(f"\n... (총 {len(content_text)}자 중 2000자만 표시)")
    else:
        print("[개정문내용] 필드가 응답에 없음 (None)")

    # 조문 정보에서 제개정 관련 필드도 확인
    articles = law_data.get("조문", {})
    if articles:
        article_list = articles.get("조문단위", [])
        if isinstance(article_list, dict):
            article_list = [article_list]

        print(f"\n{'=' * 60}")
        print(f"[조문] 총 {len(article_list)}개 조문")
        print(f"{'=' * 60}")

        for art in article_list[:5]:
            art_no = art.get("조문번호", "N/A")
            art_title = art.get("조문제목", "N/A")
            art_revision_type = art.get("조문제개정유형", "N/A")
            art_changed = art.get("조문변경여부", "N/A")
            print(f"  조문 {art_no} ({art_title}) | 제개정유형: {art_revision_type} | 변경여부: {art_changed}")

    # 부칙 정보 확인
    addenda = law_data.get("부칙", {})
    if addenda:
        addenda_list = addenda.get("부칙단위", [])
        if isinstance(addenda_list, dict):
            addenda_list = [addenda_list]
        print(f"\n[부칙] 총 {len(addenda_list)}개 부칙 항목")
        for add in addenda_list[:2]:
            print(f"  부칙 번호: {add.get('부칙번호', 'N/A')} | 부칙제개정유형: {add.get('부칙제개정유형', 'N/A')}")

    return data


def test_law_detail_xml(law_mst: str, law_name: str = ""):
    """법령 본문 조회 (XML) - JSON에서 못 찾으면 XML에서 시도"""
    print()
    print("=" * 60)
    print(f"[3] 법령 본문 조회 (XML) - MST: {law_mst} ({law_name})")
    print("=" * 60)

    params = {
        "OC": API_KEY,
        "target": "law",
        "MST": law_mst,
        "type": "XML",
    }

    text = fetch_text("lawService.do", params)

    reason_match = re.search(r"<제개정이유내용>(.*?)</제개정이유내용>", text, re.DOTALL)
    amendment_match = re.search(r"<개정문내용>(.*?)</개정문내용>", text, re.DOTALL)

    if reason_match:
        reason_text = reason_match.group(1).strip()
        print(f"[XML] 제개정이유내용 발견! 길이: {len(reason_text)} chars")
        print(f"\n--- 제개정이유내용 (처음 2000자) ---")
        print(reason_text[:2000])
    else:
        print("[XML] 제개정이유내용 태그 없음")

    if amendment_match:
        amend_text = amendment_match.group(1).strip()
        print(f"\n[XML] 개정문내용 발견! 길이: {len(amend_text)} chars")
        print(f"\n--- 개정문내용 (처음 1000자) ---")
        print(amend_text[:1000])
    else:
        print("[XML] 개정문내용 태그 없음")

    revision_types = re.findall(r"<조문제개정유형>(.*?)</조문제개정유형>", text)
    changed_flags = re.findall(r"<조문변경여부>(.*?)</조문변경여부>", text)

    if revision_types:
        type_counts = Counter(revision_types)
        print(f"\n[조문제개정유형 분포]: {dict(type_counts)}")

    if changed_flags:
        flag_counts = Counter(changed_flags)
        print(f"[조문변경여부 분포]: {dict(flag_counts)}")


def save_full_response(data: dict, filename: str):
    """전체 응답을 JSON 파일로 저장"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n[저장] 전체 응답 -> {filename}")


if __name__ == "__main__":
    print("법제처 OPEN API - 제개정이유내용 테스트")
    print("=" * 60)

    if len(sys.argv) > 1:
        test_mst = sys.argv[1]
        test_name = sys.argv[2] if len(sys.argv) > 2 else "지정법령"
    else:
        # Step 1: 법령 목록 조회
        laws = test_law_list()
        if not laws:
            print("법령 목록 조회 실패!")
            sys.exit(1)

        # 가장 먼저 나오는 '일부개정' 법령 선택 (제개정이유가 있을 가능성 높음)
        test_law = None
        for law in laws:
            if "개정" in law.get("제개정구분명", ""):
                test_law = law
                break

        if not test_law:
            test_law = laws[0]

        test_mst = test_law.get("법령일련번호", "")
        test_name = test_law.get("법령명한글", "")

    # Step 2: JSON 본문 조회
    detail_data = test_law_detail_json(test_mst, test_name)

    # Step 3: XML 본문 조회 (비교)
    test_law_detail_xml(test_mst, test_name)

    # Step 4: 전체 응답 저장
    if detail_data:
        save_full_response(detail_data, "test_api_response.json")

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)
