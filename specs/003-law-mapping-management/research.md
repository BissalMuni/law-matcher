# Research: 003-law-mapping-management

**Date**: 2026-02-28
**Input**: spec.md

## 기존 구현 현황

### 구현 완료 (대부분 완성)

| User Story | 백엔드 | 프론트엔드 | 비고 |
|------------|--------|-----------|------|
| US1 상위법령 연결 추가 | ✅ 완료 | ✅ 완료 | API 검색 + 시스템 내 검색, 자동 법령 등록 |
| US2 상위법령 목록 조회 | ✅ 완료 | ✅ 완료 | Core Rule 적용 (공포일자 비교) |
| US3 연결 수정/삭제 | ✅ 완료 | ✅ 완료 | cascade 삭제 포함 |
| US4 상위법령 없음 표시 | ✅ 완료 | ✅ 완료 | no_parent_law 플래그 |
| US5 조문 단위 매핑 | ✅ 완료 | ✅ 완료 | ordinance_article_mappings, 일괄 저장 |
| US6 자동 추천 | ✅ 완료 | ✅ 완료 | Jaccard 유사도 기반 키워드 매칭 |

### 주요 코드 위치

| 구분 | 파일 | 비고 |
|------|------|------|
| Law ORM | `backend/models/law.py` | 법령 마스터 (25 필드) |
| Article ORM | `backend/models/article.py` | 조문 (content_hash 기반 변경 감지) |
| LawChange ORM | `backend/models/law_change.py` | 법령 변경 이력 |
| ArticleChange ORM | `backend/models/article_change.py` | 조문 변경 이력 (diff_html) |
| OrdinanceLawMapping ORM | `backend/models/ordinance_law_mapping.py` | 조례-법령 N:M |
| OrdinanceArticleMapping ORM | `backend/models/ordinance_article_mapping.py` | 조례-조문 N:M |
| LawSyncService | `backend/services/law_sync_service.py` | 1089줄, 법령 동기화+변경 감지 |
| ArticleService | `backend/services/article_service.py` | 590줄, 조문 동기화+해시 비교 |
| OrdinanceService | `backend/services/ordinance_service.py` | 매핑 CRUD (create/get/delete) |
| Laws API | `backend/api/v1/laws.py` | 15+ 엔드포인트 |
| Articles API | `backend/api/v1/articles.py` | 10+ 엔드포인트, 자동 추천 포함 |
| Ordinances API | `backend/api/v1/ordinances.py` | 상위법령/조문 매핑 엔드포인트 |
| 프론트 상세 | `frontend/src/pages/OrdinanceDetail.tsx` | 상위법령 탭 + 조문 매핑 |
| 프론트 조문 | `frontend/src/pages/ArticleList.tsx` | 조문 목록 |
| 프론트 조문상세 | `frontend/src/pages/ArticleDetail.tsx` | 조문 상세 + diff 뷰어 |
| 프론트 개정대상 | `frontend/src/pages/RevisionNeededList.tsx` | 개정 필요 조례 목록 |

### 핵심 아키텍처 패턴

#### 변경 감지 흐름
```
sync_articles_for_law()
  → moleg_client.get_law_detail(law.law_serial_no)
  → detect_article_changes():
      - 기존 content_hash vs 신규 content_hash 비교
      - ArticleChange 레코드 생성 (created/updated/deleted)
      - diff_html 생성 (difflib)
  → notify_affected_ordinances():
      - ordinance.needs_revision = True 설정
```

#### 법령 동기화 흐름 (SSE)
```
sync_all_laws_with_progress() [SSE 스트리밍]
  → _resolve_exact_match() [MST 직접 조회 or 이름 검색]
  → proclaimed_date/enforced_date/revision_type 비교
  → sync_articles_for_law() [조문 동기화 연계]
  → LawChange 레코드 저장
  → yield progress events
```

## 미비 사항 (보강 필요)

### 1. 에러 복구 부재
- 법제처 API 일시 장애 시 재시도 메커니즘 없음
- 동기화 중 부분 실패 시 배치 단위 롤백만 수행

### 2. 자동 추천 정확도
- US6: 현재 Jaccard 유사도 기반 키워드 매칭만 구현
- SC-003(적합률 70%) 달성 여부 미검증
- 향후 LLM 기반 의미 분석으로 개선 가능 (Constitution VIII 범위)

### 3. 조문 번호 변경 시 매핑 정합성
- 법령 개정으로 조문 번호가 변경되면 기존 매핑이 깨질 수 있음
- article_id(PK)로 연결되므로 조문 자체가 삭제/재생성되면 매핑 유실
- Edge case로 기록, 현재 cascading delete로 처리

### 4. 알림 시스템 부재
- needs_revision 플래그 설정만 수행
- 이메일/웹훅 등 능동적 알림 미구현

## 결론

**상위법령 연결 관리 기능은 완성 상태**이며, 보강 작업은:

1. **에러 복구**: API 재시도 로직 추가 (FR-008과 연관)
2. **에러 메시지 한국어화**: 매핑 중복, 법령 미발견 등
3. **조문 매핑 정합성 경고**: 조문 삭제 시 영향받는 매핑 알림
