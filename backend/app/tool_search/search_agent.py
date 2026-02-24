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

import json
import select
import os
from typing import List, Dict, Any, Set, Tuple
from openai import AsyncOpenAI

from app.llm_adapter import DEFAULT_MODEL
from app.tool_search.qwen3_embedding import Qwen3Embedding
import os
import numpy as np
from app.mcp_aggregator import MCPServerConfig, MCPServer
from app.tool_search.tool_embedding_data import ToolInfo, EmbeddingDatas
import asyncio
from typing import List
import threading
import torch
from app.tool_search.profiling import profiling

current_dir = os.path.dirname(os.path.abspath(__file__))


class SearchAgent:
    #     system_prompt = """
    # You are an expert mcp tool search agent.
    # Your goal is to search for the most relevant tools based on the user's request.

    # You have access to a list of MCP tools descriptions that will be provided as below format:
    # ['tool 1 description', 'tool 2 description', 'tool 3 description', ...].Use them as needed.
    # disassemble the tool call steps if need to call the tools from user's request ,find the most relevant tools descriptions as a list.
    # Return the most relevant tools descriptions index of the tools descriptions list.
    # multiple indexs can be returned if need to call the tools from user's request,format as below: [0, 2, 3].
    # single index can be returned if only one tool is needed to be called,format as below: [1].
    # """
    system_prompt = """
# Role
You are an intent understanding and decomposition expert.
## Functionality
Your task is to understand the user's intent based on their input text, and decompose it into several steps. Each step is a description of a tool that needs to be called. Decompose the user input into a list of tool descriptions corresponding to multiple steps. If the user input does not mention the need to call any tools, return an empty list.
## Response Format
Return a list as a JSON list string, format: ["query weather by date", "use calculator to compute value", "Feishu tool - search department ID by department name, supports name or pinyin search"]. If no tool calls needed, return empty list: [].
## Examples
User input: query today's weather
Response: ["query weather by date"]
User input: use calculator to compute 10+20
Response: ["use calculator to compute value"]
User input: "send a text message to Zhang San, content: 'hello'"
Response: ["look up phone number in contacts by name", "send SMS via messaging platform"]
User input: where is the capital of China
Response: []
## Constraints
Format must be a JSON list string, response must not contain irrelevant content.
"""

    def __init__(self):
        SearchAgent.instance = self
        self.client = AsyncOpenAI()
        self.model = DEFAULT_MODEL
        model_path = os.getenv("EMODEL_PATH", "Qwen3-Embedding-0.6B")
        self.qwen3_embedding = Qwen3Embedding(model_path, device=torch.device("cuda" if torch.cuda.is_available() else "cpu"))
        print(f"SearchAgent:load embedding model {model_path} successfully")
        self.embedding_db_dir = os.path.join(current_dir, "db")
        self.tools_embedding_info: EmbeddingDatas = self.load_embedding_data(self.embedding_db_dir)
        print(f"SearchAgent:load embedding data successfully,tool size:{len(self.tools_embedding_info.embedding_indexs)}")

        self._locker = threading.Lock()

    def load_embedding_data(self, embedding_db_dir: str) -> EmbeddingDatas:
        #tools_embeddings: Dict[str, List[ToolEmbeddingData]] = {}
        aggr_embedding_info: EmbeddingDatas = None
        for file in os.listdir(embedding_db_dir):
            if file.endswith(".json"):
                server_name = os.path.basename(file).split(".")[0]
                with open(os.path.join(embedding_db_dir, file), "r") as f:
                    try:
                        json_data = json.load(f)
                        embedding_info = EmbeddingDatas(**json_data)
                        if aggr_embedding_info is None:
                            aggr_embedding_info = embedding_info
                        else:
                            aggr_embedding_info.tool_infos.update(embedding_info.tool_infos)
                            aggr_embedding_info.embeddings = np.concatenate([aggr_embedding_info.embeddings, embedding_info.embeddings], axis=0)
                            aggr_embedding_info.embedding_indexs.extend(embedding_info.embedding_indexs)
                        print(f"SearchAgent :load embedding data from {file} successfully,tool size: {len(embedding_info.tool_infos.values())}")
                    except Exception as e:
                        print(f"SearchAgent :load embedding data from {file} failed,error: {e}")
                        raise e

        if aggr_embedding_info is None:
            return EmbeddingDatas()
        return aggr_embedding_info

    @profiling
    async def search_tools(self, user_message: str, all_mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Search tools based on user message.
        TODO(lingyue.ly)the all_mcp_tools is a list of tools,duplicated tool names will be occurred in the list,should be organized as a dict of tool list by server name,need to be fixed when the framework is stable.
        """
        system_prompt = self.generate_system_prompt(all_mcp_tools)
        response = await self.client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{
                "role": "system",
                "content": self.system_prompt
            }, {
                "role": "user",
                "content": user_message
            }],
        )
        # Log token usage
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            from app.utils.session_logger_simple import estimate_cost
            cost = estimate_cost(DEFAULT_MODEL, usage.prompt_tokens, usage.completion_tokens)
            print(
                f"[TokenUsage][tool_search] model={DEFAULT_MODEL} "
                f"prompt={usage.prompt_tokens} completion={usage.completion_tokens} "
                f"total={usage.total_tokens} cost=${cost:.6f}"
            )
        res_content = response.choices[0].message.content
        print(f"SearchAgent response: {res_content}")
        # Convert string list to Python list object
        try:
            res_list = json.loads(res_content)
            for i, estimated_desc in enumerate(res_list):
                print(f"SearchAgent response,step id: {i},estimated tool description:{estimated_desc}")
        except Exception as e:
            print(
                f"SearchAgent :response content is not a valid list string,return all list of mcp tools descriptions index,system prompt: {system_prompt},user message: {user_message}"
            )
            res_list = []
        retrieve_results = await self._retrieve_tools(res_list)
        if len(retrieve_results) == 0:
            print(f"WARNING SearchAgent:no retrieve results,return all list of mcp tools descriptions")
            return all_mcp_tools

        selected_tools: List[Dict[str, Any]] = []
        selected_tool_names: Set[str] = set()
        for i, retrieve_result in enumerate(retrieve_results):
            for server_name, tool_name, score in retrieve_result:
                #because the input all_mcp_tools have no server name,so we only find the tool by tool name in the all_mcp_tools.
                for tool in all_mcp_tools:
                    if tool['name'] == tool_name and tool['name'] not in selected_tool_names:
                        selected_tools.append(tool)
                        selected_tool_names.add(tool['name'])
                        #for debug,print the selected tool name,server name,score,step id,estimated tool description
                        print("------------------------------------------SELECTED TOOL---------------------------------------------------")
                        print(f"SearchAgent:selected tool name: {tool['name']},server name: {server_name},score: {score},step id: {i}")
                        print(f"SearchAgent:estimated tool description: {res_list[i]}")
                        print(f"SearchAgent:configured tool description: {tool['description']}")
                        print("------------------------------------------SELECTED TOOL---------------------------------------------------")
        return selected_tools

    def generate_system_prompt(self, all_mcp_tools: List[List[Dict[str, Any]]]) -> str:
        return self.system_prompt
        # descriptions = [tool['description'] for tool in all_mcp_tools]
        # return self.system_prompt + "\n" + "Here are the all MCP tools descriptions:\n" + json.dumps(
        #     descriptions, ensure_ascii=False)

    @profiling
    async def embedding_tools(self, mcp_server_config: MCPServerConfig, all_mcp_tools: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        embeddings_tools_indexs: List[int] = []
        embeddings_tools_descs: List[str] = []
        for i, server in enumerate(mcp_server_config.servers):
            if server.enabled:
                tool_names = [tool_info.tool_name for tool_infos in self.tools_embedding_info.tool_infos.values() for tool_info in tool_infos]
                for ii, tool in enumerate(all_mcp_tools[i]):
                    if server.name not in self.tools_embedding_info.tool_infos or tool['name'] not in tool_names:
                        fixed_description = f"{server.name}:{tool['description']}"

                        tool_index = i << 16 | ii
                        embeddings_tools_indexs.append(tool_index)
                        embeddings_tools_descs.append(fixed_description)

        if embeddings_tools_descs:
            changed_server_names: Set[str] = set()
            tools_embeddings = await self._text_embedding(embeddings_tools_descs)
            with self._locker:
                for i, svc_tool_index in enumerate(embeddings_tools_indexs):
                    server_index = svc_tool_index >> 16
                    tool_index = svc_tool_index & 0xFFFF
                    server_name = mcp_server_config.servers[server_index].name
                    tool = all_mcp_tools[server_index][tool_index]
                    tool_embedding = ToolInfo(tool_name=tool['name'], tool_description=embeddings_tools_descs[i])
                    if server_name not in self.tools_embedding_info.tool_infos:
                        self.tools_embedding_info.tool_infos[server_name] = []
                    self.tools_embedding_info.tool_infos[server_name].append(tool_embedding)
                    self.tools_embedding_info.embedding_indexs.append(self._create_embedding_index(server_name, tool['name']))
                    changed_server_names.add(server_name)
                self.tools_embedding_info.embeddings = np.concatenate(
                    [self.tools_embedding_info.embeddings, tools_embeddings],
                    axis=0) if self.tools_embedding_info.embeddings is not None else np.stack(tools_embeddings)

            for server_name in changed_server_names:
                #save the embedding data to the file separately
                server_embedding_indices = self._get_embedding_idx_by_server(server_name)
                embedding_db_file = os.path.join(self.embedding_db_dir, f"{server_name}.json")
                server_embeddings = self.tools_embedding_info.embeddings[server_embedding_indices, :]
                server_embedding_indexs = [self.tools_embedding_info.embedding_indexs[i] for i in server_embedding_indices]
                sever_embedding_info = EmbeddingDatas(tool_infos={server_name: self.tools_embedding_info.tool_infos[server_name]},
                                                      embedding_indexs=server_embedding_indexs,
                                                      embeddings=server_embeddings)
                with open(embedding_db_file, "w") as f:
                    json.dump(sever_embedding_info.model_dump(), f, indent=4, ensure_ascii=False)
                print(f"SearchAgent :save embedding data to {len(changed_server_names)} files of {server_name} successfully")

    def _create_embedding_index(self, server_name: str, tool_name: str) -> str:
        return f"{server_name}||||{tool_name}"

    def _get_tool_names(self, index_str: str) -> Tuple[str, str]:
        server_name, tool_name = index_str.split("||||")
        return server_name, tool_name

    def _get_embedding_idx_by_server(self, server_name: str) -> List[int]:
        return [i for i, index in enumerate(self.tools_embedding_info.embedding_indexs) if self._get_tool_names(index)[0] == server_name]

    @profiling
    async def _text_embedding(self, text: str | List[str]) -> List[List[float]]:

        def embed(text: str | List[str]) -> np.ndarray:
            tokens = self.qwen3_embedding.preprocess_text(text)
            embedding_list = self.qwen3_embedding.batch_text_embedding(tokens)
            return embedding_list

        return await asyncio.to_thread(embed, text)

    @profiling
    async def _retrieve_tools(self, query_tool_descs: List[str], topk: int = 3) -> List[List[Tuple[str, str, float]]]:
        if len(query_tool_descs) == 0:
            return []
        retrieve_results: List[List[Tuple[str, str, float]]] = []
        query_embeddings = await self._text_embedding(query_tool_descs)
        with self._locker:
            similarities = self.qwen3_embedding.batch_calculate_similarity(query_embeddings, self.tools_embedding_info.embeddings)
        topk_indices = np.argsort(similarities, axis=-1)[:, ::-1][:, :topk]
        topk_scores = similarities[np.arange(similarities.shape[0])[:, None], topk_indices]
        print(f"topk_indices: {topk_indices},topk_scores: {topk_scores}")
        for i in range(similarities.shape[0]):
            results_for_query = []
            for j, score in zip(topk_indices[i], topk_scores[i]):
                server_name, tool_name = self._get_tool_names(self.tools_embedding_info.embedding_indexs[j])
                results_for_query.append((server_name, tool_name, float(score)))
            retrieve_results.append(results_for_query)
        return retrieve_results


async def main():
    mcp_servers = [
        MCPServer(id="0", name="DingTalk-MCP", enabled=True, type="sse", config={"url": "http://localhost:8000/api/tools"}),
        MCPServer(id="1", name="Feishu-MCP", enabled=True, type="sse", config={"url": "http://localhost:8001/api/tools"}),
        MCPServer(id="2", name="WeChat-MCP", enabled=True, type="sse", config={"url": "http://localhost:8002/api/tools"})
    ]
    mcp_server_config = MCPServerConfig(servers=mcp_servers)
    mcp_tools_jstr = """
    [
    [{
        "name": "searchUser",
        "description": "Search DingTalk contacts userId by name.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "queryWord": {
                    "type": "string",
                    "description": "Search keyword, can be user name, pinyin or English name."
                },
                "offset": {
                    "type": "number",
                    "description": "Pagination offset, starting from 0"
                },
                "size": {
                    "type": "number",
                    "description": "Page size, max 50"
                },
                "fullMatchField": {
                    "type": "number",
                    "description": "Exact match flag, 1: exact match user name."
                }
            },
            "required": [
                "queryWord"
            ]
        },
        "server_id": "mcp_1765266621102_s2whf91p1",
        "server_url": "https://dashscope.aliyuncs.com/api/v1/mcps/dingtalk-mcp/sse",
        "server_type": "sse"
    },
    {
        "name": "getUserDetailByUserId",
        "description": "Query user details - get detailed user info by userId, including unionId.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": {
                    "type": "string",
                    "description": "User's userId."
                },
                "language": {
                    "type": "string",
                    "description": "Language. * **zh_CN**: Chinese (default) * **en_US**: English"
                }
            },
            "required": [
                "userid"
            ]
        },
        "server_id": "mcp_1765266621102_s2whf91p1",
        "server_url": "https://dashscope.aliyuncs.com/api/v1/mcps/dingtalk-mcp/sse",
        "server_type": "sse"
    },
    {
        "name": "getUserIdByMobile",
        "description": "Get userId by mobile phone number.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mobile": {
                    "type": "string",
                    "description": "Mobile phone number"
                }
            },
            "required": [
                "mobile"
            ]
        },
        "server_id": "mcp_1765266621102_s2whf91p1",
        "server_url": "https://dashscope.aliyuncs.com/api/v1/mcps/dingtalk-mcp/sse",
        "server_type": "sse"
    }
    ],
    [{
        "name": "searchDepartment",
        "description": "Search department ID by name, supports name or pinyin search",
        "inputSchema": {
            "type": "object",
            "properties": {
                "queryWord": {
                    "type": "string",
                    "description": "Department name or department name pinyin"
                },
                "offset": {
                    "type": "number",
                    "description": "Page number, default 0"
                },
                "size": {
                    "type": "number",
                    "description": "Page size, default 10, max 100"
                }
            },
            "required": [
                "queryWord",
                "offset",
                "size"
            ]
        },
        "server_id": "mcp_1765266621102_s2whf91p1",
        "server_url": "https://dashscope.aliyuncs.com/api/v1/mcps/dingtalk-mcp/sse",
        "server_type": "sse"
    },
    {
        "name": "listSubDepartments",
        "description": "Get basic info list of sub-departments under specified department",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dept_id": {
                    "type": "number",
                    "description": "Parent department ID, omit to get root department sub-departments, root ID is 1"
                },
                "language": {
                    "type": "string",
                    "description": "Contact language, zh_CN(Chinese) or en_US(English), default zh_CN"
                }
            },
            "required": []
        },
        "server_id": "mcp_1765266621102_s2whf91p1",
        "server_url": "https://dashscope.aliyuncs.com/api/v1/mcps/dingtalk-mcp/sse",
        "server_type": "sse"
    }],
    [{
        "name": "sendNotice",
        "description": "Send work notification message, supports markdown message type",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid_list": {
                    "type": "string",
                    "description": "Recipient UserID list, comma-separated, max 5000"
                },
                "dept_id_list": {
                    "type": "string",
                    "description": "Recipient department ID list, comma-separated (optional)"
                },
                "to_all_user": {
                    "type": "boolean",
                    "description": "Send to all users (optional, default false)"
                },
                "msg.markdown.title": {
                    "type": "string",
                    "description": "Markdown message title"
                },
                "msg.markdown.text": {
                    "type": "string",
                    "description": "Markdown message content"
                }
            },
            "required": [
                "agent_id",
                "msg.msgtype",
                "msg.markdown.title",
                "msg.markdown.text"
            ]
        },
        "server_id": "mcp_1765266621102_s2whf91p1",
        "server_url": "https://dashscope.aliyuncs.com/api/v1/mcps/dingtalk-mcp/sse",
        "server_type": "sse"
    },
    {
        "name": "sendServiceWindowMessage",
        "description": "Send service window individual message",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {
                    "type": "string",
                    "description": "UseruserId"
                },
                "accountId": {
                    "type": "string",
                    "description": "Service window account ID"
                },
                "messageTitle": {
                    "type": "string",
                    "description": "Message title"
                },
                "messageContent": {
                    "type": "string",
                    "description": "Message content in markdown format"
                }
            },
            "required": [
                "userId",
                "accountId",
                "messageTitle",
                "messageContent"
            ]
        },
        "server_id": "mcp_1765266621102_s2whf91p1",
        "server_url": "https://dashscope.aliyuncs.com/api/v1/mcps/dingtalk-mcp/sse",
        "server_type": "sse"
    },    
    {
        "name": "sendDINGMessageByRobot",
        "description": "Robot sends DING message",
        "inputSchema": {
            "type": "object",
            "properties": {
                "remindType": {
                    "type": "string",
                    "description": "DING message type. 1: in-app DING, 2: SMS DING, 3: phone DING; default 1."
                },
                "receiverUserIdList": {
                    "type": "array",
                    "description": "Recipient userId list. In-app DING max 200 recipients per call. SMS/phone DING max 20 recipients.",
                    "items": {
                        "type": "string"
                    }
                },
                "content": {
                    "type": "string",
                    "description": "DING message content."
                }
            },
            "required": [
                "remindType",
                "receiverUserIdList",
                "content"
            ]
        },
        "server_id": "mcp_1765266621102_s2whf91p1",
        "server_url": "https://dashscope.aliyuncs.com/api/v1/mcps/dingtalk-mcp/sse",
        "server_type": "sse"
    }    
    ]
    ]
"""

    all_mcp_tools = json.loads(mcp_tools_jstr)
    flattened_all_mcp_tools = [tool for server_tools in all_mcp_tools for tool in server_tools]
    await search_agent.embedding_tools(mcp_server_config=mcp_server_config, all_mcp_tools=all_mcp_tools)
    estimated_tool_descs = ["Search userId by name.", "Send notification message to someone"]
    retrieve_results = await search_agent._retrieve_tools(query_tool_descs=estimated_tool_descs, topk=3)
    for i, estimated_tool_desc in enumerate(estimated_tool_descs):
        print(
            f"estimated_tool_desc: {estimated_tool_desc},retrival info:server name: {retrieve_results[i][0][0]},tool name: {retrieve_results[i][0][1]},retrival score: {retrieve_results[i][0][2]}"
        )
    # user_message = "Use DingTalk robot to send a notification to user Huijin, content: 'meeting at 4pm tomorrow'"
    # select_tools = await search_agent.search_tools(user_message=user_message, all_mcp_tools=flattened_all_mcp_tools)
    # print(f"select tools size: {len(select_tools)}")
    # for tool in select_tools:
    #     print(f"select tool name: {tool['name']},tool description: {tool['description']}")


search_agent = SearchAgent()

if __name__ == "__main__":
    asyncio.run(main())
