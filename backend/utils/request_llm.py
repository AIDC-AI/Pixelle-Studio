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

import argparse
import json
import asyncio
import os
from openai import AsyncOpenAI

# # Read LLM configuration from environment variables

async def main(req_path: str):
    client = AsyncOpenAI()
    with open(req_path, "r") as f:
        req = json.load(f)
    print(f"request: {req}")
    response = await client.chat.completions.create(**req)
    generation = response.choices[0].message.content
    print(generation)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=str, required=True)
    args = parser.parse_args()
    asyncio.run(main(args.request))
