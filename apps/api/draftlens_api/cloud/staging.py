from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from draftlens_api.cloud.models import CloudFileReference
from draftlens_api.services.paths import DataPaths

_STAGING_TTL_S = 3600


def staging_dir(paths: DataPaths, user_id: str, handle: str) -> Path:
    return paths.cloud_staging / user_id / handle


def write_staged_bytes(
    paths: DataPaths,
    *,
    user_id: str,
    data: bytes,
    reference: CloudFileReference,
) -> str:
    handle = str(uuid.uuid4())
    d = staging_dir(paths, user_id, handle)
    d.mkdir(parents=True, exist_ok=True)
    blob = d / "blob"
    blob.write_bytes(data)
    meta: dict[str, Any] = {
        "reference": reference.model_dump(mode="json"),
        "created_at": time.time(),
    }
    (d / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return handle


def read_staged(paths: DataPaths, user_id: str, handle: str) -> tuple[Path, CloudFileReference]:
    d = staging_dir(paths, user_id, handle)
    blob = d / "blob"
    meta_path = d / "meta.json"
    if not blob.is_file() or not meta_path.is_file():
        raise FileNotFoundError("staging_missing")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    ref = CloudFileReference.model_validate(meta["reference"])
    created = float(meta.get("created_at") or 0)
    if time.time() - created > _STAGING_TTL_S:
        raise TimeoutError("staging_expired")
    return blob, ref


def delete_staged(paths: DataPaths, user_id: str, handle: str) -> None:
    d = staging_dir(paths, user_id, handle)
    if d.is_dir():
        for p in sorted(d.glob("**/*"), reverse=True):
            if p.is_file():
                p.unlink(missing_ok=True)
        try:
            d.rmdir()
        except OSError:
            pass
