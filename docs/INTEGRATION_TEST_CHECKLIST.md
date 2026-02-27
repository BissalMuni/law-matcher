# Phase 4: Integration Testing 체크리스트

## ✅ 완료된 항목

### 1. Migration 실행 및 검증
- ✅ articles 테이블 생성 완료 (349개 레코드)
- ✅ article_changes 테이블 생성 완료
- ✅ ordinance_article_mappings 테이블 생성 완료
- ✅ 모든 인덱스, 제약조건, 외래키 정상 작동

### 2. Backend API 테스트
- ✅ ArticleService 초기화 정상
- ✅ 조문 목록 조회 (GET /articles) - 페이지네이션 정상
- ✅ 조문 상세 조회 (GET /articles/{id}) - 정상 작동
- ✅ 변경 이력 조회 (GET /articles/{id}/history) - 정상 작동
- ✅ Swagger UI 정상 작동 (http://localhost:8000/docs)

### 3. Frontend 구현 확인
- ✅ ArticleList.tsx 구현 완료
- ✅ ArticleDetail.tsx 구현 완료
- ✅ RevisionNeededList.tsx 구현 완료
- ✅ App.tsx 라우팅 설정 완료
- ✅ articleApi 전체 엔드포인트 구현 (Phase 4 포함)

---

## 🔄 수동 테스트 필요 항목

### Frontend 통합 테스트 (브라우저)

**준비:**
1. Backend 서버 실행 확인: http://localhost:8000
2. Frontend 서버 실행:
   ```bash
   cd frontend
   npm run dev
   # 또는 yarn dev
   ```
3. 브라우저에서 접속: http://localhost:5173

**테스트 시나리오:**

#### A. ArticleList 페이지 (/articles)
- [ ] 조문 목록이 표시되는지 확인
- [ ] 페이지네이션이 작동하는지 확인
- [ ] 법령 필터가 작동하는지 확인
- [ ] 검색 기능이 작동하는지 확인
- [ ] 연계 조례 필터가 작동하는지 확인
- [ ] 변경일 필터가 작동하는지 확인
- [ ] 동기화 버튼이 작동하는지 확인

#### B. ArticleDetail 페이지 (/articles/:id)
- [ ] 조문 상세 정보가 표시되는지 확인
- [ ] **조문 내용 탭**:
  - [ ] 조문 번호, 제목, 내용이 표시되는지 확인
  - [ ] 단락(paragraphs) JSONB 데이터가 표시되는지 확인
  - [ ] 소속 법령 정보가 표시되는지 확인
- [ ] **연계 조례 탭**:
  - [ ] 연계된 조례 목록이 표시되는지 확인
  - [ ] 연계 추가 버튼이 작동하는지 확인
  - [ ] 연계 삭제 버튼이 작동하는지 확인
- [ ] **변경 이력 탭**:
  - [ ] 변경 이력 목록이 표시되는지 확인
  - [ ] Diff HTML이 모달로 표시되는지 확인
  - [ ] 변경 유형(신규/수정/삭제) 태그가 표시되는지 확인

#### C. RevisionNeededList 페이지 (/revision-needed)
- [ ] 개정 검토 필요 조례 목록이 표시되는지 확인
- [ ] 통계 카드(검토 필요 건수, 조회 기간)가 표시되는지 확인
- [ ] 조회 기간 필터(7/30/90/180/365일)가 작동하는지 확인
- [ ] 담당부서 필터가 작동하는지 확인
- [ ] 조문 보기/조례 보기 링크가 작동하는지 확인

#### D. 메뉴 네비게이션
- [ ] MainLayout에 "조문조회" 메뉴가 추가되었는지 확인
- [ ] MainLayout에 "개정 검토 필요" 메뉴가 추가되었는지 확인
- [ ] 메뉴 클릭 시 해당 페이지로 이동하는지 확인

---

## 🎯 E2E 시나리오 테스트

### 시나리오 1: 법령 조문 동기화
1. [ ] Swagger UI에서 로그인 (POST /auth/login)
2. [ ] POST /articles/sync 호출 (특정 법령 ID 지정)
3. [ ] 응답 확인: synced_articles, created, updated, deleted, changes_detected
4. [ ] GET /articles로 새로 생성된 조문 확인
5. [ ] Frontend에서 ArticleList 새로고침 후 조문 확인

### 시나리오 2: 조문 변경 감지 및 이력 확인
1. [ ] 특정 조문의 내용을 직접 수정 (데이터베이스 또는 API)
2. [ ] 동기화 실행 (POST /articles/sync)
3. [ ] GET /articles/{id}/history로 변경 이력 확인
4. [ ] 변경 이력에 diff_html이 생성되었는지 확인
5. [ ] Frontend ArticleDetail 페이지에서 변경 이력 탭 확인
6. [ ] Diff 모달로 변경 내용 비교 확인

### 시나리오 3: 조례와 조문 연계 추가/삭제
1. [ ] ArticleDetail 페이지에서 "연계 조례" 탭 선택
2. [ ] "연계 추가" 버튼 클릭
3. [ ] 조례 선택 후 연계 사유 입력
4. [ ] 연계 생성 확인
5. [ ] 연계 삭제 버튼 클릭
6. [ ] 연계 삭제 확인

### 시나리오 4: 개정 검토 필요 조례 확인
1. [ ] 최근 변경된 조문이 있는 법령 확인
2. [ ] 해당 법령과 매핑된 조례 확인
3. [ ] GET /articles/revision-needed 호출
4. [ ] 응답에 해당 조례가 포함되었는지 확인
5. [ ] Frontend RevisionNeededList 페이지에서 확인
6. [ ] 조회 기간 필터 변경 시 결과 변경 확인

### 시나리오 5: Diff HTML 표시 확인
1. [ ] 변경 이력이 있는 조문 선택
2. [ ] ArticleDetail > 변경 이력 탭 선택
3. [ ] "변경 내용 보기" 버튼 클릭
4. [ ] Diff 모달이 표시되는지 확인
5. [ ] 추가/삭제/수정 부분이 색상으로 구분되는지 확인

---

## 📊 API 엔드포인트 체크리스트

### 기본 CRUD
- [x] GET /articles (조문 목록)
- [x] GET /articles/{id} (조문 상세)

### 연계 관리
- [ ] GET /articles/{id}/ordinances (연계 조례 목록)
- [ ] POST /articles/{id}/mappings (연계 추가)
- [ ] DELETE /articles/{id}/mappings/{mapping_id} (연계 삭제)

### 변경 이력
- [x] GET /articles/{id}/history (변경 이력)

### 동기화
- [ ] POST /articles/sync (조문 동기화)

### Phase 4 추가 API
- [ ] POST /articles/mappings/bulk (대량 매핑)
- [ ] GET /articles/revision-needed (개정 검토 필요 조례)
- [ ] GET /articles/auto-recommendations (자동 매핑 추천)

---

## 🔧 알려진 이슈 및 개선 사항

### 현재 상태
- ✅ Migration 완료
- ✅ Backend API 구현 완료
- ✅ Frontend 페이지 구현 완료
- ⏳ 실제 통합 테스트 필요 (사용자 수동 테스트)

### 다음 단계 (Phase 5)
- Celery Task 구현 (backend/tasks/article_sync.py)
- Celery Beat 스케줄 설정 (일 1회 오전 9시)
- 백그라운드 동기화 테스트

---

## 📝 테스트 완료 후 체크
- [ ] 모든 E2E 시나리오 테스트 완료
- [ ] 버그 발견 시 이슈 등록 및 수정
- [ ] Frontend-Backend 통합 정상 작동 확인
- [ ] Phase 5 (Celery 동기화) 진행 준비
