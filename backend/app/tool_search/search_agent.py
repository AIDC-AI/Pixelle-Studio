import json
import select
from app.llm_adapter import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
from openai import AsyncOpenAI
from typing import List, Dict, Any, Set, Tuple
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
# 角色
你是一个意图理解和拆解专家。
## 功能
你的任务是根据用户的输入文本，理解用户的意图，并拆解成数个步骤，每个步骤是对需要调用一个工具的描述，将用户输入拆解成多个步骤对应的工具的描述的列表。如果用户输入中没有提到需要调用工具，则返回空列表。
## 回复格式
返回一个列表，列表格式为一个json list 字符串，格式为:["根据日期查询天气", "使用计算器计算数值", "飞书工具-据部门名称搜索部门ID，支持部门名称或拼音搜索"]，如无需工具调用则返回空列表，格式如：[]。
## 示例
用户输入：查询今天天气
回复：["根据日期查询天气"]
用户输入：使用计算器计算10+20
回复：["使用计算器计算数值"]
用户输入："给张三发送一条短信，短信内容是:'你好'"
回复：["根据姓名查询通讯录中的手机号码","通过短信平台发送短信"]
用户输入：中国的首都在哪里
回复：[]
## 限制
格式必须为json list 字符串，返回内容不包含无关内容。
"""

    def __init__(self):
        SearchAgent.instance = self
        self.client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        self.model = LLM_MODEL
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
            model=LLM_MODEL,
            messages=[{
                "role": "system",
                "content": self.system_prompt
            }, {
                "role": "user",
                "content": user_message
            }],
        )
        res_content = response.choices[0].message.content
        print(f"SearchAgent response: {res_content}")
        # 将字符串形式的list转换为Python list对象
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
        MCPServer(id="0", name="钉钉MCP", enabled=True, type="sse", config={"url": "http://localhost:8000/api/tools"}),
        MCPServer(id="1", name="飞书MCP", enabled=True, type="sse", config={"url": "http://localhost:8001/api/tools"}),
        MCPServer(id="2", name="微信MCP", enabled=True, type="sse", config={"url": "http://localhost:8002/api/tools"})
    ]
    mcp_server_config = MCPServerConfig(servers=mcp_servers)
    mcp_tools_jstr = """
    [
    [{
        "name": "searchUser",
        "description": "根据姓名搜索钉钉通讯录用户的userId。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "queryWord": {
                    "type": "string",
                    "description": "搜索关键词，可以是用户姓名、姓名拼音或英文名称。"
                },
                "offset": {
                    "type": "number",
                    "description": "分页偏移量，从0开始"
                },
                "size": {
                    "type": "number",
                    "description": "分页大小，最大50"
                },
                "fullMatchField": {
                    "type": "number",
                    "description": "是否精确匹配，1：精确匹配用户名称。"
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
        "description": "查询用户详情 - 根据userId获取用户的详细信息，包含用户的unionId。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid": {
                    "type": "string",
                    "description": "用户的userId。"
                },
                "language": {
                    "type": "string",
                    "description": "语言。 * **zh_CN** ：中文（默认值） * **en_US** ：英文"
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
        "description": "根据手机号获取用户的userId。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mobile": {
                    "type": "string",
                    "description": "手机号"
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
        "description": "根据部门名称搜索部门ID，支持部门名称或拼音搜索",
        "inputSchema": {
            "type": "object",
            "properties": {
                "queryWord": {
                    "type": "string",
                    "description": "部门名称或者部门名称拼音"
                },
                "offset": {
                    "type": "number",
                    "description": "分页页码，默认0"
                },
                "size": {
                    "type": "number",
                    "description": "分页大小，默认10，最大100"
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
        "description": "获取指定部门的下一级子部门基础信息列表",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dept_id": {
                    "type": "number",
                    "description": "父部门ID，不传则获取根部门的子部门，根部门ID为1"
                },
                "language": {
                    "type": "string",
                    "description": "通讯录语言，zh_CN(中文)或en_US(英文)，默认zh_CN"
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
        "description": "发送工作通知消息，支持 markdown 消息类型",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userid_list": {
                    "type": "string",
                    "description": "接收人用户ID列表，用逗号分隔，最多5000人"
                },
                "dept_id_list": {
                    "type": "string",
                    "description": "接收部门ID列表，用逗号分隔（可选）"
                },
                "to_all_user": {
                    "type": "boolean",
                    "description": "是否发送给全员（可选，默认false）"
                },
                "msg.markdown.title": {
                    "type": "string",
                    "description": "markdown消息标题"
                },
                "msg.markdown.text": {
                    "type": "string",
                    "description": "markdown消息内容"
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
        "description": "发送服务窗单人消息",
        "inputSchema": {
            "type": "object",
            "properties": {
                "userId": {
                    "type": "string",
                    "description": "用户userId"
                },
                "accountId": {
                    "type": "string",
                    "description": "服务窗帐号ID"
                },
                "messageTitle": {
                    "type": "string",
                    "description": "消息标题"
                },
                "messageContent": {
                    "type": "string",
                    "description": "markdown格式的消息内容"
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
        "description": "机器人发送DING消息",
        "inputSchema": {
            "type": "object",
            "properties": {
                "remindType": {
                    "type": "string",
                    "description": "DING消息类型。1：应用内DING，2：短信DING，3：电话DING；默认值为1。"
                },
                "receiverUserIdList": {
                    "type": "array",
                    "description": "接收人userId列表。应用内DING消息，每次接收人不能超过200个。短信DING和电话DING，每次接收人不能超过20个。",
                    "items": {
                        "type": "string"
                    }
                },
                "content": {
                    "type": "string",
                    "description": "DING消息内容。"
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
    estimated_tool_descs = ["根据姓名查询用户ID。", "发送通知消息给某人"]
    retrieve_results = await search_agent._retrieve_tools(query_tool_descs=estimated_tool_descs, topk=3)
    for i, estimated_tool_desc in enumerate(estimated_tool_descs):
        print(
            f"estimated_tool_desc: {estimated_tool_desc},retrival info:server name: {retrieve_results[i][0][0]},tool name: {retrieve_results[i][0][1]},retrival score: {retrieve_results[i][0][2]}"
        )
    # user_message = "使用钉钉机器人给用户会锦发送一条通知消息，消息内容是:'明天下午4点有会'"
    # select_tools = await search_agent.search_tools(user_message=user_message, all_mcp_tools=flattened_all_mcp_tools)
    # print(f"select tools size: {len(select_tools)}")
    # for tool in select_tools:
    #     print(f"select tool name: {tool['name']},tool description: {tool['description']}")


search_agent = SearchAgent()

if __name__ == "__main__":
    asyncio.run(main())
