# Copyright (C) 2026 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import List, Dict, Any, Tuple

from pydantic_core.core_schema import NoneSchema
from app.llm.llm import LLM
from app.llm.components import Message,Tool,ToolCall
from openai import AsyncOpenAI, OpenAI,omit
from enum import Enum
import os
import logging
from typing import Generator
import inspect

logger = logging.getLogger(__name__)


class LLMMode(Enum):
    SYNC = "sync"
    ASYNC = "async"


class AihubLLM:
    """
    Generic OpenAI-compatible LLM wrapper.
    NOTE: api_key and base_url are required parameters. Environment variable
    fallback (OPENAI_API_KEY / OPENAI_BASE_URL) has been removed — LLM
    credentials are now configured per-user via the web UI Settings panel.
    """

    def __init__(self, model, api_key: str = None, base_url: str = None, mode=LLMMode.SYNC, stream: bool = True):
        if api_key is None:
            logger.warning("[AihubLLM] No api_key provided – caller should pass user-configured credentials")
        if mode == LLMMode.SYNC:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.mode = mode
        self.stream = stream
        self.model = model

    def generate(self, messages: list[Message], tools: list[Tool] | None = None, **kwargs) -> Message | Generator[Message, None, None]:
        # kwargs['temperature'] = omit
        # kwargs['top_p'] = omit
        openai_messages, filtered_kwargs = self._format_input_message(messages, **kwargs)
        response = self.client.chat.completions.create(model=self.model, messages=openai_messages, tools=tools, **filtered_kwargs)
        return self._format_output_message(response)

    async def async_generate(self, messages: list[Message], tools: list[Tool] | None = None, **kwargs) -> Message | Generator[Message, None, None]:
        openai_messages, filtered_kwargs = self._format_input_message(messages, **kwargs)
        response = await self.client.chat.completions.create(model=self.model, messages=openai_messages, tools=tools, **filtered_kwargs)
        return self._format_output_message(response)

    def _format_input_message(self, messages: list[Message], **kwargs) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        parameters = inspect.signature(self.client.chat.completions.create).parameters
        filtered_kwargs = {key: value for key, value in kwargs.items() if key in parameters}
        openai_messages = [message.format_to_openai() for message in messages]
        return openai_messages, filtered_kwargs

    def _format_output_message(self, completion) -> Message:
        """Formats the full non-streaming response into a Message object.

       Args:
           completion: The raw response from the OpenAI API.

       Returns:
           Message: A Message object containing the final response.
       """
        content = completion.choices[0].message.content or ''
        if hasattr(completion.choices[0].message, 'reasoning_content'):
            reasoning_content = completion.choices[0].message.reasoning_content or ''
        else:
            reasoning_content = ''
        tool_calls = None
        if completion.choices[0].message.tool_calls:
            tool_calls = [
                ToolCall(id=tool_call.id,
                         index=getattr(tool_call, 'index', idx),
                         type=tool_call.type,
                         arguments=tool_call.function.arguments,
                         tool_name=tool_call.function.name) for idx, tool_call in enumerate(completion.choices[0].message.tool_calls)
            ]
        
        # Log token usage
        if hasattr(completion, 'usage') and completion.usage:
            try:
                from app.utils.session_logger_simple import estimate_cost
                cost = estimate_cost(self.model, completion.usage.prompt_tokens, completion.usage.completion_tokens)
                logger.info(
                    f"[TokenUsage][aihub_llm] model={self.model} "
                    f"prompt={completion.usage.prompt_tokens} completion={completion.usage.completion_tokens} "
                    f"total={completion.usage.total_tokens} cost=${cost:.6f}"
                )
            except Exception as e:
                logger.debug(f"Failed to log LLM usage: {e}")
        
        return Message(role='assistant',
                       content=content,
                       reasoning_content=reasoning_content,
                       tool_calls=tool_calls,
                       id=completion.id,
                       prompt_tokens=completion.usage.prompt_tokens,
                       completion_tokens=completion.usage.completion_tokens)
