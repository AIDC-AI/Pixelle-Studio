import argparse
import json
import asyncio
from openai import AsyncOpenAI


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
