#!/usr/bin/env python3
"""Bulk import all .md and .txt files from a folder into an app."""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk import documents into an app")
    parser.add_argument("--app-id", required=True, help="Target app ID")
    parser.add_argument("--folder", required=True, help="Folder containing .md/.txt files")
    parser.add_argument("--chunk-size", type=int, default=450, help="Chunk size in words")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        print(f"Error: folder '{folder}' does not exist")
        sys.exit(1)

    files = list(folder.glob("*.md")) + list(folder.glob("*.txt"))
    if not files:
        print("No .md or .txt files found in folder.")
        sys.exit(0)

    from src.pipeline.indexer import index_file

    print(f"Importing {len(files)} file(s) into app '{args.app_id}' ...")
    total_chunks = 0
    for f in files:
        result = await index_file(f, args.app_id, chunk_size=args.chunk_size)
        status = "SKIPPED" if result.skipped else f"{result.chunks_indexed} chunks"
        print(f"  {f.name}: {status}")
        total_chunks += result.chunks_indexed

    print(f"\nDone. {total_chunks} total chunks indexed.")


if __name__ == "__main__":
    asyncio.run(main())
