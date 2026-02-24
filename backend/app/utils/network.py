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
