users 테이블:

id	username	email	full_name	user_type	is_active
1	admin	admin@localhost	관리자	GENERAL	✓
2	user	user@localhost	사용자	DEPARTMENT	✓
로그인 정보:

관리자: admin / admin12123456
사용자: user / user1212
비번은 어디 기록되어 잇나
Bash Query users password hash
IN
cd "d:\Coding\law-matcher" && docker exec law-matcher-db-1 psql -U lawmatcher -d lawmatcher -c "SELECT id, username, LEFT(hashed_password, 50) as hashed_password_preview FROM users ORDER BY id;"

OUT
 id | username |              hashed_password_preview               
----+----------+----------------------------------------------------
  1 | admin    | $2b$12$INr3gGZB/dXRYld3D0hhXuEYZEGEC2VEUjJY4QmLhqa
  2 | user     | $2b$12$DhQ4SHyzdZesBVDZhxAIEOvZEgx9rJ3s8IehjNKa2KV
(2 rows)
비밀번호는 users 테이블의 hashed_password 컬럼에 bcrypt 해시로 저장됩니다.

id	username	hashed_password (암호화됨)
1	admin	$2b$12$INr3gGZB/dXRYld3D0hhXu...
2	user	$2b$12$DhQ4SHyzdZesBVDZhxAIEO...
실제 비밀번호 (평문):

admin: admin12123456
user: user1212
비밀번호는 create_users.py 스크립트에서 설정되었습니다.