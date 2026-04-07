import openai
from typing import Any
from .base import LLMProvider


class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat(self, model: str, messages: list[dict]) -> dict:
        response = await self.client.chat.completions.create(
            model=model, messages=messages
        )

        return {
            "message": {
                "role": response.choices[0].message.role,
                "content": response.choices[0].message.content,
            },
            "total_duration": getattr(response, "total_duration", None),
            "prompt_eval_count": getattr(response, "prompt_eval_count", None),
            "eval_count": response.usage.completion_tokens if response.usage else None,
            "model": model,
        }

    async def list_models(self) -> list[str]:
        try:
            response = await self.client.models.list()
            return [m.id for m in response.data]
        except Exception as e:
            print(f"[OpenRouterProvider] Could not list models: {e}")
            return []

    async def get_model_info(self, model: str) -> dict:
        try:
            response = await self.client.models.retrieve(model)
            return {
                "model": model,
                "context_limit": getattr(response, "context_window", 4096),
                "details": {"id": response.id, "created": response.created},
            }
        except Exception as e:
            print(f"[OpenRouterProvider] Could not fetch model info: {e}")
            return {"model": model, "context_limit": 4096, "details": {}}

    def get_provider_name(self) -> str:
        return "openrouter"
