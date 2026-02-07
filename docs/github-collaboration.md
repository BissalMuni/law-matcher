# GitHub 협업 흐름 정리

이 문서는 현재 사용하는 브랜치 `hd/dashboard` 기준으로, 작업부터 배포까지의 협업 흐름을 간단히 정리한 것입니다.

## 기본 흐름

1) 작업 브랜치(`hd/dashboard`)에서 코드 수정
2) 커밋 후 원격에 푸시
3) GitHub에서 Pull Request(PR) 생성
4) PR 리뷰/승인 후 `main`에 merge
5) 다음 작업 시작 전에 `main` 최신 변경사항을 pull

## 작업/배포 단계별 체크리스트

### 1. 작업 시작

```bash
git checkout hd/dashboard
git pull origin main
```

### 2. 작업 후 커밋/푸시

```bash
git status
git add .
git commit -m "작업 요약"
git push origin hd/dashboard
```

### 3. Pull Request 생성/병합

- GitHub에서 PR 생성 (base: `main`, compare: `hd/dashboard`)
- 리뷰/승인 후 `main`으로 merge

### 4. 다음 작업 전 최신화

```bash
git checkout main
git pull origin main
git checkout hd/dashboard
git merge main
```

## 참고

- `main` 직접 작업 금지, 항상 `hd/dashboard` 브랜치에서 작업
- PR 병합 후 로컬 `main`과 작업 브랜치를 최신 상태로 맞추기
