import ollama
from .base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self):
        self.client = ollama.AsyncClient()

    async def chat(self, model: str, messages: list[dict]) -> dict:
        response = await self.client.chat(model=model, messages=messages)
        return response

    async def list_models(self) -> list[str]:
        try:
            response = await self.client.list()
            return [m.model for m in response.models]
        except Exception as e:
            print(f"[OllamaProvider] Could not list models: {e}")
            return []

    async def get_model_info(self, model: str) -> dict:
        try:
            info = await self.client.show(model=model)
            data = info.model_dump() if hasattr(info, "model_dump") else info

            parameters = data.get("parameters", "") or ""
            modelfile = data.get("modelfile", "") or ""
            modelinfo = data.get("modelinfo", {}) or {}

            context_limit = 2048
            for key, value in modelinfo.items():
                if key.endswith(".context_length") and isinstance(value, int):
                    context_limit = value
                    break
            else:
                import re

                match = re.search(r"num_ctx\s+(\d+)", str(parameters))
                if match:
                    context_limit = int(match.group(1))
                else:
                    match = re.search(r"PARAMETER\s+num_ctx\s+(\d+)", modelfile)
                    if match:
                        context_limit = int(match.group(1))

            return {
                "model": model,
                "context_limit": context_limit,
                "details": data.get("details", {}),
            }
        except Exception as e:
            print(f"[OllamaProvider] Could not fetch model info: {e}")
            return {"model": model, "context_limit": 2048, "details": {}}

    def get_provider_name(self) -> str:
        return "ollama"
