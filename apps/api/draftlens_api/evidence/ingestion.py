from __future__ import annotations

from pathlib import Path

from draftlens_api.services.documents import extract_supporting


def bundle_supporting_text(files: list[tuple[Path, str]]) -> str:
    blocks: list[str] = []
    for path, original_name in files:
        try:
            text = extract_supporting(path, original_name)
        except Exception as exc:  # noqa: BLE001
            blocks.append(f"### {original_name}\n(unreadable: {exc})")
            continue
        preview = text.strip()
        if len(preview) > 120_000:
            preview = preview[:120_000] + "\n\n[truncated]"
        blocks.append(f"### {original_name}\n{preview}")
    return "\n\n".join(blocks).strip()
