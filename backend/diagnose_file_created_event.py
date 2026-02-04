#!/usr/bin/env python3
"""诊断 file_created 事件问题"""

import sys
import json
from pathlib import Path

# 读取最新的会话日志
log_file = Path("/Users/shali.yx/Desktop/code/mcp-workflow/backend/logs/sessions/1/sess_02e2f84a.jsonl")

print(f"分析日志文件: {log_file}")
print("=" * 80)

events = []
with open(log_file, 'r') as f:
    for line in f:
        if line.strip():
            events.append(json.loads(line))

print(f"\n总事件数: {len(events)}")

# 查找 tool_result 事件
print("\n" + "=" * 80)
print("查找 shell_exec 的 tool_result:")
print("=" * 80)

for event in events:
    if event.get("event_type") == "tool_result" and event.get("tool") == "shell_exec":
        print(f"\n时间戳: {event['timestamp']}")
        print(f"Call ID: {event['call_id']}")
        print(f"状态: {event.get('status')}")
        
        # 解析 result
        result_str = event.get("result", "")
        if result_str.startswith("{"):
            try:
                result_data = json.loads(result_str)
                print(f"\n解析后的 result:")
                print(json.dumps(result_data, indent=2, ensure_ascii=False))
                
                # 检查 created_files
                created_files = result_data.get("created_files", [])
                print(f"\n✅ created_files 字段存在: {len(created_files)} 个文件")
                for file_info in created_files:
                    print(f"  - {file_info['name']} ({file_info['size']} bytes)")
                    print(f"    路径: {file_info['path']}")
            except Exception as e:
                print(f"解析失败: {e}")

# 查找 file_created 事件
print("\n" + "=" * 80)
print("查找 file_created 事件:")
print("=" * 80)

file_created_events = [e for e in events if e.get("event_type") == "file_created"]
if file_created_events:
    print(f"找到 {len(file_created_events)} 个 file_created 事件:")
    for event in file_created_events:
        print(f"  - {event.get('timestamp')}: {event.get('message', 'N/A')}")
else:
    print("❌ 没有找到 file_created 事件！")
    print("\n这说明 agent.py 中的 file_created 事件没有被记录到日志中。")
    print("可能的原因:")
    print("1. 事件是通过 yield 返回的，但没有被 session_logger 记录")
    print("2. 事件生成后，前端收到了但日志里没有记录")

# 检查事件顺序
print("\n" + "=" * 80)
print("事件时间线:")
print("=" * 80)

for event in events:
    event_type = event.get("event_type")
    timestamp = event.get("timestamp", "")
    
    if event_type == "message":
        role = event.get("role")
        content = event.get("content", "")[:50]
        print(f"{timestamp} | message ({role}): {content}...")
    elif event_type == "tool_call":
        tool = event.get("tool")
        print(f"{timestamp} | tool_call: {tool}")
    elif event_type == "tool_result":
        tool = event.get("tool")
        status = event.get("status")
        print(f"{timestamp} | tool_result: {tool} ({status})")
    elif event_type == "file_created":
        message = event.get("message", "")
        print(f"{timestamp} | ✅ file_created: {message}")
    elif event_type == "status":
        status = event.get("status")
        print(f"{timestamp} | status: {status}")

print("\n" + "=" * 80)
print("诊断完成")
print("=" * 80)

