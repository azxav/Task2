"""Choose task boundaries over verbatim text; retain parent span provenance."""
import itertools
import re

from .candidates import UNIT, passage_text
from .decisions import DecisionQuestion
from .language import explicit_action
from .schema import Document, SourceSpan


def _subject(text):
    body = re.sub(r"^\d+[.)]\s*", "", text.strip())
    match = re.match(rf"(.{{1,100}}?\b{UNIT})\b", body, re.IGNORECASE)
    if match and re.match(r"\s+bilan\b", body[match.end():], re.IGNORECASE):
        return None  # Coordination/consultation phrase is not a new grammatical subject.
    return match.group(1).casefold() if match else None


def _same_draft(left, right):
    return bool(
        re.search(r"loyiha", left, re.IGNORECASE)
        and re.search(r"ishlab\s+chiqsin|tayyorlasin", left, re.IGNORECASE)
        and re.search(r"kiritsin|taqdim\s+etsin", right, re.IGNORECASE)
        and not _subject(right)
        and not re.search(r"hisobot|axborot|ma[‘’ʻʼ']lumot|taklif", right, re.IGNORECASE)
    )


def segment_document(document, client):
    spans = list(document.spans)
    passages = []
    by_id = {span.id: span for span in spans}
    warnings = list(document.warnings)
    for passage in document.passages:
        if passage.kind not in ("paragraph", "clause"):
            passages.append(passage)
            continue
        text = passage_text(document, passage)
        cuts = [0]
        # Conjunctions are candidates, never sufficient evidence to split a compound.
        for boundary in re.finditer(r";\s+|[.!?]\s+(?=[A-ZА-Я])|\s+(?:hamda|va)\s+", text):
            left, right = text[cuts[-1]:boundary.start()].strip(), text[boundary.end():].strip()
            if not explicit_action(left) or not explicit_action(right):
                continue
            first, second = _subject(left), _subject(right)
            if _same_draft(left, right):
                continue
            separate_subjects = bool(first and second and first != second)
            decision = client.evaluate(
                {"clause": text, "left": left, "right": right, "source_ids": passage.span_ids},
                [DecisionQuestion(id="task_boundary", type="choice", instructions=(
                    "Are these independently assigned obligations? Split separate deliverables with distinct "
                    "responsible executors or deadlines. Preserve ONE compound task when actions develop and "
                    "submit the SAME draft, or implement an appendix and report its progress. Conjunction alone "
                    "is not evidence of independence. Never invent tasks or change wording."
                ), options={"split": "Separate independent obligations", "preserve": "One compound task"})],
            )["task_boundary"]
            if decision.selected_id == "split" or separate_subjects:
                # Keep punctuation/conjunction on the left: both outputs are literal source substrings.
                cuts.append(boundary.end())
                if separate_subjects and decision.selected_id != "split":
                    warnings.append(f"{passage.id}: distinct explicit executors preserved as separate tasks; review boundary")
        if len(cuts) == 1:
            passages.append(passage)
            continue
        cuts.append(len(text))
        for part, (start, end) in enumerate(itertools.pairwise(cuts)):
            refs = []
            offset = 0
            for ref in passage.span_ids:
                original = by_id[ref]
                a, b = max(start, offset), min(end, offset+len(original.text))
                if a < b:
                    value = original.text[a-offset:b-offset].strip()
                    if value:
                        span = SourceSpan(id=f"{passage.id}-part-{part}-{ref}", page=original.page,
                                          text=value, bbox=original.bbox, parent_id=ref)
                        spans.append(span)
                        refs.append(span.id)
                offset += len(original.text)+1
            passages.append(passage.model_copy(update={"id": f"{passage.id}-part-{part}", "span_ids": refs}))
    return Document(spans=spans, passages=passages, warnings=warnings, provenance=document.provenance)
