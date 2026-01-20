# PostgreSQL 접속 정보

## 접속 정보

| 항목     | 값                                       |
| -------- | ---------------------------------------- |
| Host     | `localhost` (외부) / `db` (Docker 내부)  |
| Port     | `5432`                                   |
| User     | `lawmatcher`                             |
| Password | `lawmatcher`                             |
| Database | `lawmatcher`                             |

## 접속 명령어

### Docker 컨테이너 내부에서 psql 접속

```bash
docker exec -it law-matcher-db-1 psql -U lawmatcher -d lawmatcher
```

### 외부에서 접속 (psql 설치 필요)

```bash
psql -h localhost -p 5432 -U lawmatcher -d lawmatcher
```

## Connection String

### 기본

```text
postgresql://lawmatcher:lawmatcher@localhost:5432/lawmatcher
```

### AsyncPG (Python용)

```text
postgresql+asyncpg://lawmatcher:lawmatcher@localhost:5432/lawmatcher
```
