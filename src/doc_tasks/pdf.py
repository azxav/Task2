import hashlib
import re
import tempfile
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

from .ocr import OCRAdapter, OCRPage, TableRow
from .roles import table_role
from .schema import SourceSpan
from .structure import build_passages


class InvalidPDF(ValueError):
    pass


class PDFLimitExceeded(ValueError):
    pass


def _clean(text):
    return " ".join((text or "").split())


def _native_page(page, number):
    spans = []
    rows = []
    table_boxes = []
    for table_index, table in enumerate(page.find_tables()):
        extracted = table.extract()
        if not extracted or len(extracted) < 2:
            continue
        roles = [table_role(cell) for cell in extracted[0]]
        if "instruction" not in roles:
            continue
        table_boxes.append(table.bbox)
        for row_index, row in enumerate(extracted[1:], 1):
            cells = {}
            geometry = table.rows[row_index].cells
            for column, text in enumerate(row):
                role = roles[column]
                cells.setdefault(role, [])
                if not _clean(text):
                    continue
                ref = f"p{number}-table{table_index}-r{row_index}-c{column}"
                spans.append(SourceSpan(id=ref, page=number, text=_clean(text), bbox=geometry[column]))
                cells[role].append(ref)
            rows.append(TableRow(id=f"p{number}-table{table_index}-row{row_index}",
                                 reference=f"table-{table_index + 1}/row-{_clean(row[0])}", cells=cells))

    words = page.extract_words(x_tolerance=2, y_tolerance=3)
    words = [word for word in words if not any(
        box[0] <= (word["x0"] + word["x1"]) / 2 <= box[2]
        and box[1] <= (word["top"] + word["bottom"]) / 2 <= box[3] for box in table_boxes
    )]
    lines = []
    for word in sorted(words, key=lambda word: (round(word["top"] / 3), word["x0"])):
        line = next((line for line in reversed(lines[-3:]) if abs(line[0]["top"] - word["top"]) < 3), None)
        if line is None:
            lines.append([word])
        else:
            line.append(word)
    for line_index, line in enumerate(lines):
        fragments = [[]]
        for word in sorted(line, key=lambda word: word["x0"]):
            if fragments[-1] and word["x0"] - fragments[-1][-1]["x1"] > 24:
                fragments.append([])
            fragments[-1].append(word)
        for fragment_index, fragment in enumerate(fragments):
            text = _clean(" ".join(word["text"] for word in fragment))
            if not text or re.fullmatch(r"\d+", text) and fragment[0]["top"] > page.height * .93:
                continue
            spans.append(SourceSpan(
                id=f"p{number}-line{line_index}-f{fragment_index}", page=number, text=text,
                bbox=(min(word["x0"] for word in fragment), min(word["top"] for word in fragment),
                      max(word["x1"] for word in fragment), max(word["bottom"] for word in fragment)),
            ))
    spans.sort(key=lambda span: (span.bbox[1], span.bbox[0]))
    return OCRPage(page=number, width=page.width, height=page.height, spans=spans, rows=rows)


def validate_pdf(path: Path):
    if path.stat().st_size > 20 * 1024 * 1024:
        raise PDFLimitExceeded("PDF exceeds the 20 MB limit")
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise InvalidPDF("Encrypted PDFs are unsupported")
        if not reader.pages:
            raise InvalidPDF("PDF has no pages")
        if len(reader.pages) > 20:
            raise PDFLimitExceeded("PDF exceeds the 20-page limit")
    except (InvalidPDF, PDFLimitExceeded):
        raise
    except Exception as exc:
        raise InvalidPDF("Invalid or corrupt PDF") from exc
    return len(reader.pages)


def read_pdf(path: Path, ocr: OCRAdapter, stage=None):
    validate_pdf(path)
    pages = []
    modes = []
    with pdfplumber.open(path) as pdf, tempfile.TemporaryDirectory(prefix="doc-tasks-ocr-") as directory:
        for number, page in enumerate(pdf.pages, 1):
            native_text = (page.extract_text() or "").strip()
            # An image-only page with a tiny page-number layer still needs OCR.
            if len(native_text) >= 30 or native_text and not page.images:
                if stage:
                    stage("reading")
                pages.append(_native_page(page, number))
                modes.append("native")
            else:
                if stage:
                    stage("ocr")
                image_path = Path(directory) / f"page-{number}.png"
                page.to_image(resolution=220).save(image_path)
                pages.append(ocr.recognize(image_path, number))
                modes.append("ocr")
    document = build_passages(pages)
    document.provenance = {
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "page_modes": modes, "ocr": ocr.name,
        "ocr_raw_results": {str(page.page): page.raw_result for page in pages if page.raw_result},
    }
    return document
