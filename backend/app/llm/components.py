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

# Copyright (c) Alibaba, Inc. and its affiliates.
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Union

import json
from typing_extensions import Literal, Required, TypedDict


class ToolCall(TypedDict, total=False):
    id: str = 'default_id'
    index: int = 0
    type: str = 'function'
    tool_name: str = ''
    arguments: str = '{}'


class Tool(TypedDict, total=False):
    server_name: str = None

    tool_name: Required[str]

    description: Required[str]

    parameters: Dict[str, Any] = dict()


@dataclass
class Message:
    role: Literal['system', 'user', 'assistant', 'tool']

    content: Union[str, List[Dict[str, str]]] = ''

    tool_calls: List[ToolCall] = field(default_factory=list)

    tool_call_id: Optional[str] = None

    name: Optional[str] = None

    # needed for output
    reasoning_content: str = ''

    # request id
    id: str = ''

    # continue generation mode
    partial: bool = False
    prefix: bool = False

    # usage
    completion_tokens: int = 0
    prompt_tokens: int = 0
    api_calls: int = 1

    def to_dict(self):
        return asdict(self)

    def to_dict_clean(self):
        raw_dict = asdict(self)
        if raw_dict.get('tool_calls'):
            for idx, tool_call in enumerate(raw_dict['tool_calls']):
                try:
                    if tool_call['arguments']:
                        json.loads(tool_call['arguments'])
                except Exception:
                    tool_call['arguments'] = '{}'
                raw_dict['tool_calls'][idx] = {
                    'id': tool_call['id'],
                    'type': tool_call['type'],
                    'function': {
                        'name': tool_call['tool_name'],
                        'arguments': tool_call['arguments'],
                    }
                }
        required = ['content', 'role']
        rm = ['completion_tokens', 'prompt_tokens', 'api_calls']
        return {key: value for key, value in raw_dict.items() if (value or key in required) and key not in rm}

    def format_to_openai(self) -> Dict[str, Any]:
        if isinstance(self.content, str):
            self.content = self.content.strip()
        message = self.to_dict_clean()
        return message
