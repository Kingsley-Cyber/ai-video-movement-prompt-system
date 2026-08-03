"""Marengo 3.0 embedding transport."""

from __future__ import annotations

from typing import Any, Sequence

from .common import CREATE_REQUEST_OPTIONS, MARENGO_MODEL, build_client, to_plain


def create_embedding(
    input_type: str,
    *,
    text: str | None = None,
    asset_id: str | None = None,
    image_asset_ids: Sequence[str] | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    active = client or build_client()
    kwargs: dict[str, Any] = {
        "input_type": input_type,
        "model_name": MARENGO_MODEL,
        "request_options": CREATE_REQUEST_OPTIONS,
    }
    if input_type == "text":
        if not text:
            raise ValueError("text embedding requires text")
        kwargs["text"] = {"input_text": text}
    elif input_type in {"video", "audio", "image"}:
        if not asset_id:
            raise ValueError(f"{input_type} embedding requires asset_id")
        kwargs[input_type] = {"media_source": {"asset_id": asset_id}}
    elif input_type == "multi_input":
        ids = list(image_asset_ids or [])
        if not text or not ids:
            raise ValueError("multi_input embedding requires text and image asset IDs")
        if len(ids) > 10:
            raise ValueError("multi_input supports at most 10 images")
        kwargs["multi_input"] = {
            "input_text": text,
            "media_sources": [
                {"media_type": "image", "asset_id": item} for item in ids
            ],
        }
    else:
        raise ValueError(
            "input_type must be video, audio, text, image, or multi_input"
        )
    return to_plain(active.embed.v_2.create(**kwargs))
