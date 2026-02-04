#!/usr/bin/env python3
"""清理所有 shell 会话"""

import sys
from pathlib import Path
import asyncio

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.tools.shell_session import _session_manager

async def main():
    print("当前活跃的会话:")
    for sid, session in _session_manager.sessions.items():
        print(f"  - {sid}: {session.shell_type}, workdir={session.workdir}, alive={session.is_alive}")
    
    print("\n关闭所有会话...")
    for sid in list(_session_manager.sessions.keys()):
        await _session_manager._close_session(sid)
        print(f"  ✅ 关闭: {sid}")
    
    print("\n✅ 所有会话已清理")

if __name__ == "__main__":
    asyncio.run(main())

