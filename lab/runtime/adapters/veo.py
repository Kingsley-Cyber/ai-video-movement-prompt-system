"""Google Vertex AI Veo 3.1 REST adapter for compiled CPCS build requests."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable

from lab.compiler.provenance import sha256_bytes

from .base import AdapterError

ADAPTER_ID = "google_vertex_ai.veo/1.0"
OPERATION_RE = re.compile(
    r"^projects/[a-z][a-z0-9-]+/locations/us-central1/publishers/google/"
    r"models/veo-3\.1-generate-001/operations/[A-Za-z0-9._-]+$"
)
SUBMIT_URL_RE = re.compile(
    r"^https://us-central1-aiplatform\.googleapis\.com/v1/projects/"
    r"[a-z][a-z0-9-]+/locations/us-central1/publishers/google/models/"
    r"veo-3\.1-generate-001:predictLongRunning$"
)


def _default_access_token() -> str:
    try:
        import google.auth
        from google.auth.transport.requests import Request
    except ImportError as error:
        raise AdapterError(
            "google-auth is not installed; install lab/runtime/requirements.txt",
            code="authentication_unavailable",
        ) from error
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(Request())
    if not credentials.token:
        raise AdapterError("Google ADC returned no access token", code="authentication_failed")
    return str(credentials.token)


def _plain_json(body: bytes) -> dict[str, Any]:
    try:
        value = json.loads(body)
    except json.JSONDecodeError as error:
        raise AdapterError("provider returned invalid JSON", code="invalid_response") from error
    if not isinstance(value, dict):
        raise AdapterError("provider response must be an object", code="invalid_response")
    return value


class VeoVertexAdapter:
    """Transport-only adapter for the build compiler's Veo REST payload."""

    adapter_id = ADAPTER_ID
    submission_idempotent = False
    supports_remote_cancel = False

    def __init__(
        self,
        *,
        token_provider: Callable[[], str] = _default_access_token,
        opener: Callable[[urllib.request.Request, float], bytes] | None = None,
        download: Callable[[str, str], bytes] | None = None,
        request_timeout_s: float = 120.0,
    ) -> None:
        self._token_provider = token_provider
        self._opener = opener or self._urlopen
        self._download = download or self._download_gcs
        self._request_timeout_s = request_timeout_s

    @staticmethod
    def _urlopen(request: urllib.request.Request, timeout: float) -> bytes:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()

    def _request_json(
        self,
        *,
        url: str,
        body: dict[str, Any],
        stage: str,
    ) -> dict[str, Any]:
        token = self._token_provider()
        request = urllib.request.Request(
            url,
            data=json.dumps(body, sort_keys=True, separators=(",", ":")).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        try:
            response = self._opener(request, self._request_timeout_s)
        except urllib.error.HTTPError as error:
            payload = error.read().decode("utf-8", errors="replace")[:2000]
            retryable = error.code in {429, 500, 502, 503, 504}
            raise AdapterError(
                f"Veo {stage} HTTP {error.code}: {payload}",
                retryable=retryable,
                submission_uncertain=stage == "submit" and error.code >= 500,
                code=f"http_{error.code}",
            ) from error
        except (OSError, TimeoutError) as error:
            raise AdapterError(
                f"Veo {stage} transport failed: {error}",
                retryable=True,
                submission_uncertain=stage == "submit",
                code="transport_error",
            ) from error
        return _plain_json(response)

    def validate(self, build: dict[str, Any], job: dict[str, Any]) -> None:
        manifest = build["manifest"]
        request = build["provider_request"]
        if job["adapter"] != self.adapter_id:
            raise AdapterError("render job selects a different adapter", code="adapter_mismatch")
        if manifest["provider_capability_id"] != (
            "provider-capability://google-vertex-ai/veo-3.1-generate-001/1.0"
        ):
            raise AdapterError("build capability is not Veo 3.1", code="capability_mismatch")
        if request.get("method") != "POST" or not SUBMIT_URL_RE.fullmatch(
            str(request.get("url", ""))
        ):
            raise AdapterError("compiled Veo request URL is not allowed", code="request_rejected")
        if any(
            key.lower() in {"authorization", "access_token", "api_key"}
            for key in request
        ):
            raise AdapterError("compiled request contains credentials", code="secret_in_request")

    def prepare(self, build: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
        request = build["provider_request"]
        return {
            "method": request["method"],
            "url": request["url"],
            "body": request["body"],
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "build_id": build["manifest"]["build_id"],
            "adapter": self.adapter_id,
        }

    def submit(
        self, prepared: dict[str, Any], *, idempotency_key: str
    ) -> dict[str, Any]:
        response = self._request_json(
            url=prepared["url"], body=prepared["body"], stage="submit"
        )
        operation_name = response.get("name")
        if not isinstance(operation_name, str) or not OPERATION_RE.fullmatch(operation_name):
            raise AdapterError(
                "Veo submission returned an invalid operation name",
                submission_uncertain=True,
                code="invalid_operation_receipt",
            )
        return {
            "operation_id": operation_name,
            "provider": "google_vertex_ai",
            "model": "veo-3.1-generate-001",
            "submit_response": response,
        }

    def poll(self, operation: dict[str, Any]) -> dict[str, Any]:
        operation_name = operation.get("operation_id")
        if not isinstance(operation_name, str) or not OPERATION_RE.fullmatch(operation_name):
            raise AdapterError("cannot poll an invalid Veo operation", code="invalid_operation")
        project = operation_name.split("/", 2)[1]
        url = (
            "https://us-central1-aiplatform.googleapis.com/v1/projects/"
            f"{project}/locations/us-central1/publishers/google/models/"
            "veo-3.1-generate-001:fetchPredictOperation"
        )
        response = self._request_json(
            url=url,
            body={"operationName": operation_name},
            stage="poll",
        )
        if response.get("name") != operation_name:
            raise AdapterError("Veo poll crossed operation identity", code="operation_mismatch")
        if not response.get("done", False):
            status = "pending"
        elif isinstance(response.get("error"), dict):
            status = "failed"
        elif isinstance(response.get("response"), dict):
            status = "succeeded"
        else:
            raise AdapterError("completed Veo poll has no response", code="invalid_response")
        return {"status": status, "operation_id": operation_name, "raw": response}

    def _download_gcs(self, uri: str, mime_type: str) -> bytes:
        parsed = urllib.parse.urlparse(uri)
        if parsed.scheme != "gs" or not parsed.netloc or not parsed.path.lstrip("/"):
            raise AdapterError("Veo returned an invalid GCS URI", code="invalid_artifact_uri")
        object_name = urllib.parse.quote(parsed.path.lstrip("/"), safe="")
        url = (
            "https://storage.googleapis.com/download/storage/v1/b/"
            f"{urllib.parse.quote(parsed.netloc, safe='')}/o/{object_name}?alt=media"
        )
        token = self._token_provider()
        request = urllib.request.Request(
            url, method="GET", headers={"Authorization": f"Bearer {token}"}
        )
        try:
            return self._opener(request, self._request_timeout_s)
        except (urllib.error.HTTPError, OSError, TimeoutError) as error:
            raise AdapterError(
                f"Veo artifact retrieval failed: {error}",
                retryable=True,
                code="artifact_retrieval_failed",
            ) from error

    def retrieve(
        self,
        completed: dict[str, Any],
        destination: Path,
    ) -> list[dict[str, Any]]:
        response = completed.get("raw", {}).get("response")
        videos = response.get("videos") if isinstance(response, dict) else None
        if not isinstance(videos, list) or not videos:
            raise AdapterError("Veo completed without video artifacts", code="missing_artifacts")
        destination.mkdir(parents=True, exist_ok=True)
        artifacts: list[dict[str, Any]] = []
        for index, video in enumerate(videos):
            if not isinstance(video, dict) or video.get("mimeType") != "video/mp4":
                raise AdapterError("Veo returned an unsupported artifact", code="invalid_artifact")
            uri = video.get("gcsUri")
            encoded = video.get("bytesBase64Encoded")
            if isinstance(uri, str):
                data = self._download(uri, "video/mp4")
            elif isinstance(encoded, str):
                try:
                    data = base64.b64decode(encoded, validate=True)
                except ValueError as error:
                    raise AdapterError(
                        "Veo returned invalid base64 video data", code="invalid_artifact"
                    ) from error
            else:
                raise AdapterError("Veo artifact has no retrievable carrier", code="invalid_artifact")
            if not data:
                raise AdapterError("Veo returned an empty video artifact", code="invalid_artifact")
            name = f"artifact_{index:03d}.mp4"
            path = destination / name
            if path.exists() and path.read_bytes() != data:
                raise AdapterError("artifact replay changed existing bytes", code="artifact_collision")
            if not path.exists():
                temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
                with temporary.open("xb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
            artifacts.append(
                {
                    "artifact_id": f"artifact_{index:03d}",
                    "relative_path": f"artifacts/{name}",
                    "source_uri": uri,
                    "mime_type": "video/mp4",
                    "size_bytes": len(data),
                    "sha256": sha256_bytes(data),
                }
            )
        return artifacts

    def normalize(
        self,
        *,
        job: dict[str, Any],
        build: dict[str, Any],
        operation: dict[str, Any],
        completed: dict[str, Any],
        artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        settings = build["provider_request"]["body"]["parameters"]
        result = {
            "schema": "cpcs.render_result/1.0",
            "job_id": job["job_id"],
            "build_id": build["manifest"]["build_id"],
            "build_hash": build["manifest"]["build_hash"],
            "provider": "google_vertex_ai",
            "model": "veo-3.1-generate-001",
            "operation_id": operation["operation_id"],
            "status": "succeeded",
            "artifacts": artifacts,
            "expected_media": {
                "duration_seconds": settings["durationSeconds"],
                "aspect_ratio": settings["aspectRatio"],
                "resolution": settings["resolution"],
                "sample_count": settings["sampleCount"],
            },
            "provider_response_hash": "sha256:"
            + hashlib.sha256(
                json.dumps(
                    completed["raw"], sort_keys=True, separators=(",", ":")
                ).encode()
            ).hexdigest(),
        }
        return result

    def cancel(self, operation: dict[str, Any]) -> dict[str, Any]:
        return {
            "supported": False,
            "status": "unsupported",
            "operation_id": operation.get("operation_id"),
            "warning": (
                "Veo predictLongRunning exposes polling but no documented server-side "
                "cancellation method; local polling can stop while provider work may continue."
            ),
        }
