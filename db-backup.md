# Database Backup Guide

## DB 정보

- **Database**: PostgreSQL 15
- **User**: lawmatcher
- **Password**: lawmatcher
- **Database Name**: lawmatcher
- **Container Name**: db

---

## 백업 명령어

### 1. Docker 컨테이너에서 직접 백업

```bash
# 전체 데이터베이스 백업 (SQL 형식)
docker-compose exec db pg_dump -U lawmatcher lawmatcher > backup.sql


# 압축 백업 (권장)
docker-compose exec db pg_dump -U lawmatcher lawmatcher | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 2. Custom 형식 백업 (대용량 DB 권장)

```bash
# Custom 형식 (-Fc): 압축 + 병렬 복원 지원
docker-compose exec db pg_dump -U lawmatcher -Fc lawmatcher > backup_$(date +%Y%m%d_%H%M%S).dump
```

### 3. 특정 테이블만 백업

```bash
# 특정 테이블 백업
docker-compose exec db pg_dump -U lawmatcher -t 테이블명 lawmatcher > table_backup.sql
```

---

## 복원 명령어

### 1. SQL 파일 복원

```bash
# SQL 파일 복원
docker-compose exec -T db psql -U lawmatcher lawmatcher < backup.sql

# 압축 파일 복원
gunzip -c backup.sql.gz | docker-compose exec -T db psql -U lawmatcher lawmatcher
```

### 2. Custom 형식 복원

```bash
# .dump 파일 복원
docker-compose exec -T db pg_restore -U lawmatcher -d lawmatcher < backup.dump

# 기존 데이터 삭제 후 복원
docker-compose exec -T db pg_restore -U lawmatcher -d lawmatcher --clean < backup.dump
```

---

## Windows 환경

Windows CMD/PowerShell에서는 날짜 형식이 다릅니다:

```powershell
# PowerShell
docker-compose exec db pg_dump -U lawmatcher lawmatcher > backup_$(Get-Date -Format "yyyyMMdd_HHmmss").sql

# CMD (간단한 이름)
docker-compose exec db pg_dump -U lawmatcher lawmatcher > backup.sql
```

---

## 자동 백업 스크립트 예시

### Linux/Mac (backup.sh)

```bash
#!/bin/bash
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
docker-compose exec -T db pg_dump -U lawmatcher lawmatcher | gzip > "$BACKUP_DIR/backup_$TIMESTAMP.sql.gz"
echo "Backup completed: backup_$TIMESTAMP.sql.gz"
```

### Windows (backup.bat)

```batch
@echo off
set BACKUP_DIR=.\backups
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
if not exist %BACKUP_DIR% mkdir %BACKUP_DIR%
docker-compose exec -T db pg_dump -U lawmatcher lawmatcher > "%BACKUP_DIR%\backup_%TIMESTAMP%.sql"
echo Backup completed!
```
