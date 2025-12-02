import asyncio
import sys
import os
import json
from typing import AsyncGenerator

async def run_script(script_path: str, cwd: str) -> AsyncGenerator[dict, None]:
    """
    Runs a python script and yields logs/results.
    """
    env = os.environ.copy()
    # Ensure the backend directory is in PYTHONPATH so we can import mcp_client if needed
    # Or better, we install the package. For now, let's add the parent dir.
    env["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

    process = await asyncio.create_subprocess_exec(
        sys.executable, "-u", script_path,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )

    # Helper to read stream
    async def read_stream(stream, stream_name):
        while True:
            line = await stream.readline()
            if not line:
                break
            yield {"type": "log", "stream": stream_name, "content": line.decode().strip()}

    # We need to read both stdout and stderr concurrently
    # This is a bit complex with generators. 
    # Simplified approach: just read line by line from both?
    # Or use a task to gather them.
    
    # For simplicity in this demo, let's just loop and wait.
    # Actually, asyncio.gather is better but we want to yield.
    
    # Let's use a queue to aggregate outputs
    queue = asyncio.Queue()
    
    async def pipe_to_queue(stream, name):
        while True:
            line = await stream.readline()
            if not line:
                break
            await queue.put({"type": "log", "stream": name, "content": line.decode().strip()})
        
    stdout_task = asyncio.create_task(pipe_to_queue(process.stdout, "stdout"))
    stderr_task = asyncio.create_task(pipe_to_queue(process.stderr, "stderr"))
    
    # Yield items as they come in, until both streams are done
    while not (stdout_task.done() and stderr_task.done()):
        try:
            item = await asyncio.wait_for(queue.get(), timeout=0.1)
            yield item
        except asyncio.TimeoutError:
            # No items available, continue checking if tasks are done
            continue
    
    # Drain any remaining items in the queue after tasks complete
    while not queue.empty():
        item = queue.get_nowait()
        yield item
            
    # Wait for process to finish
    await process.wait()
    
    # Send the final result
    if process.returncode == 0:
        yield {"type": "result", "status": "success"}
    else:
        yield {"type": "result", "status": "error", "code": process.returncode}
