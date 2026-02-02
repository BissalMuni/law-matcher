# Docker 기본 명령어

## 컨테이너 시작 (백그라운드)

docker compose up -d

## 컨테이너 중지 및 삭제

docker compose down

## 이미지 빌드

docker compose build

## 빌드 후 시작 (백그라운드)

docker compose up -d --build

## 마이그레이션 생성

docker compose run --rm -w /app/backend backend alembic revision --autogenerate -m "description"

## 마이그레이션 적용

docker compose run --rm -w /app/backend backend alembic upgrade head
