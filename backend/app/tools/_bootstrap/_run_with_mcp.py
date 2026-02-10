"""
Auto-generated wrapper: injects call_tool() then runs the target Python script.
Usage: python _run_with_mcp.py <target_script.py> [args...]
"""
import os
import sys
import runpy

def _inject_call_tool():
    """Load MCP bootstrap to make call_tool available as a builtin."""
    bootstrap_path = os.environ.get("_MCP_BOOTSTRAP")
    if not bootstrap_path or not os.path.exists(bootstrap_path):
        return
    
    try:
        # Execute bootstrap in a namespace
        ns = {}
        exec(open(bootstrap_path).read(), ns)
        
        # If bootstrap defined call_tool, inject it into builtins
        # so it's available in ALL subsequently executed scripts
        if "call_tool" in ns:
            import builtins
            builtins.call_tool = ns["call_tool"]
    except Exception as e:
        print(f"[MCP Wrapper] Warning: Failed to load bootstrap: {e}", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python _run_with_mcp.py <script.py> [args...]", file=sys.stderr)
        sys.exit(1)
    
    # Inject call_tool into builtins
    _inject_call_tool()
    
    # Fix sys.argv so the target script sees the correct arguments
    target_script = sys.argv[1]
    sys.argv = sys.argv[1:]
    
    # Run the target script
    runpy.run_path(target_script, run_name="__main__")
