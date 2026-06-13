from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

T = TypeVar("T", bound=BaseModel)

_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_llm(
    prompt: str,
    system: str = "",
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    client = get_openai_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = await client.chat.completions.create(
        model=model or settings.openai_model,
        messages=messages,
        temperature=temperature if temperature is not None else settings.openai_temperature,
        max_tokens=max_tokens or settings.openai_max_tokens,
    )
    return response.choices[0].message.content


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_llm_structured(
    prompt: str,
    response_model: type[T],
    system: str = "",
    model: str | None = None,
    temperature: float | None = None,
) -> T:
    client = get_openai_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = await client.beta.chat.completions.parse(
        model=model or settings.openai_model,
        messages=messages,
        temperature=temperature if temperature is not None else settings.openai_temperature,
        response_format=response_model,
    )
    return response.choices[0].message.parsed
