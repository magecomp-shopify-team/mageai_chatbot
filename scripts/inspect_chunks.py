#!/usr/bin/env python3
"""Inspect ChromaDB chunks for an app, optionally filtered by source file."""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect indexed chunks")
    parser.add_argument("--app-id", required=True, help="App ID")
    parser.add_argument("--file", default=None, help="Filter by source filename")
    parser.add_argument("--limit", type=int, default=5, help="Max chunks to display")
    args = parser.parse_args()

    import asyncio as _asyncio
    from src.core.chroma import get_or_create_collection

    collection = await _asyncio.to_thread(get_or_create_collection, args.app_id)
    where = {"source_file": args.file} if args.file else None
    results = await _asyncio.to_thread(
        lambda: collection.get(
            where=where, limit=args.limit, include=["documents", "metadatas"]
        )
    )

    ids = results.get("ids", [])
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])

    if not ids:
        print("No chunks found.")
        return

    print(f"\nApp: {args.app_id}  |  {len(ids)} chunk(s) shown\n")
    for id_, doc, meta in zip(ids, docs, metas):
        print(f"ID       : {id_}")
        print(f"Source   : {meta.get('source_file', '?')}  (chunk {meta.get('chunk_index', '?')}/{meta.get('total_chunks', '?')})")
        print(f"Indexed  : {meta.get('indexed_at', '?')[:19]}")
        print(f"Text     : {doc[:300]}{'...' if len(doc) > 300 else ''}")
        print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
