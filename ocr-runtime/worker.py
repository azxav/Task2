"""Local OCR subprocess. Run in the separately pinned OCR environment."""
import argparse
import csv
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def detect_grid(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY_INV, 35, 12)
    height, width = gray.shape
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                                  cv2.getStructuringElement(cv2.MORPH_RECT, (max(30, width // 12), 1)))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(30, height // 15))))
    grid = cv2.dilate(horizontal | vertical, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    found = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w < width * .35 or h < height * .08:
            continue
        # Hough segments preserve slightly slanted scan borders; axis histograms lose them.
        segments = cv2.HoughLinesP(binary[y:y+h, x:x+w], 1, np.pi / 1800,
                                  threshold=65, minLineLength=min(w, h) * .35, maxLineGap=20)
        x_indices, y_indices = [], []
        for segment in ([] if segments is None else segments[:, 0]):
            x1, y1, x2, y2 = segment
            dx, dy = abs(x2-x1), abs(y2-y1)
            if dx > w * .75 and dy / max(dx, 1) < .05:
                y_indices.append(y + (int(y1)+int(y2))/2)
            elif dy > h * .4 and dx / max(dy, 1) < .05:
                x_indices.append(x + (int(x1)+int(x2))/2)

        def centers(indices, tolerance):
            groups = []
            for index in sorted(indices):
                if not groups or index - groups[-1][-1] > tolerance:
                    groups.append([float(index)])
                else:
                    groups[-1].append(float(index))
            return [sum(group) / len(group) for group in groups]

        xs, ys = centers(x_indices, max(8, w * .015)), centers(y_indices, max(8, w * .015))
        if len(xs) >= 4 and len(ys) >= 3:
            found.append((xs, ys))
    return found


def assemble(records, image, page):
    height, width = image.shape[:2]
    spans = []
    for index, record in enumerate(sorted(records, key=lambda r: (r[1][1], r[1][0]))):
        text, box, _score = record
        if text.strip():
            spans.append({"id": f"p{page}-ocr-{index}", "page": page,
                          "text": " ".join(text.split()), "bbox": [float(x) for x in box], "parent_id": None})
    rows = []
    diagnostics = []
    for table_index, (xs, ys) in enumerate(detect_grid(image), 1):
        cells = []
        for row in range(len(ys)-1):
            columns = []
            for col in range(len(xs)-1):
                references = [span["id"] for span in spans
                              if xs[col] <= (span["bbox"][0] + span["bbox"][2]) / 2 <= xs[col+1]
                              and ys[row] <= (span["bbox"][1] + span["bbox"][3]) / 2 <= ys[row+1]]
                columns.append(references)
            cells.append(columns)
        by_id = {span["id"]: span for span in spans}
        roles = []
        for references in cells[0]:
            header = " ".join(by_id[ref]["text"] for ref in references).casefold()
            header = re.sub(r"[^a-z]", "", header)
            if "muddat" in header:
                roles.append("deadline")
            elif "ijrochi" in header or "masul" in header:
                roles.append("executor")
            elif "topshiriq" in header or "choratadbir" in header:
                roles.append("instruction")
            elif "natija" in header:
                roles.append("deliverable")
            else:
                roles.append("reference")
        if not {"instruction", "executor", "deadline"} <= set(roles):
            diagnostics.append(f"Page {page}: table header recognition incomplete; manual review needed")
            continue
        # Header fragments must not become body obligations.
        header_ids = {ref for refs in cells[0] for ref in refs}
        for span in spans:
            if span["id"] in header_ids:
                span["text"] = "[Table header] " + span["text"]
        for index, cell in enumerate(cells[1:], 1):
            row_cells = {role: refs for role, refs in zip(roles, cell)}
            rows.append({"id": f"p{page}-ocr-table{table_index}-row{index}",
                         "reference": f"table-{table_index}/row-{index}", "cells": row_cells})
    return {"page": page, "width": width, "height": height, "spans": spans,
            "rows": rows, "diagnostics": diagnostics,
            "raw_result": {"records": [{"text": text, "bbox": list(map(float, box)), "score": float(score)}
                                      for text, box, score in records]}}


def paddle_v5(image_path):
    from paddleocr import PaddleOCR
    root = Path(os.environ["OCR_MODEL_ROOT"])
    ocr = PaddleOCR(text_detection_model_name="PP-OCRv5_mobile_det",
                    text_recognition_model_name="latin_PP-OCRv5_mobile_rec",
                    text_detection_model_dir=str(root / "PP-OCRv5_mobile_det"),
                    text_recognition_model_dir=str(root / "latin_PP-OCRv5_mobile_rec"),
                    use_doc_orientation_classify=False, use_doc_unwarping=False,
                    use_textline_orientation=False, device="cpu")
    records = []
    for result in ocr.predict(str(image_path)):
        for text, polygon, score in zip(result["rec_texts"], result["rec_polys"], result["rec_scores"]):
            polygon = np.asarray(polygon)
            records.append((text, [polygon[:, 0].min(), polygon[:, 1].min(),
                                   polygon[:, 0].max(), polygon[:, 1].max()], float(score)))
    return records


def paddle_vl(image_path, image, page):
    from paddleocr import PaddleOCRVL

    from doc_tasks.ocr_layout import parse_vl_page
    root = Path(os.environ["OCR_MODEL_ROOT"])
    height, width = image.shape[:2]
    if max(height, width) > 1700:
        scale = 1700 / max(height, width)
        image = cv2.resize(image, (round(width*scale), round(height*scale)), interpolation=cv2.INTER_AREA)
        image_path = image_path.with_name(image_path.stem + "-vl.png")
        cv2.imwrite(str(image_path), image)
    pipeline = PaddleOCRVL(pipeline_version="v1.6", device="gpu:0",
                           layout_detection_model_dir=str(root / "PP-DocLayoutV3"),
                           vl_rec_model_dir=str(root / "PaddleOCR-VL-1.6"),
                           use_doc_orientation_classify=False, use_doc_unwarping=False)
    results = list(pipeline.predict(str(image_path), max_new_tokens=1536, merge_layout_blocks=False))
    if len(results) != 1:
        raise ValueError("Expected one local VL page result")
    raw = results[0].json
    if "res" in raw:
        raw = raw["res"]
    return parse_vl_page(raw, page, detect_grid(image)).model_dump()


def tesseract(image_path):
    binary = os.environ["TESSERACT_BIN"]
    command = [binary, str(image_path), "stdout", "--tessdata-dir", os.environ["TESSDATA_DIR"],
               "-l", "uzb+eng", "--psm", "3", "-c", "tessedit_create_tsv=1"]
    response = subprocess.run(command, capture_output=True, check=True)
    words = list(csv.DictReader(io.StringIO(response.stdout.decode("utf-8")), delimiter="\t"))
    groups = {}
    for word in words:
        if word.get("text", "").strip() and float(word["conf"]) >= 0:
            key = (word["block_num"], word["par_num"], word["line_num"])
            groups.setdefault(key, []).append(word)
    records = []
    for line in groups.values():
        fragments = [[]]
        for word in sorted(line, key=lambda w: int(w["left"])):
            if fragments[-1]:
                previous = fragments[-1][-1]
                if int(word["left"]) - int(previous["left"]) - int(previous["width"]) > 45:
                    fragments.append([])
            fragments[-1].append(word)
        for fragment in fragments:
            text = " ".join(word["text"] for word in fragment)
            box = [min(int(w["left"]) for w in fragment), min(int(w["top"]) for w in fragment),
                   max(int(w["left"]) + int(w["width"]) for w in fragment),
                   max(int(w["top"]) + int(w["height"]) for w in fragment)]
            records.append((text, box, np.mean([float(w["conf"]) for w in fragment]) / 100))
    return records


def main():
    from doc_tasks.network import install_local_network_guard
    install_local_network_guard()
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=["paddle-v5", "paddle-vl", "tesseract"], required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--page", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    image = cv2.imread(str(args.image))
    if image is None:
        raise ValueError("Cannot read page image")
    if args.engine == "paddle-vl":
        result = paddle_vl(args.image, image, args.page)
    else:
        records = paddle_v5(args.image) if args.engine == "paddle-v5" else tesseract(args.image)
        result = assemble(records, image, args.page)
    args.output.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
