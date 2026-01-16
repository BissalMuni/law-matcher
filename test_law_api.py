import requests
import json

url = "http://www.law.go.kr/DRF/lawSearch.do"
params = {
    "OC": "minh0313",
    "target": "law",
    "type": "JSON",
    "query": "지방세법 시행령"
}

response = requests.get(url, params=params)
data = response.json()

with open("law.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"저장 완료: law.json ({len(data.get('LawSearch', {}).get('law', []))}건)")
