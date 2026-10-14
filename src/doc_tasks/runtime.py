"""Explicit local production profile; text-only Tev1, no baseline fallback."""
import json
import os
from pathlib import Path

import httpx

from .audit import AuditedDecisions
from .benchmark import ROOT, code_hash, local_ocr
from .decisions import DecisionUnavailable, OllamaDecisions, validate_local_url
from .extract import extract
from .network import install_local_network_guard
from .pdf import read_pdf


class Settings:
    def __init__(self):
        self.model = os.environ.get("DOC_TASKS_MODEL", "tev1:4b-q4_K_M")
        if not self.model.startswith("tev1:"):
            raise ValueError("Production requires Tev1; Qwen is a comparison baseline")
        self.base_url = os.environ.get("DOC_TASKS_OLLAMA_URL", "http://127.0.0.1:11435")
        validate_local_url(self.base_url)
        self.ocr_engine = os.environ.get("DOC_TASKS_OCR", "paddle-vl")
        if self.ocr_engine not in ("paddle-vl", "paddle-v5", "tesseract"):
            raise ValueError("Unknown local OCR engine")


def verify_model_profile(settings, transport=None):
    profiles = json.loads((ROOT / "model-profiles.json").read_text(encoding="utf-8"))["models"]
    if settings.model not in profiles:
        raise DecisionUnavailable("Unbenchmarked Tev1 profile; choose a model in model-profiles.json")
    try:
        with httpx.Client(base_url=settings.base_url, transport=transport, trust_env=False, timeout=5) as http:
            models = http.get("/api/tags").raise_for_status().json()["models"]
        actual = next((m for m in models if m["name"] == settings.model), None)
        if not actual:
            raise DecisionUnavailable("Tested local Tev1 model missing; load its pinned tag during setup")
        if actual.get("digest") != profiles[settings.model]["digest"]:
            raise DecisionUnavailable("Model digest changed; benchmark the new weights before production use")
        return actual["digest"]
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise DecisionUnavailable("Local Ollama service unavailable; start run.ps1") from exc


def readiness(settings=None):
    settings = settings or Settings()
    result = {"model": settings.model, "ocr": settings.ocr_engine, "local_only": True,
              "model_ready": False, "ocr_ready": False}
    with httpx.Client(base_url=settings.base_url, trust_env=False, timeout=3) as http:
        try:
            models = http.get("/api/tags").raise_for_status().json()["models"]
            result["model_ready"] = any(m["name"] == settings.model for m in models)
        except (httpx.HTTPError, ValueError, KeyError):
            pass
    adapter = local_ocr(settings.ocr_engine)
    result["ocr_ready"] = all(Path(p).exists() for p in (adapter.command[0], adapter.command[3]))
    if settings.ocr_engine == "tesseract":
        needed = [Path(os.environ["TESSERACT_BIN"]), Path(os.environ["TESSDATA_DIR"]) / "uzb.traineddata",
                  Path(os.environ["TESSDATA_DIR"]) / "eng.traineddata"]
    else:
        names = ["PP-DocLayoutV3", "PaddleOCR-VL-1.6"] if settings.ocr_engine == "paddle-vl" else [
            "PP-OCRv5_mobile_det", "latin_PP-OCRv5_mobile_rec"]
        needed = [Path(os.environ["OCR_MODEL_ROOT"]) / name for name in names]
    result["ocr_ready"] &= all(path.exists() for path in needed)
    return result


def analyze_pdf(path, stage=lambda value: None, settings=None):
    install_local_network_guard()
    settings = settings or Settings()
    digest = verify_model_profile(settings)
    # The dedicated local Ollama service releases VRAM before a local GPU OCR worker starts.
    if settings.ocr_engine == "paddle-vl":
        with httpx.Client(base_url=settings.base_url, trust_env=False, timeout=30) as http:
            try:
                for model in http.get("/api/ps").raise_for_status().json().get("models", []):
                    http.post("/api/generate", json={"model": model["name"], "keep_alive": 0}).raise_for_status()
            except httpx.HTTPError:
                pass  # Native extraction still validates input; the decision adapter reports model failure.
    document = read_pdf(path, local_ocr(settings.ocr_engine), stage)
    stage("extracting")
    client = AuditedDecisions(OllamaDecisions(settings.model, settings.base_url))
    try:
        result = extract(document, client)
        stage("validating")
        result.provenance.update({"stack_sha256": code_hash(), "decision_trace": client.trace,
                                  "model_digest": digest,
                                  "profile": {"model": settings.model, "ocr": settings.ocr_engine}})
        return result
    finally:
        client.close()
