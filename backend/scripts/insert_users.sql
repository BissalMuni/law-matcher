-- users 테이블 초기 데이터 삽입
-- 비밀번호는 bcrypt로 해시되어야 하므로 Python 스크립트(create_users.py) 사용 권장

-- 기존 데이터 확인 후 삽입 (PostgreSQL)
INSERT INTO users (id, username, email, full_name, user_type, is_active, created_at, updated_at)
VALUES
    (1, 'admin', 'admin@localhost', '관리자', 'GENERAL', true, NOW(), NOW()),
    (2, 'user', 'user@localhost', '사용자', 'DEPARTMENT', true, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    username = EXCLUDED.username,
    email = EXCLUDED.email,
    full_name = EXCLUDED.full_name,
    user_type = EXCLUDED.user_type,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- 시퀀스 재설정 (id 자동 증가 값 조정)
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));

-- 참고: 비밀번호 설정
-- admin: admin12123456
-- user: user1212
-- 비밀번호 해시는 Python 스크립트로 생성해야 합니다:
--   python backend/scripts/create_users.py
