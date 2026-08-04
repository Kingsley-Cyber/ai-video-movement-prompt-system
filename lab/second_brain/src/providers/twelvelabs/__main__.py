"""Command line access to authority-free TwelveLabs transport operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import (
    add_media,
    create_embedding,
    create_knowledge_store,
    doctor,
    search_all,
    upload_asset,
    wait_for_asset,
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    store = sub.add_parser("create-store")
    store.add_argument("name")
    store.add_argument("--description")
    upload = sub.add_parser("upload")
    upload.add_argument("media_type", choices=("video", "image", "audio"))
    upload_source = upload.add_mutually_exclusive_group(required=True)
    upload_source.add_argument("--url")
    upload_source.add_argument("--file", type=Path)
    add = sub.add_parser("add-media")
    add.add_argument("knowledge_store_id")
    add.add_argument("media_type", choices=("video", "image"))
    source = add.add_mutually_exclusive_group(required=True)
    source.add_argument("--url")
    source.add_argument("--file", type=Path)
    search = sub.add_parser("search")
    search.add_argument("knowledge_store_id")
    search.add_argument("query")
    search.add_argument("--page-size", type=int, default=50)
    embed = sub.add_parser("embed")
    embed.add_argument(
        "input_type", choices=("video", "audio", "text", "image", "multi_input")
    )
    embed.add_argument("--text")
    embed.add_argument("--asset-id")
    embed.add_argument("--image-asset-id", action="append", default=[])
    args = parser.parse_args(argv)
    if args.command == "doctor":
        result = doctor()
    elif args.command == "create-store":
        result = create_knowledge_store(args.name, description=args.description)
    elif args.command == "upload":
        created = upload_asset(
            media_type=args.media_type, url=args.url, file_path=args.file
        )
        result = wait_for_asset(created["id"])
    elif args.command == "add-media":
        result = add_media(
            args.knowledge_store_id,
            media_type=args.media_type,
            url=args.url,
            file_path=args.file,
        )
    elif args.command == "search":
        result = search_all(
            args.knowledge_store_id, args.query, page_size=args.page_size
        )
    else:
        result = create_embedding(
            args.input_type,
            text=args.text,
            asset_id=args.asset_id,
            image_asset_ids=args.image_asset_id,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
