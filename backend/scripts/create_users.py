"""
사용자 생성 스크립트
관리자와 일반 사용자 계정을 생성합니다.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from backend.core.database import async_session
from backend.core.security import get_password_hash
from backend.models.user import User


async def create_users():
    """관리자와 사용자 계정 생성"""
    async with async_session() as db:
        # Check if admin already exists
        result = await db.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()

        if not admin:
            admin = User(
                email="admin@localhost",
                username="admin",
                hashed_password=get_password_hash("admin12123456"),
                full_name="관리자",
                user_type="GENERAL",  # GENERAL = 관리자
                is_active=True,
            )
            db.add(admin)
            print("관리자 계정 생성됨: admin / admin12123456")
        else:
            # Update password if exists
            admin.hashed_password = get_password_hash("admin12123456")
            print("관리자 계정 비밀번호 업데이트됨: admin / admin12123456")

        # Check if default user exists
        result = await db.execute(select(User).where(User.username == "user"))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email="user@localhost",
                username="user",
                hashed_password=get_password_hash("user1212"),
                full_name="사용자",
                user_type="DEPARTMENT",  # DEPARTMENT = 부서 사용자
                is_active=True,
            )
            db.add(user)
            print("사용자 계정 생성됨: user / user1212")
        else:
            # Update password if exists
            user.hashed_password = get_password_hash("user1212")
            print("사용자 계정 비밀번호 업데이트됨: user / user1212")

        await db.commit()
        print("\n완료!")


if __name__ == "__main__":
    asyncio.run(create_users())
