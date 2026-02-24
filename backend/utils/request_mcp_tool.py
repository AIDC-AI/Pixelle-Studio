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

import argparse
import json
import asyncio
from app.mcp_client import call_tool, register_tool_server
from app.mcp_aggregator import MCPAggregator, MCPServerConfig, MCPServer
import os

async def main(config_path: str, tool_name: str, args_path: str):
    with open(config_path, "r") as f:
        config_dict = json.load(f)
    with open(args_path, "r") as f:
        args = json.load(f)
    mcp_server_config = MCPServerConfig(servers=[MCPServer(**config_dict)])
    mcp_aggregator = MCPAggregator()
    all_mcp_tools = await mcp_aggregator.fetch_tools_by_server(mcp_server_config)
    all_mcp_tools = all_mcp_tools[0]
    request_tool = None
    for tool in all_mcp_tools:
        if tool['name'] == tool_name:
            request_tool = tool
            break
    if request_tool is None:
        raise ValueError(f"Tool {tool_name} not found")
    register_tool_server(request_tool['name'], request_tool['server_url'], mcp_server_config.servers[0].type, mcp_server_config.servers[0].headers)
    result = await call_tool(request_tool['name'], args)
    result_json = json.dumps(result, ensure_ascii=False, indent=4)
    print(f"Tool {tool_name} result:")
    print(result_json)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path", type=str, required=True)
    parser.add_argument("--tool_name", type=str, default=None)
    parser.add_argument("--args_path", type=str, required=True)
    args = parser.parse_args()
    if args.tool_name is None:
        tool_name = os.path.basename(args.args_path).split("_")[1]
    else:
        tool_name = args.tool_name
    asyncio.run(main(args.config_path, tool_name, args.args_path))
