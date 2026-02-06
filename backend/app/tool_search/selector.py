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

'''
Author: ai-business-hql ai.bussiness.hql@gmail.com
Date: 2025-12-22 11:11:34
LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
LastEditTime: 2025-12-22 14:57:28
FilePath: /mcp-workflow/backend/app/tool_search/selector.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from typing import List, Dict, Any
#from app.tool_search.search_agent import SearchAgent
import json




async def select_tools(user_message: str,
                 all_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Select relevant tools based on user message.
    
    Args:
        user_message: The user's request
        all_tools: List of all available tools
        
    Returns:
        List of selected tools
        
    Current Strategy:
        - Simple: Return all tools (phase 1)
        - Future: Use LLM or keyword matching to intelligently select tools
    """
    # Phase 1: Simple implementation - return all tools
    print(
        f"[Tool Search] Selecting tools for message: '{user_message[:50]}...'")
    print(f"[Tool Search] Available tools: {len(all_tools)}")
    print(f"[Tool Search] Strategy: Return all tools (simple)")
    # Filter out default mock tools if we have real MCP tools
    mcp_tools = [t for t in all_tools if 'server_url' in t]
    search_agent = SearchAgent.instance
    if mcp_tools:
        # Prefer MCP tools over mock tools
        selected_tools = await search_agent.search_tools(user_message=user_message, all_mcp_tools=all_tools)
        print(f"[Tool Search] Selected {len(selected_tools)} MCP tools")
    else:
        # Fallback to all tools including mocks
        selected_tools = all_tools
        print(
            f"[Tool Search] Selected {len(selected_tools)} tools (including mocks)")

    return selected_tools


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
