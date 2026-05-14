from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

CloudProvider = Literal["google_drive", "dropbox", "onedrive"]
DocumentRole = Literal["main", "supporting"]


class CloudFileReference(BaseModel):
    """Normalized descriptor after a successful cloud import (pre-job)."""

    provider: CloudProvider
    provider_file_id: str = ""
    shared_link: str | None = None
    download_url: str | None = None
    filename: str
    mime_type: str
    document_role: DocumentRole = "main"


class CloudImportRequest(BaseModel):
    """Client → API: fetch a remote file into DraftLens staging using a short-lived access token."""

    provider: CloudProvider
    provider_file_id: str = Field(default="", description="Drive / Graph item id; empty when using shared_link (Dropbox).")
    shared_link: str | None = Field(default=None, description="Dropbox Chooser shared link (alternative to provider_file_id).")
    download_url: str | None = Field(
        default=None,
        description="OneDrive picker temporary @microsoft.graph.downloadUrl (no token needed for GET).",
    )
    filename: str = Field(min_length=1, max_length=512)
    mime_type: str | None = Field(default=None, description="Hint from picker; Drive export may override.")
    document_role: DocumentRole = "main"

    @model_validator(mode="after")
    def _has_remote_pointer(self) -> "CloudImportRequest":
        if self.provider == "google_drive" and not self.provider_file_id.strip():
            raise ValueError("google_drive_requires_provider_file_id")
        if self.provider == "dropbox":
            if not (self.shared_link or "").strip() and not self.provider_file_id.strip():
                raise ValueError("dropbox_requires_shared_link_or_path")
        if self.provider == "onedrive":
            if not self.download_url and not self.provider_file_id.strip():
                raise ValueError("onedrive_requires_download_url_or_item_id")
        return self


class CloudImportResult(BaseModel):
    import_handle: str
    reference: CloudFileReference


class CloudExportRequest(BaseModel):
    """Upload an existing artifact to the user's cloud as a new file (never in-place)."""

    provider: CloudProvider
    artifact_name: str = Field(min_length=1, max_length=256, description="Artifact filename, e.g. reviewed.docx")
    parent_folder_id: str | None = Field(default=None, description="Optional Drive folder / Graph parent id.")


class CloudExportResult(BaseModel):
    provider: CloudProvider
    remote_file_id: str | None = None
    web_view_link: str | None = None
    message: str = "uploaded"


class CloudImportBody(BaseModel):
    request: CloudImportRequest
    access_token: str = Field(default="", max_length=16000, description="User OAuth access token; empty if download_url suffices.")


class CloudExportBody(BaseModel):
    job_id: str = Field(min_length=8, max_length=80)
    request: CloudExportRequest
    access_token: str = Field(min_length=10, max_length=16000)


class DropboxPkceTokenRequest(BaseModel):
    code: str = Field(min_length=4)
    redirect_uri: str = Field(min_length=8, max_length=2048)
    code_verifier: str = Field(min_length=43, max_length=128)


class MicrosoftPkceTokenRequest(BaseModel):
    code: str = Field(min_length=4)
    redirect_uri: str = Field(min_length=8, max_length=2048)
    code_verifier: str = Field(min_length=43, max_length=128)


class GoogleDriveFileMetadataBody(BaseModel):
    """User access token + Drive file id — used only for lightweight metadata (thumbnails, links)."""

    file_id: str = Field(min_length=1, max_length=512)
    access_token: str = Field(min_length=10, max_length=16000)


class GoogleDriveFileMetadataResult(BaseModel):
    id: str
    name: str
    mime_type: str = ""
    icon_link: str | None = None
    thumbnail_link: str | None = None
    web_view_link: str | None = None
    size: str | None = None
    modified_time: str | None = None
