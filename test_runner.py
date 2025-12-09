import asyncio
import sys
import json
from pathlib import Path

# Add parent directory to path to import from backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.execution.runner import run_script

async def test_runner():
    # Use relative path from project root
    project_root = Path(__file__).parent
    script_path = project_root / "scripts" / "eb33bc6f-ba3d-49a4-9f3f-4ea305892886.py"
    cwd = str(script_path.parent)
    
    print(f"Testing runner with script: {script_path}")
    print(f"Working directory: {cwd}")
    print("=" * 60)
    
    async for log in run_script(script_path, cwd):
        print(f"[{log.get('type', 'unknown')}] {json.dumps(log)}")
    
    print("=" * 60)
    print("Runner test completed!")

if __name__ == "__main__":
    asyncio.run(test_runner())
