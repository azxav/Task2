"""Single-document localhost service with worker-owned cleanup after disconnect."""
import asyncio
import shutil
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .benchmark import ROOT
from .decisions import DecisionUnavailable
from .ocr import OCRUnavailable
from .pdf import InvalidPDF, PDFLimitExceeded, validate_pdf
from .runtime import analyze_pdf, readiness


def create_app(analyze=None, upload_root=None):
    analyze = analyze or analyze_pdf
    root = Path(upload_root or ROOT / ".runtime/uploads").resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    status = {"busy": False, "stage": "idle"}

    @asynccontextmanager
    async def lifespan(app):
        for child in root.glob("doc-tasks-*"):
            if child.is_dir() and (child / ".doc-tasks-owned").is_file():
                shutil.rmtree(child)
        yield

    app = FastAPI(title="Local document tasks", lifespan=lifespan)

    def stage(value):
        status.update(busy=True, stage=value)

    def cleanup(directory):
        try:
            if directory is not None:
                shutil.rmtree(directory)
        finally:
            status.update(busy=False, stage="idle")
            lock.release()

    @app.get("/api/status")
    def get_status():
        return dict(status)

    @app.get("/api/health")
    def health():
        return readiness()

    @app.post("/api/analyze")
    async def analyze_upload(file: Annotated[UploadFile, File()]):
        if not lock.acquire(blocking=False):
            await file.close()
            raise HTTPException(409, "Another document is being analyzed")
        directory = None
        handed_off = False
        stage("reading")
        try:
            directory = Path(tempfile.mkdtemp(prefix="doc-tasks-", dir=root))
            (directory / ".doc-tasks-owned").touch()
            path = directory / "document.pdf"
            size = 0
            with path.open("wb") as output:
                while chunk := await file.read(1024*1024):
                    size += len(chunk)
                    if size > 20*1024*1024:
                        raise HTTPException(413, "PDF exceeds the 20 MB limit")
                    output.write(chunk)
            validate_pdf(path)

            def worker():
                try:
                    return analyze(path, stage)
                finally:
                    cleanup(directory)

            task = asyncio.create_task(asyncio.to_thread(worker))
            # Consume failures even if the browser disconnects before receiving a result.
            task.add_done_callback(lambda completed: completed.exception() if not completed.cancelled() else None)
            handed_off = True
            return await asyncio.shield(task)
        except PDFLimitExceeded as exc:
            raise HTTPException(413, str(exc)) from exc
        except InvalidPDF as exc:
            raise HTTPException(422, str(exc)) from exc
        except (DecisionUnavailable, OCRUnavailable) as exc:
            raise HTTPException(503, str(exc)) from exc
        except OSError as exc:
            raise HTTPException(503, "Local storage unavailable") from exc
        finally:
            await file.close()
            if not handed_off:
                cleanup(directory)

    web = Path(__file__).parent / "web"
    if web.exists():
        app.mount("/assets", StaticFiles(directory=web), name="assets")
        @app.get("/")
        def index():
            return FileResponse(web / "index.html")
    return app
