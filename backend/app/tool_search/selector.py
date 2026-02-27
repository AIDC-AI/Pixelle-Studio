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

from typing import List, Dict, Any
import json


def format_tools_for_llm(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format tools for LLM tools parameter (OpenAI function calling format).
    
    Args:
        tools: List of tool definitions from MCP
        
    Returns:
        List of tools in OpenAI function calling format
    """
    formatted_tools = []

    for tool in tools:
        # Build enhanced description with output schema information
        description = tool['description']
        
        # Add output schema info if available
        if 'outputSchema' in tool and tool['outputSchema']:
            output_schema = tool['outputSchema']
            description += "\n\n**Output Format (MUST be followed exactly):**\n"
            description += f"```json\n{json.dumps(output_schema, indent=2)}\n```"
            
            # Add human-readable explanation if properties exist
            if 'properties' in output_schema:
                description += "\n\nReturned fields:\n"
                for prop_name, prop_info in output_schema['properties'].items():
                    prop_type = prop_info.get('type', 'any')
                    prop_desc = prop_info.get('description', '')
                    description += f"- `{prop_name}` ({prop_type}): {prop_desc}\n"
        
        # Convert MCP tool format to OpenAI function calling format
        formatted_tool = {
            "type": "function",
            "function": {
                "name": tool['name'],
                "description": description,
                "parameters": tool.get('inputSchema', {
                    "type": "object",
                    "properties": {},
                    "required": []
                })
            }
        }
        formatted_tools.append(formatted_tool)

    return formatted_tools
