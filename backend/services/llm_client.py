"""
LLM Client 추상화 - III. 외부 의존 격리
3개 프로바이더(Claude, ChatGPT, Gemini)를 공통 인터페이스로 관리
"""
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.llm_provider import LlmProvider

logger = logging.getLogger(__name__)


@dataclass
class LlmResponse:
    """LLM 응답 데이터"""
    content: str  # LLM 응답 원문
    input_tokens: int
    output_tokens: int


class LlmClient(ABC):
    """LLM 클라이언트 공통 인터페이스"""

    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = settings.LLM_TIMEOUT

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str) -> LlmResponse:
        """LLM에 프롬프트를 전송하고 응답을 반환한다"""
        ...

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """마크다운 코드 펜스(```json ... ```) 제거"""
        import re
        stripped = re.sub(r'^```(?:json)?\s*\n?', '', text.strip())
        stripped = re.sub(r'\n?```\s*$', '', stripped)
        return stripped.strip()

    async def generate_with_retry(
        self, prompt: str, system_prompt: str, max_retries: int = 2
    ) -> LlmResponse:
        """JSON 파싱 실패 시 재시도 포함 호출"""
        last_error = None
        for attempt in range(max_retries):
            try:
                response = await self.generate(prompt, system_prompt)
                # 마크다운 코드 펜스 제거 후 JSON 파싱 검증
                response.content = self._strip_markdown_fences(response.content)
                json.loads(response.content)
                return response
            except json.JSONDecodeError as e:
                last_error = e
                content_preview = response.content[:200] if response.content else "(empty)"
                logger.warning(
                    f"LLM JSON 파싱 실패 (시도 {attempt + 1}/{max_retries}): {e} | "
                    f"응답 미리보기: {content_preview} | "
                    f"토큰: in={response.input_tokens}, out={response.output_tokens}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                last_error = e
                logger.error(f"LLM 호출 실패 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

        raise last_error


class ClaudeClient(LlmClient):
    """Anthropic Claude API 클라이언트 (커넥션 풀링)"""

    _client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(
                api_key=self.api_key,
                timeout=self.timeout,
            )
        return self._client

    async def generate(self, prompt: str, system_prompt: str) -> LlmResponse:
        client = self._get_client()
        response = await client.messages.create(
            model=self.model_name,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        return LlmResponse(
            content=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    async def close(self):
        if self._client is not None:
            await self._client.close()
            self._client = None


class ChatGptClient(LlmClient):
    """OpenAI ChatGPT API 클라이언트 (커넥션 풀링)"""

    _client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.AsyncOpenAI(
                api_key=self.api_key,
                timeout=self.timeout,
            )
        return self._client

    async def generate(self, prompt: str, system_prompt: str) -> LlmResponse:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=8192,
        )
        usage = response.usage
        return LlmResponse(
            content=response.choices[0].message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

    async def close(self):
        if self._client is not None:
            await self._client.close()
            self._client = None


class GeminiClient(LlmClient):
    """Google Gemini API 클라이언트"""

    async def generate(self, prompt: str, system_prompt: str) -> LlmResponse:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                max_output_tokens=8192,
            ),
        )
        # Gemini SDK는 동기 API — asyncio에서 실행
        response = await asyncio.to_thread(
            model.generate_content, prompt
        )
        # Gemini 토큰 사용량
        usage_meta = getattr(response, "usage_metadata", None)
        return LlmResponse(
            content=response.text,
            input_tokens=getattr(usage_meta, "prompt_token_count", 0) if usage_meta else 0,
            output_tokens=getattr(usage_meta, "candidates_token_count", 0) if usage_meta else 0,
        )

    async def close(self):
        pass  # Gemini SDK는 stateless — 별도 정리 불필요


# 프로바이더별 클라이언트 매핑
_CLIENT_MAP = {
    "claude": ClaudeClient,
    "chatgpt": ChatGptClient,
    "gemini": GeminiClient,
}


class LlmServiceUnavailableError(Exception):
    """LLM 서비스 사용 불가"""
    pass


async def get_active_llm_client(db: AsyncSession) -> tuple[LlmClient, LlmProvider]:
    """DB에서 활성 프로바이더를 조회하여 해당 클라이언트와 프로바이더 정보를 반환"""
    result = await db.execute(
        select(LlmProvider).where(LlmProvider.is_active == True).limit(1)
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise LlmServiceUnavailableError("활성화된 LLM 프로바이더가 없습니다. 관리자에게 문의하세요")

    import os
    # env 우선, DB fallback
    api_key = os.getenv(provider.api_key_env_name, "") or (provider.api_key or "")
    if not api_key:
        raise LlmServiceUnavailableError(
            f"LLM API 키가 설정되지 않았습니다 (환경변수: {provider.api_key_env_name}, DB: 미설정)"
        )

    client_class = _CLIENT_MAP.get(provider.provider_name)
    if not client_class:
        raise LlmServiceUnavailableError(
            f"지원하지 않는 프로바이더: {provider.provider_name}"
        )

    return client_class(api_key, provider.model_name), provider
