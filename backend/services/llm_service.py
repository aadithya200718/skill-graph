import json
import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

_gemini_model = None


def _get_gemini_model():
    global _gemini_model
    if _gemini_model is None:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        _gemini_model = genai.GenerativeModel(settings.gemini_model)
    return _gemini_model


async def _call_ollama(prompt: str, system: str = "") -> str:
    url = f"{settings.ollama_base_url}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")


async def _call_gemini(prompt: str, system: str = "") -> str:
    model = _get_gemini_model()
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    response = await model.generate_content_async(full_prompt)
    return response.text


async def _check_ollama_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


async def generate(prompt: str, system: str = "") -> str:
    provider = settings.llm_provider.lower()

    if provider == "ollama":
        if await _check_ollama_available():
            try:
                return await _call_ollama(prompt, system)
            except Exception as exc:
                logger.warning("Ollama call failed, falling back to Gemini: %s", exc)
        else:
            logger.info("Ollama not available, using Gemini fallback")

    if not settings.gemini_api_key:
        raise RuntimeError(
            "No LLM available. Ollama is not running and GEMINI_API_KEY is not set."
        )
    return await _call_gemini(prompt, system)


async def generate_json(prompt: str, system: str = "") -> dict[str, Any]:
    json_system = (
        "You must respond with valid JSON only. No markdown fences, no extra text. "
        "Output raw JSON."
    )
    full_system = f"{json_system}\n{system}" if system else json_system

    raw = await generate(prompt, full_system)

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM response as JSON: %s", cleaned[:200])
        return {}
