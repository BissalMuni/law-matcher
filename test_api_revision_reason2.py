"""
법제처 OPEN API 테스트 2: XML 기반 제개정이유내용 확인
- JSON에서는 제개정이유내용이 누락됨 -> XML 사용 필수
- 일부개정 법령 위주로 테스트 (제개정이유가 풍부함)
"""
import urllib.request
import json
import sys
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
from collections import Counter

API_KEY = "minh0313"
BASE_URL = "https://www.law.go.kr/DRF"


def fetch_text(endpoint, params):
    url = f"{BASE_URL}/{endpoint}?{urlencode(params)}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def fetch_json(endpoint, params):
    url = f"{BASE_URL}/{endpoint}?{urlencode(params)}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def search_laws_with_revision_type(revision_type="일부개정"):
    """특정 제개정구분의 법령 목록 조회"""
    print("=" * 70)
    print(f"[1] '{revision_type}' 법령 목록 조회")
    print("=" * 70)

    params = {
        "OC": API_KEY,
        "target": "law",
        "type": "JSON",
        "display": 20,
        "page": 1,
    }

    data = fetch_json("lawSearch.do", params)
    laws = data.get("LawSearch", {}).get("law", [])
    if isinstance(laws, dict):
        laws = [laws]

    # 일부개정만 필터
    filtered = [l for l in laws if revision_type in l.get("제개정구분명", "")]
    print(f"전체 {len(laws)}건 중 '{revision_type}' {len(filtered)}건")

    for law in filtered[:5]:
        print(f"  - {law.get('법령명한글')} | MST: {law.get('법령일련번호')} | {law.get('제개정구분명')} | {law.get('공포일자')}")

    return filtered


def test_xml_detail(law_mst, law_name=""):
    """XML로 법령 본문 조회 - 제개정이유내용 + 개정문내용 + 조문제개정유형"""
    print()
    print("=" * 70)
    print(f"[2] XML 본문 조회: MST={law_mst} ({law_name})")
    print("=" * 70)

    params = {
        "OC": API_KEY,
        "target": "law",
        "MST": law_mst,
        "type": "XML",
    }

    xml_text = fetch_text("lawService.do", params)

    # --- 제개정이유내용 ---
    reason_match = re.search(r"<제개정이유내용>(.*?)</제개정이유내용>", xml_text, re.DOTALL)
    if reason_match:
        raw = reason_match.group(1)
        # CDATA 제거
        clean = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", raw, flags=re.DOTALL).strip()
        print(f"\n[제개정이유내용] 길이: {len(clean)} chars")
        print("-" * 50)
        print(clean[:3000])
        if len(clean) > 3000:
            print(f"\n... (총 {len(clean)}자)")
    else:
        print("\n[제개정이유내용] 없음")

    # --- 개정문내용 ---
    amend_match = re.search(r"<개정문내용>(.*?)</개정문내용>", xml_text, re.DOTALL)
    if amend_match:
        raw = amend_match.group(1)
        clean = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", raw, flags=re.DOTALL).strip()
        print(f"\n[개정문내용] 길이: {len(clean)} chars")
        print("-" * 50)
        print(clean[:3000])
        if len(clean) > 3000:
            print(f"\n... (총 {len(clean)}자)")
    else:
        print("\n[개정문내용] 없음")

    # --- 조문별 제개정유형 및 변경여부 ---
    articles_info = []
    # 조문번호, 조문제목, 조문제개정유형, 조문변경여부 추출
    article_blocks = re.findall(r"<조문단위>(.*?)</조문단위>", xml_text, re.DOTALL)
    for block in article_blocks:
        no_m = re.search(r"<조문번호>(.*?)</조문번호>", block)
        title_m = re.search(r"<조문제목>(.*?)</조문제목>", block, re.DOTALL)
        type_m = re.search(r"<조문제개정유형>(.*?)</조문제개정유형>", block)
        changed_m = re.search(r"<조문변경여부>(.*?)</조문변경여부>", block)

        no = no_m.group(1).strip() if no_m else ""
        title_raw = title_m.group(1).strip() if title_m else ""
        title = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", title_raw).strip()
        rev_type = type_m.group(1).strip() if type_m else ""
        changed = changed_m.group(1).strip() if changed_m else ""

        articles_info.append({
            "no": no,
            "title": title,
            "revision_type": rev_type,
            "changed": changed,
        })

    print(f"\n[조문 분석] 총 {len(articles_info)}개 조문")
    print("-" * 50)

    # 제개정유형 분포
    rev_types = [a["revision_type"] for a in articles_info if a["revision_type"]]
    if rev_types:
        print(f"[조문제개정유형 분포]: {dict(Counter(rev_types))}")

    changed_flags = [a["changed"] for a in articles_info if a["changed"]]
    if changed_flags:
        print(f"[조문변경여부 분포]: {dict(Counter(changed_flags))}")

    # 변경된 조문 목록
    changed_articles = [a for a in articles_info if a["changed"] == "Y" or a["revision_type"]]
    if changed_articles:
        print(f"\n[변경/개정 조문 목록] ({len(changed_articles)}건)")
        for a in changed_articles[:20]:
            print(f"  조{a['no']} {a['title'][:30]} | 유형: {a['revision_type']} | 변경: {a['changed']}")

    return {
        "reason": reason_match.group(1) if reason_match else None,
        "amendment": amend_match.group(1) if amend_match else None,
        "articles": articles_info,
        "changed_articles": changed_articles,
    }


if __name__ == "__main__":
    print("법제처 API - 제개정이유내용 테스트 (XML)")
    print("=" * 70)

    if len(sys.argv) > 1:
        mst = sys.argv[1]
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        test_xml_detail(mst, name)
    else:
        # 일부개정 법령 검색
        laws = search_laws_with_revision_type("일부개정")

        if not laws:
            print("일부개정 법령이 없어서 전체에서 첫 번째 법령으로 테스트")
            laws = search_laws_with_revision_type("")
            if not laws:
                # 아무거나 가져오기
                data = fetch_json("lawSearch.do", {"OC": API_KEY, "target": "law", "type": "JSON", "display": 5})
                laws = data.get("LawSearch", {}).get("law", [])
                if isinstance(laws, dict):
                    laws = [laws]

        if laws:
            # 첫 번째 일부개정 법령으로 테스트
            test_law = laws[0]
            mst = test_law.get("법령일련번호", "")
            name = test_law.get("법령명한글", "")
            result = test_xml_detail(mst, name)

            # 결과 요약
            print("\n" + "=" * 70)
            print("[결과 요약]")
            print("=" * 70)
            has_reason = result["reason"] is not None
            has_amendment = result["amendment"] is not None
            print(f"  제개정이유내용: {'있음' if has_reason else '없음'}")
            print(f"  개정문내용: {'있음' if has_amendment else '없음'}")
            print(f"  전체 조문: {len(result['articles'])}건")
            print(f"  변경/개정 조문: {len(result['changed_articles'])}건")

            if has_reason:
                print(f"\n  => 제개정이유 내용에서 개정 대상 조문을 파싱하면")
                print(f"     조문개정 검토대상 자동 분류 가능!")

    print("\n테스트 완료!")
