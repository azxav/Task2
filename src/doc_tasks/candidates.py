"""Broad source-span candidates; model decisions assign semantic roles."""
import re

from .schema import Document, Passage, StrictModel

APOSTROPHE = "['‘’ʻʼ`´]"
UNIT = rf"(?:boshqarmasi|departamenti|bo{APOSTROPHE}lim(?:i)?|laboratoriyasi|kotibiyati|bo{APOSTROPHE}linmalar(?:i)?|guruhi|koordinatori|markaziga|o{APOSTROPHE}rinbosari|xizmati)"
NUMBER_WORD = rf"(?:bir|ikki|uch|to{APOSTROPHE}rt|besh|olti|yetti|sakkiz|to{APOSTROPHE}qqiz|o{APOSTROPHE}n|\d+)"
MONTH = "(?:yanvar|fevral|mart|aprel|may|iyun|iyul|avgust|sentabr|oktabr|noyabr|dekabr)"
DATE = rf"\b\d{{4}}\s*[-–]\s*yil\s+\d{{1,2}}\s*[-–]\s*{MONTH}(?:ga\s+qadar|dan\s+boshlab|gacha|dagi)?"
RELATIVE = rf"\b{NUMBER_WORD}\s+(?:ish\s+)?(?:kun|oy|yil)(?:i)?\s+(?:muddatda|ichida)"


class Candidate(StrictModel):
    id: str
    text: str
    source_ids: list[str]
    passage_id: str
    role_hint: str


def passage_text(document: Document, passage: Passage) -> str:
    by_id = {span.id: span for span in document.spans}
    return " ".join(by_id[ref].text for ref in passage.span_ids)


def generate_candidates(document: Document) -> list[Candidate]:
    result = []
    seen = set()
    by_id = {span.id: span for span in document.spans}

    def add(text, refs, passage, hint):
        text = text.strip(" ,;:")
        key = (text, tuple(refs), hint)
        if text and key not in seen:
            seen.add(key)
            result.append(Candidate(id=f"c{len(result)}", text=text, source_ids=refs,
                                    passage_id=passage.id, role_hint=hint))

    for passage in document.passages:
        text = passage_text(document, passage)
        refs = passage.span_ids
        # Layout roles are candidate hints, not conclusions about factual roles.
        if passage.kind == "table_row":
            for role, cell_refs in passage.table_cells.items():
                if role in ("executor", "deadline") and cell_refs:
                    value = " ".join(by_id[ref].text for ref in cell_refs)
                    add(value, cell_refs, passage, role)
                    if role == "executor":
                        for member in value.split(","):
                            add(member, cell_refs, passage, role)
        if passage.kind == "header":
            add(text, refs, passage, "organization")
            for ref in refs:
                add(by_id[ref].text, [ref], passage, "organization")
                words = []
                for word in by_id[ref].text.split():
                    if word.isupper() and not any(char.isdigit() for char in word):
                        words.append(word)
                        if word.endswith("NING") and len(words) >= 2:
                            add(" ".join(words), [ref], passage, "organization")
                    else:
                        break
                if len(words) >= 2:
                    add(" ".join(words), [ref], passage, "organization")
            uppercase_refs = []
            for ref in refs:
                value = by_id[ref].text
                if value.isupper() and not any(char.isdigit() for char in value):
                    uppercase_refs.append(ref)
                elif uppercase_refs:
                    break
            if uppercase_refs:
                add(" ".join(by_id[ref].text for ref in uppercase_refs), uppercase_refs, passage, "organization")
        for pattern in (DATE, r"\b\d{1,2}\.\d{1,2}\.\d{4}(?:\s+yilgacha)?", RELATIVE,
                        r"\b\d{4}\s*[-–]\s*yil\s+\d{1,2}\s*[-–]\s*[\w‘’ʻʼ'-]+(?:\s+(?:qadar|boshlab))?",
                        r"\bhar\s+[^.;]{0,120}?(?:qadar|kuni|chorakda|oyda)\b", rf"\bo{APOSTROPHE}z vaqtida\b", r"\bdoimiy\b"):
            for match in re.finditer(pattern, text, re.IGNORECASE):
                add(match.group(), refs, passage, "deadline")
        for match in re.finditer(r"(?:№|\bNo\.?(?=\s|:)|\bnumber:)\s*([\w/-]+)", text, re.IGNORECASE):
            add(match.group(1), refs, passage, "number")
        for match in re.finditer(r"\b\d{1,4}(?:-\d{1,4})?/\d{1,8}\b", text):
            add(match.group(), refs, passage, "number")
        for match in re.finditer(r"\b[A-ZА-Я][a-zа-я]{0,2}\.\s*[A-ZА-Я][\w‘’ʻʼ'-]+", text):
            add(match.group(), refs, passage, "preparer" if passage.kind == "footer" else "person")
            if passage.kind in ("clause", "table_row") or (passage.kind == "paragraph"
                    and re.search(r"\b[\w‘’ʻʼ'-]+sin\b", text)):
                add(match.group(), refs, passage, "executor")
        # Start each organization phrase at its own capitalized word, stop at the first unit noun.
        for match in re.finditer(rf"(?=(\b[A-ZА-Я][^.!?;:]{{0,150}}?\b{UNIT}\b))", text):
            phrase = match.group(1)
            if not re.match(r"^(Mazkur|Ilovada|Topshiriqlar|Bajarilgan)\b", phrase):
                add(phrase, refs, passage, "executor")
        for match in re.finditer(rf"\b(?:hududiy\s+bo{APOSTROPHE}linmalar|mas{APOSTROPHE}ul\s+ijrochilar|loyiha\s+koordinatori|Markaz)\b", text):
            add(match.group(), refs, passage, "executor")
        # Keep full clause prefix candidates when capitalization is damaged by OCR.
        body = re.sub(r"^\d+[.)]\s*", "", text)
        for match in re.finditer(UNIT, body, re.IGNORECASE):
            prefix = body[:match.end()]
            if len(prefix.split()) <= 12 and not re.match(r"^(Mazkur|Ilovada|Topshiriqlar|Bajarilgan)\b", prefix):
                add(prefix, refs, passage, "executor")
    # Reconstruct header column continuations without interleaving a neighboring reply-number column.
    header_refs = {ref: passage for passage in document.passages if passage.kind == "header"
                   for ref in passage.span_ids}
    header_spans = sorted((by_id[ref] for ref in header_refs if by_id[ref].bbox),
                          key=lambda span: (span.page, span.bbox[1], span.bbox[0]))
    for start in header_spans:
        chain = [start]
        for following in header_spans:
            previous = chain[-1]
            if following.page != start.page or following.id in {span.id for span in chain}:
                continue
            height = max(8, previous.bbox[3]-previous.bbox[1])
            gap = following.bbox[1]-previous.bbox[3]
            if -.2*height <= gap <= 1.8*height and abs(following.bbox[0]-start.bbox[0]) <= 1.5*height:
                chain.append(following)
        if len(chain) > 1:
            text = " ".join(span.text for span in chain)
            refs = [span.id for span in chain]
            add(text, refs, header_refs[start.id], "organization")
            if re.search(UNIT, text, re.IGNORECASE):
                add(text, refs, header_refs[start.id], "executor")
    return result
