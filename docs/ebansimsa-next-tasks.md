# 입안심사 통합 — 다음 할 일 (로드맵)

작성일: 2026-05-27
브랜치: `feat/ebansimsa-integration`

지금까지: Phase 0~4(통합) + Monaco + 앱 구동 검증(A) + "입안심사 기준" 위키 뷰어 + 워크스페이스 조문 중심 재설계 완료.

## 우선순위 높음

- [ ] **기존 프로젝트 일괄 재분류** — 재설계(조문→단계 자동분류) 이전에 만든 프로젝트는 조문이 전부 본칙에 있음. 기존 프로젝트의 조문을 `classify_stage_key`로 재배치하는 액션(백엔드 `POST /projects/{id}/reclassify` + 프론트 버튼) 추가.
- [ ] **브라우저 실사용 검증** — 재설계 UI(조문 중심·기준 칩·칩클릭 분석·메타폼·단계이동)를 사람이 직접 클릭 확인. SSE AI 작성/검증 시각 동작 포함.
- [ ] **단계 확정(stage confirm) 워크플로우** — 단계별 `confirmed/stale` 상태 전이 UI. 확정 시 스냅샷 생성, 이전 단계 수정 시 후속 단계 `stale` 표시.

## 우선순위 중간

- [ ] **검증 결과 자동 영속·재현** — 칩 클릭 분석 결과를 `drafting_validations`에 저장 중이나, 재진입 시 저장된 판정을 칩/패널에 자동 표시(현재는 세션 캐시). `GET /sections/{id}/validations`로 초기 로드.
- [ ] **개정 diff 표시** — 개정 모드 `original_body` vs `body` 사이드바이사이드 비교(jsdiff 등). `change_type` 자동 산출(unchanged/modify).
- [ ] **AI 작성 결과 → 조문 저장 연결 매끄럽게** — 현재 "에디터에 적용" 후 수동 저장. 적용+저장 일괄, citations를 메시지로 영속.
- [ ] **본칙 sub-stage(동적 분류)** — 위원회·보조·출연 등 본칙 하위 분류(원본 ebansimsa의 main sub-stage). 현재 본칙 단일.

## 우선순위 낮음 / 정리

- [ ] **AI 판정 프롬프트 품질 튜닝** — 목적 조문이 목적규정 기준에 `na`로 나오는 등 판정 정확도 개선(원본과 동일 이슈). 2단계(관련성→판정) 적용 검토.
- [ ] **모델 설정 점검** — `DRAFTING_MODEL=claude-sonnet-4-20250514` 유효 동작 확인됨. 최신 모델로 갱신 검토(`claude-api` 스킬).
- [ ] **참고 조례(타 지자체) 기능** — `drafting_references` + 등록 조례를 참고로 끌어와 AI 컨텍스트 포함(`included_in_context`). 현재 모델만 있고 UI 미연결.
- [ ] **권한/감사** — drafting 엔드포인트에 인증 의존성 추가 검토(현재 무인증 컴퓨트). 작성자/검토자 기록.
- [ ] **PR 머지** — `feat/ebansimsa-integration` → `main`. 머지 전 `docs/ebansimsa-integration-plan.md` 기준 회귀 확인.

## 운영 메모

- frontend는 `src` 볼륨마운트라 코드 변경은 HMR 반영. **npm 의존성 추가 시에만** `docker compose build frontend` 필요(예: monaco, marked).
- backend는 `./backend` 볼륨마운트 + uvicorn(--reload 없음) → 코드 변경 시 `docker compose restart backend`.
- Alembic은 컨테이너에서 `docker compose exec -w /app/backend backend python -m alembic upgrade head`.
- wiki 기준 데이터(`backend/drafting/data/`)는 `.gitignore`의 `data/` 예외로 추적됨.
