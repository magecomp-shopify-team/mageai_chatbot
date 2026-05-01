#!/usr/bin/env python3
"""Wipe and re-index all documents for a given app."""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Re-index all documents for an app")
    parser.add_argument("--app-id", required=True, help="App ID to re-index")
    parser.add_argument("--chunk-size", type=int, default=450, help="Chunk size in words")
    args = parser.parse_args()

    from src.manager.doc_manager import wipe_and_reindex_app

    print(f"Re-indexing app: {args.app_id} ...")
    total = await wipe_and_reindex_app(args.app_id)
    print(f"Done. {total} chunks indexed.")


if __name__ == "__main__":
    asyncio.run(main())
