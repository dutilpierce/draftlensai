from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from draftlens_api.config import Settings


@dataclass(frozen=True)
class DataPaths:
    root: Path

    @property
    def uploads_main(self) -> Path:
        return self.root / "uploads" / "main"

    @property
    def uploads_supporting(self) -> Path:
        return self.root / "uploads" / "supporting"

    def job_working(self, job_id: str) -> Path:
        return self.root / "jobs" / job_id / "working"

    def job_artifacts(self, job_id: str) -> Path:
        return self.root / "jobs" / job_id / "artifacts"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def tmp(self) -> Path:
        return self.root / "tmp"

    @property
    def cloud_staging(self) -> Path:
        return self.root / "cloud_staging"

    def ensure_layout(self) -> None:
        self.uploads_main.mkdir(parents=True, exist_ok=True)
        self.uploads_supporting.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.cloud_staging.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def from_settings(settings: Settings) -> "DataPaths":
        return DataPaths(root=Path(settings.data_dir))


def main_upload_path(paths: DataPaths, job_id: str, filename: str) -> Path:
    safe = Path(filename).name
    paths.uploads_main.mkdir(parents=True, exist_ok=True)
    (paths.uploads_main / job_id).mkdir(parents=True, exist_ok=True)
    return paths.uploads_main / job_id / safe


def supporting_upload_path(paths: DataPaths, job_id: str, filename: str) -> Path:
    safe = Path(filename).name
    (paths.uploads_supporting / job_id).mkdir(parents=True, exist_ok=True)
    return paths.uploads_supporting / job_id / safe
