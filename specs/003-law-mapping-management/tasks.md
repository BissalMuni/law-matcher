# 003-law-mapping-management Tasks

Spec: 003-law-mapping-management (Law Mapping Management)
Generated: 2026-03-01

## Overview

All core features (US1-US6) are already implemented. Tasks focus on:
- API retry logic with exponential backoff (moleg_client.py)
- Error message Korean localization across backend services and API endpoints
- Article deletion mapping impact warnings (frontend + backend)
- Last-law deletion warning reinforcement (US3)

## Phase 1: API Resilience

| ID | Task | File(s) | US | Deps |
|----|------|---------|----|------|
| T001 | Add retry logic to moleg_client with max 2 retries, exponential backoff (1s -> 2s), 30s timeout | `backend/external/moleg_client.py` | Cross-cutting | - |

## Phase 2: Error Message Korean Localization [P]

All tasks in this phase are parallel and independent of each other. They depend only on T001.

| ID | Task | File(s) | US | Deps |
|----|------|---------|----|------|
| T002 [P] | Localize law sync error messages to Korean: "법제처에서 해당 법령을 찾을 수 없습니다" (law not found), "법제처 서버 응답이 지연되고 있습니다" (API timeout) | `backend/services/law_sync_service.py` | [US1] | T001 |
| T003 [P] | Localize ordinance mapping error messages to Korean: "이 상위법령은 이미 연결되어 있습니다" (duplicate mapping) | `backend/services/ordinance_service.py` | [US1] | T001 |
| T004 [P] | Localize error responses in laws API endpoint to Korean | `backend/api/v1/laws.py` | [US1] | T001 |
| T005 [P] | Localize error responses in articles API endpoint to Korean | `backend/api/v1/articles.py` | [US5] | T001 |
| T006 [P] | Localize mapping-related error responses in ordinances API endpoint to Korean | `backend/api/v1/ordinances.py` | [US1] [US3] | T001 |

## Phase 3: Mapping Consistency Warnings

| ID | Task | File(s) | US | Deps |
|----|------|---------|----|------|
| T007 | Add article deletion mapping impact warning in article_service: when an article is deleted, return list of affected mappings | `backend/services/article_service.py` | [US5] | T005 |
| T008 | Add article deletion warning UI in OrdinanceDetail: show confirmation dialog listing affected mappings before article deletion | `frontend/src/pages/OrdinanceDetail.tsx` | [US5] | T007 |

## Phase 4: Polish

| ID | Task | File(s) | US | Deps |
|----|------|---------|----|------|
| T009 | Reinforce last-law deletion warning: when removing the final parent law mapping from an ordinance, show stronger confirmation with impact description | `backend/api/v1/ordinances.py`, `frontend/src/pages/OrdinanceDetail.tsx` | [US3] | T006, T008 |
| T010 | Ensure no_parent_law flag auto-clears when a parent law mapping is added (FR-006a) and verify Korean error message is returned on failure | `backend/services/ordinance_service.py` | [US1] [US4] | T003 |

## Phase 5: US6 자동추천 실패 복구 (P3)

| ID | Task | File(s) | US | Deps |
|----|------|---------|----|------|
| T011 | Add suggestion calculation failure recovery: catch exceptions, return partial results with error flag, log failures for monitoring | `backend/services/article_service.py` | [US6] | T007 |
| T012 | Localize suggestion API error responses to Korean: "자동 추천 계산 중 오류가 발생했습니다. 수동으로 매핑해 주세요" | `backend/api/v1/articles.py` | [US6] | T011 |

## Dependencies & Execution Order

```
T001 (API retry logic)
 |
 +---> T002 [P] (law_sync_service Korean messages)
 +---> T003 [P] (ordinance_service Korean messages) ---> T010 (no_parent_law auto-clear)
 +---> T004 [P] (laws API Korean responses)
 +---> T005 [P] (articles API Korean responses) ---> T007 (article deletion impact) ---> T008 (deletion warning UI)
 +---> T006 [P] (ordinances API Korean responses) ---> T009 (last-law deletion warning)
                                                         ^
                                                         |
                                                   T008 -+
 T007 ---> T011 (suggestion failure recovery) ---> T012 (suggestion Korean errors)
```

**Critical path:** T001 -> T005 -> T007 -> T008 -> T009

## Summary

| Metric | Count |
|--------|-------|
| Total tasks | 12 |
| Parallel tasks | 5 (T002-T006) |
| Backend tasks | 10 |
| Frontend tasks | 2 |
| New files | 0 |
| Modified files | 8 |
