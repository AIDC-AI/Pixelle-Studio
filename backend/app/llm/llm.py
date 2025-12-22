from abc import ABC, abstractmethod
from app.llm.components import Message,Tool

class LLM(ABC):

    @abstractmethod
    def generate(self, messages: list[Message],tools: list[Tool] | None = None) -> str:
        pass

    def async_generate(self, prompt: str) -> str:
        pass

    @abstractmethod
    def continue_generate(self, prompt: str) -> str:
        pass
