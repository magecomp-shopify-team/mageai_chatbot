#!/usr/bin/env python3
"""CLI: send a test ping to any configured provider."""
import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test an AI provider")
    parser.add_argument("--provider", required=True, help="Provider ID (e.g. anthropic, openai)")
    parser.add_argument("--model", default=None, help="Model ID (uses provider default if omitted)")
    parser.add_argument("--message", default="Hello! Reply in one sentence.", help="Test message")
    args = parser.parse_args()

    from src.ai.registry import init_registry, registry

    init_registry()

    if not registry.is_available(args.provider):
        print(f"Error: provider '{args.provider}' is not available. Check API key in .env")
        sys.exit(1)

    provider = registry.get(args.provider)
    models = await provider.list_models()
    model = args.model or (models[0] if models else "")
    if not model:
        print("Error: no model available for this provider")
        sys.exit(1)

    print(f"\nProvider : {provider.display_name}")
    print(f"Model    : {model}")
    print(f"Message  : {args.message}\n")

    start = time.perf_counter()
    result = await provider.complete(
        system_prompt="You are a helpful assistant.",
        messages=[{"role": "user", "content": args.message}],
        model=model,
        max_tokens=100,
    )
    latency = (time.perf_counter() - start) * 1000

    print(f"Reply    : {result.text}")
    print(f"Tokens   : {result.input_tokens} in / {result.output_tokens} out")
    print(f"Latency  : {latency:.0f} ms")


if __name__ == "__main__":
    asyncio.run(main())
