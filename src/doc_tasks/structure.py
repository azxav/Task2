import re

from .language import explicit_action
from .ocr import OCRPage
from .schema import Document, Passage


def build_passages(pages: list[OCRPage]) -> Document:
    spans = []
    passages = []
    warnings = []
    for page in pages:
        spans.extend(page.spans)
        warnings.extend(page.diagnostics)
        table_ids = {ref for row in page.rows for refs in row.cells.values() for ref in refs}
        for row in page.rows:
            references = [ref for refs in row.cells.values() for ref in refs]
            if not row.cells.get("instruction"):
                warnings.append(f"Page {page.page}, row {row.reference}: instruction cell missing")
                continue
            for role in ("executor", "deadline"):
                if not row.cells.get(role):
                    warnings.append(f"Page {page.page}, row {row.reference}: {role} cell missing")
            passages.append(Passage(id=row.id, kind="table_row", span_ids=references,
                                    clause_ref=row.reference, table_cells=row.cells))

        groups = []
        current = []
        current_kind = "paragraph"
        clause_ref = None
        for span in page.spans:
            if span.id in table_ids:
                continue
            text = span.text.strip()
            if not text:
                continue
            number = re.match(r"^(\d+)[.)]\s+", text)
            kind = "clause" if number else "paragraph"
            y = span.bbox[1] if span.bbox else page.height / 2
            if page.page == 1 and y < page.height * .24 and not number and not explicit_action(text):
                kind = "header"
            if y > page.height * .92 or re.match(r"^(Ijrochi:|Tel\.:|Test uchun example)", text):
                kind = "footer"
            if text in ("ILOVA", "Q A R O R I", "QARORI", "CHORA-TADBIRLAR REJASI"):
                kind = "heading"
            previous = current[-1] if current else None
            separated = False
            if previous and previous.bbox and span.bbox:
                height = max(8, previous.bbox[3] - previous.bbox[1])
                gap = span.bbox[1] - previous.bbox[3]
                # Same-baseline fragments are separate columns, never a continuation.
                separated = gap < -height * .5 or gap > height * .85
            boundary = (
                bool(number) or separated or kind in ("footer", "heading")
                or current_kind in ("footer", "heading")
                or (previous is not None and previous.text.rstrip().endswith((".", "!", "?", ":"))
                    and not re.match(r"^(Deadline|Muddat)\s*:", text, re.IGNORECASE))
                or (current_kind == "header" and kind != "header" and not explicit_action(text))
            )
            if current and boundary:
                groups.append((current, current_kind, clause_ref))
                current = []
            if not current:
                current_kind = kind
                clause_ref = number.group(1) if number else None
            current.append(span)
        if current:
            groups.append((current, current_kind, clause_ref))
        for index, (group, kind, reference) in enumerate(groups):
            if kind == "header" and explicit_action(" ".join(span.text for span in group)):
                kind = "paragraph"
            passages.append(Passage(id=f"p{page.page}-block-{index}", kind=kind,
                                    span_ids=[span.id for span in group], clause_ref=reference))
    by_id = {span.id: span for span in spans}
    passages.sort(key=lambda passage: (
        by_id[passage.span_ids[0]].page,
        (by_id[passage.span_ids[0]].bbox or (0, 0, 0, 0))[1],
        (by_id[passage.span_ids[0]].bbox or (0, 0, 0, 0))[0],
    ))
    return Document(spans=spans, passages=passages, warnings=warnings)
