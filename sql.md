# DB 접속

```bash
docker-compose exec db psql -U lawmatcher -d lawmatcher
```


 List of relations
 Schema |          Name          | Type  |   Owner
--------+------------------------+-------+------------
 public | alembic_version        | table | lawmatcher
 public | amendment_reviews      | table | lawmatcher
 public | departments            | table | lawmatcher
 public | law_amendments         | table | lawmatcher
 public | law_changes            | table | lawmatcher
 public | law_snapshots          | table | lawmatcher
 public | laws                   | table | lawmatcher
 public | ordinance_articles     | table | lawmatcher
 public | ordinance_law_mappings | table | lawmatcher
 public | ordinances             | table | lawmatcher
(10 rows)

## List of relations

| Schema | Name | Type | Owner |
|--------|------|------|-------|
| public | alembic_version | table | lawmatcher |
| public | amendment_reviews | table | lawmatcher |
| public | departments | table | lawmatcher |
| public | law_amendments | table | lawmatcher |
| public | law_changes | table | lawmatcher |
| public | law_snapshots | table | lawmatcher |
| public | laws | table | lawmatcher |
| public | ordinance_articles | table | lawmatcher |
| public | ordinance_law_mappings | table | lawmatcher |
| public | ordinances | table | lawmatcher |
