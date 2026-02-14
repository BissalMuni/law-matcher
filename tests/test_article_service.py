"""
Article Service Tests
"""
import pytest
from backend.services.article_service import ArticleService


class TestArticleService:
    """ArticleService 테스트"""

    def test_generate_content_hash(self):
        """SHA-256 해시 생성 테스트"""
        content = "이 법은 지방자치단체의 종류와 조직 및 운영에 관한 사항을 정함으로써..."

        hash_value = ArticleService.generate_content_hash(content)

        # 해시는 64자 hex 문자열이어야 함
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

        # 같은 내용은 같은 해시를 생성해야 함
        hash_value2 = ArticleService.generate_content_hash(content)
        assert hash_value == hash_value2

        # 다른 내용은 다른 해시를 생성해야 함
        different_content = "다른 내용"
        different_hash = ArticleService.generate_content_hash(different_content)
        assert hash_value != different_hash

    def test_generate_diff_html(self):
        """Diff HTML 생성 테스트"""
        old_content = """제1조(목적) 이 법은 지방자치단체의 종류와 조직을 정한다."""
        new_content = """제1조(목적) 이 법은 지방자치단체의 종류, 조직 및 운영을 정한다."""

        diff_html = ArticleService.generate_diff_html(old_content, new_content)

        # HTML이 생성되어야 함
        assert isinstance(diff_html, str)
        assert len(diff_html) > 0
        assert "<table" in diff_html
        assert "diff" in diff_html.lower()

    def test_generate_diff_html_empty(self):
        """빈 내용에 대한 Diff HTML 생성 테스트"""
        diff_html = ArticleService.generate_diff_html("", "새 내용")

        assert isinstance(diff_html, str)
        assert len(diff_html) > 0


# Async 테스트는 pytest-asyncio 필요
# @pytest.mark.asyncio
# async def test_detect_article_changes():
#     """조문 변경 감지 테스트"""
#     # DB 모킹 필요
#     pass
