#!/usr/bin/env python3
"""Rebuild all CPCS bibliography indexes from the paper.

This is a narrow wrapper around the authoritative parser and writer in
``build_cpcs_rag.py`` so that the standalone reference build and the complete
RAG build always produce byte-identical Markdown, JSON, CSV, and TSV indexes.
"""

from __future__ import annotations

import json

from build_cpcs_rag import MD_PATH, parse_reference_records, write_reference_indices


def main() -> None:
    text = MD_PATH.read_text(encoding="utf-8")
    records = parse_reference_records(text)
    if not records:
        raise ValueError("No reference records were parsed from the paper")
    source_ids = [record["source_id"] for record in records]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Duplicate source IDs were parsed from the bibliography")
    write_reference_indices(records)
    print(
        json.dumps(
            {
                "paper": str(MD_PATH),
                "reference_count": len(records),
                "references_with_urls": sum(bool(record.get("urls")) for record in records),
                "total_urls": sum(len(record.get("urls", [])) for record in records),
                "first_source_id": source_ids[0],
                "last_source_id": source_ids[-1],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
