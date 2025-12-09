# Docker 기본 명령어

docker-compose up -d      # 컨테이너 시작 (백그라운드)
docker-compose down       # 컨테이너 중지 및 삭제
docker-compose build      # 이미지 빌드

# 마이그레이션 생성
docker-compose run --rm backend alembic -c backend/alembic.ini revision --autogenerate -m "description"

# 마이그레이션 적용
docker-compose run --rm backend alembic -c backend/alembic.ini upgrade head