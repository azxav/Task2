"""OCR contracts and process boundary; no cloud inference."""
import json
import subprocess
from pathlib import Path
from typing import Protocol

from pydantic import Field

from .schema import SourceSpan, StrictModel


class TableRow(StrictModel):
    id: str
    reference: str
    cells: dict[str, list[str]]


class OCRPage(StrictModel):
    page: int
    width: float
    height: float
    spans: list[SourceSpan]
    rows: list[TableRow] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    raw_result: dict = Field(default_factory=dict)


class OCRAdapter(Protocol):
    name: str

    def recognize(self, image_path: Path, page: int) -> OCRPage: ...


class OCRUnavailable(RuntimeError):
    pass


class ProcessOCR:
    """Execute a pinned local OCR worker in its independent Python environment."""

    def __init__(self, name: str, command: list[str], timeout: float = 300):
        self.name = name
        self.command = command
        self.timeout = timeout

    def recognize(self, image_path: Path, page: int) -> OCRPage:
        result_path = image_path.with_suffix(".ocr.json")
        try:
            completed = subprocess.run(
                [*self.command, "--image", str(image_path), "--page", str(page),
                 "--output", str(result_path)],
                capture_output=True, timeout=self.timeout, check=False,
            )
            if completed.returncode != 0 or not result_path.exists():
                raise OCRUnavailable(f"Local {self.name} OCR worker failed")
            return OCRPage.model_validate(json.loads(result_path.read_text(encoding="utf-8")))
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            raise OCRUnavailable(f"Local {self.name} OCR worker unavailable") from exc


class NoOCR:
    name = "unconfigured"

    def recognize(self, image_path: Path, page: int) -> OCRPage:
        raise OCRUnavailable("Scanned page requires a configured local OCR engine")
