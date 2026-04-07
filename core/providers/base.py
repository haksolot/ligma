from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, model: str, messages: list[dict]) -> dict[str, Any]:
        pass

    @abstractmethod
    async def list_models(self) -> list[str]:
        pass

    @abstractmethod
    async def get_model_info(self, model: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass
