# 시스템 점검모드 사용 가이드

## 점검모드 켜기

```bash
curl -X POST http://localhost:8000/api/v1/admin/maintenance \
  -H "X-Admin-Password: admin0313" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "message": "System is under maintenance."}'
```

- `message`는 선택사항이며, 생략 시 기본 메시지("시스템 정비 중입니다. 잠시 후 다시 접속해 주세요.")가 표시됩니다.

## 점검모드 끄기

```bash
curl -X POST http://localhost:8000/api/v1/admin/maintenance \
  -H "X-Admin-Password: admin0313" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

## 점검모드 상태 확인

```bash
curl http://localhost:8000/api/v1/admin/maintenance
```

응답 예시:
```json
{
  "enabled": true,
  "message": "시스템 업데이트 중입니다. 14시까지 완료 예정입니다."
}
```

## 점검모드 우회 접속

관리자가 점검 중에도 시스템을 확인해야 할 때 URL에 `?bypass=admin` 파라미터를 추가합니다.

```
http://localhost:3000/?bypass=admin
```

## 동작 방식

| 구분 | 설명 |
|------|------|
| 저장소 | Redis (`law_matcher:maintenance_mode` 키) |
| 백엔드 | 미들웨어가 모든 API 요청을 가로채서 503 반환 |
| 프론트엔드 | 앱 로딩 시 상태 조회 후 정비중 페이지 표시 |
| 허용 경로 | `/health`, `/api/v1/admin/maintenance` |
