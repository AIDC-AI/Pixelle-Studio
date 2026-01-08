import argparse
import json
import asyncio
from openai import AsyncOpenAI
LLM_BASE_URL = "https://REDACTED_BASE_URL_HOST/v1"
LLM_API_KEY = "REDACTED_API_KEY"
LLM_MODEL = "gemini-3-pro-preview"


async def main(req_path: str):
    client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
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
