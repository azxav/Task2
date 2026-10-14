"""Convert local VL page blocks and HTML tables to source-grounded cells."""
import re
from html.parser import HTMLParser

from .ocr import OCRPage, TableRow
from .roles import table_role
from .schema import SourceSpan


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = []
        self.cell = None
        self.merged = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        if tag in ("td", "th"):
            self.cell = []
            self.merged |= any(k in ("rowspan", "colspan") and v != "1" for k, v in attrs)
        if tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).replace("\\n", " ").split()))
            self.cell = None
        if tag == "tr":
            self.rows.append(self.row)


def plain_ocr_text(text):
    def plain(match):
        original = match.group(0)
        content = match.group(1)
        for _ in range(4):
            content = re.sub(r"\\+(?:underline|text|mathrm|textrm)\{([^{}]*)\}", r"\1", content)
        return content.strip() if not re.search(r"[\\{}]", content) else original
    return re.sub(r"\$\s*([^$]*\\+(?:underline|text|mathrm|textrm)[^$]*)\s*\$", plain, text)


def parse_vl_page(raw: dict, page: int, grids=()) -> OCRPage:
    spans, rows, diagnostics = [], [], []
    table_index = 0
    for index, block in enumerate(raw["parsing_res_list"]):
        box = tuple(float(v) for v in block["block_bbox"])
        content = " ".join(plain_ocr_text(block["block_content"]).split())
        if block["block_label"] != "table":
            if content:
                spans.append(SourceSpan(id=f"p{page}-vl-{index}", page=page, text=content, bbox=box))
            continue
        table_index += 1
        parser = TableParser()
        parser.feed(block["block_content"])
        if len(parser.rows) < 2:
            diagnostics.append(f"Page {page}: unreadable VL table")
            continue
        roles = [table_role(cell) for cell in parser.rows[0]]
        # OCR uses Mas'ul headers as well as ijrochi.
        roles = ["executor" if "mas" in cell.casefold() and role == "reference" else role
                 for cell, role in zip(parser.rows[0], roles)]
        if "instruction" not in roles or parser.merged:
            diagnostics.append(f"Page {page}: merged or unrecognized VL table requires review")
            spans.append(SourceSpan(id=f"p{page}-vl-table-{index}", page=page,
                                    text=" ".join(" ".join(row) for row in parser.rows), bbox=box))
            continue
        grid = next(((xs, ys) for xs, ys in grids if len(xs)-1 == len(roles)
                     and len(ys)-1 == len(parser.rows) and abs(xs[0]-box[0]) < 40), None)
        if grid is None:
            diagnostics.append(f"Page {page}: VL cell text linked to table box; exact cell geometry unavailable")
        for r, values in enumerate(parser.rows[1:], 1):
            if len(values) != len(roles):
                diagnostics.append(f"Page {page}, table {table_index}, row {r}: unequal cell count")
                continue
            cells = {}
            for col, (role, text) in enumerate(zip(roles, values)):
                cells.setdefault(role, [])
                if not text:
                    continue
                ref = f"p{page}-vl-table{table_index}-r{r}-c{col}"
                geometry = (grid[0][col], grid[1][r], grid[0][col+1], grid[1][r+1]) if grid else box
                spans.append(SourceSpan(id=ref, page=page, text=text, bbox=geometry))
                cells[role].append(ref)
            rows.append(TableRow(id=f"p{page}-vl-table{table_index}-row{r}",
                                 reference=f"table-{table_index}/row-{values[0]}", cells=cells))
    spans.sort(key=lambda s: (s.bbox[1], s.bbox[0]))
    original = {key: value for key, value in raw.items() if key != "input_path"}
    return OCRPage(page=page, width=raw["width"], height=raw["height"], spans=spans,
                   rows=rows, diagnostics=diagnostics, raw_result=original)
