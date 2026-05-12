from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from draftlens_api.domain.models import EvidenceSource, MainDocumentRecord, SupportingFileRecord
from draftlens_api.evidence.supporting_parser import SupportingFileParser


@dataclass
class EvidenceIngestionService:
    """Extracts and normalizes supporting material; never treats evidence as the editable manuscript."""

    def build_evidence_bundle(self, supporting: list[tuple[Path, str]]) -> tuple[str, list[EvidenceSource]]:
        parser = SupportingFileParser()
        bundle_parts: list[str] = []
        sources: list[EvidenceSource] = []
        for path, original_name in supporting:
            pr = parser.parse(path, original_name)
            bundle_parts.append(pr.bundle_section)
            sources.extend(pr.sources)
        return "\n\n".join(bundle_parts).strip(), sources

    def describe_main(self, rec: MainDocumentRecord) -> EvidenceSource:
        preview = rec.full_text[:8000]
        if len(rec.full_text) > 8000:
            preview += "\n\n[main document truncated for evidence preview]"
        return EvidenceSource(label=rec.original_filename, excerpt=preview, kind="main_snippet")

    def to_supporting_record(
        self,
        *,
        job_id: str,
        file_id: str,
        original_name: str,
        storage_path: str,
        mime: str,
        byte_size: int,
        extracted_cache_path: str | None = None,
        pages: int | None = None,
    ) -> SupportingFileRecord:
        return SupportingFileRecord(
            file_id=file_id,
            job_id=job_id,
            original_name=original_name,
            storage_path=storage_path,
            mime=mime,
            byte_size=byte_size,
            extracted_cache_path=extracted_cache_path,
            page_estimate=pages,
        )
