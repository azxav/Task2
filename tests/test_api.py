import asyncio
import threading
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from doc_tasks.schema import AnalysisResult, Metadata


def pdf_bytes(tmp_path, pages=1):
    path = tmp_path / "input.pdf"
    c = canvas.Canvas(str(path))
    for _ in range(pages):
        c.drawString(50, 700, "A local document with sufficient native text.")
        c.showPage()
    c.save()
    return path.read_bytes()


def app_factory(tmp_path, analyze=None):
    from doc_tasks.api import create_app
    return create_app(analyze=analyze or (lambda path, stage: AnalysisResult(metadata=Metadata(), tasks=[])),
                      upload_root=tmp_path / "uploads")


def test_upload_result_and_cleanup(tmp_path):
    app = app_factory(tmp_path)
    with TestClient(app) as client:
        response = client.post("/api/analyze", files={"file": ("test.pdf", pdf_bytes(tmp_path), "application/pdf")})
        assert response.status_code == 200
        assert response.json()["tasks"] == []
        assert client.get("/api/status").json()["busy"] is False
        assert list((tmp_path / "uploads").iterdir()) == []


def test_limits_and_corrupt_input(tmp_path):
    app = app_factory(tmp_path)
    with TestClient(app) as client:
        for content, expected in [(b"x" * (20*1024*1024+1), 413), (pdf_bytes(tmp_path, 21), 413), (b"bad pdf", 422)]:
            response = client.post("/api/analyze", files={"file": ("input.pdf", content, "application/pdf")})
            assert response.status_code == expected
        assert not list((tmp_path / "uploads").iterdir())


def test_inference_failure_cleans_and_unlocks(tmp_path):
    from doc_tasks.decisions import DecisionUnavailable
    def failed(path, stage):
        raise DecisionUnavailable("unavailable")
    with TestClient(app_factory(tmp_path, failed)) as client:
        response = client.post("/api/analyze", files={"file": ("x.pdf", pdf_bytes(tmp_path))})
        assert response.status_code == 503
        assert client.get("/api/status").json()["busy"] is False
        assert not list((tmp_path / "uploads").iterdir())


def test_concurrent_request_and_disconnect_keep_lock_until_work_finishes(tmp_path):
    started, release, finished = threading.Event(), threading.Event(), threading.Event()
    def slow(path, stage):
        started.set()
        release.wait(5)
        assert Path(path).exists()
        finished.set()
        return AnalysisResult(metadata=Metadata(), tasks=[])
    app = app_factory(tmp_path, slow)
    content = pdf_bytes(tmp_path)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            request = asyncio.create_task(client.post("/api/analyze", files={"file": ("x.pdf", content)}))
            await asyncio.to_thread(started.wait, 3)
            assert started.is_set()
            request.cancel()
            try:
                await request
            except asyncio.CancelledError:
                pass
            assert (await client.get("/api/status")).json()["busy"] is True
            assert (await client.post("/api/analyze", files={"file": ("x.pdf", content)})).status_code == 409
            release.set()
            await asyncio.to_thread(finished.wait, 3)
            for _ in range(100):
                if not (await client.get("/api/status")).json()["busy"]:
                    break
                await asyncio.sleep(.01)
            assert not (await client.get("/api/status")).json()["busy"]
            assert not list((tmp_path / "uploads").iterdir())
    asyncio.run(run())


def test_encrypted_pdf_rejected(tmp_path):
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter()
    writer.append_pages_from_reader(PdfReader(BytesIO(pdf_bytes(tmp_path))))
    writer.encrypt("password")
    buffer = BytesIO()
    writer.write(buffer)
    with TestClient(app_factory(tmp_path)) as client:
        assert client.post("/api/analyze", files={"file": ("x.pdf", buffer.getvalue())}).status_code == 422


def test_upload_storage_failure_does_not_leak_job_lock(tmp_path, monkeypatch):
    from doc_tasks import api
    original = api.tempfile.mkdtemp
    with TestClient(app_factory(tmp_path), raise_server_exceptions=False) as client:
        monkeypatch.setattr(api.tempfile, "mkdtemp", lambda **kwargs: (_ for _ in ()).throw(OSError("disk full")))
        assert client.post("/api/analyze", files={"file": ("x.pdf", pdf_bytes(tmp_path))}).status_code == 503
        monkeypatch.setattr(api.tempfile, "mkdtemp", original)
        assert client.post("/api/analyze", files={"file": ("x.pdf", pdf_bytes(tmp_path))}).status_code == 200
