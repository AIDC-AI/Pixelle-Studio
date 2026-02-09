"""
Network utility functions.
"""
import os
import socket


def get_local_ip() -> str:
    """
    Get the local IP address of this machine.
    
    Priority:
    1. EXTERNAL_IP environment variable (for Docker environments)
    2. Auto-detected local IP
    3. Fallback to 127.0.0.1
    """
    # Prefer external IP from env var (for Docker environments)
    external_ip = os.environ.get("EXTERNAL_IP")
    if external_ip:
        return external_ip
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


# Pre-computed value for convenience
LOCAL_IP = get_local_ip()
SERVER_PORT = 8001  # Default backend port
