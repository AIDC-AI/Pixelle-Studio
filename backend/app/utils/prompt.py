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

from typing import Optional, List


def get_full_message(user_message: str, file_urls: List[str], file_names: List[str]) -> str:
        # Build initial user message with file context
    full_user_message = user_message.strip()
    
    if file_names:
        full_user_message += "\n\n## User Uploaded Files:\n"
        full_user_message += "These files are in your current working directory. Access them directly by filename:\n"
        for name in file_names:
            full_user_message += f"- {name}\n"
    elif file_urls:
        full_user_message += "\n\n## User Uploaded Files:\n"
        full_user_message += "These files are in your current working directory. Access them directly by filename:\n"
        for url in file_urls:
            filename = url.split("/")[-1]
            full_user_message += f"- {filename}\n"
    return full_user_message