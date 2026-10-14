"""Shared table header vocabulary, independent of PDF/OCR runtimes."""
import re


def table_role(header):
    normalized = re.sub(r"[^a-z]", "", (header or "").casefold())
    if "muddat" in normalized or "deadline" in normalized:
        return "deadline"
    if "ijrochi" in normalized or "executor" in normalized or "masul" in normalized:
        return "executor"
    if "topshiriq" in normalized or "instruction" in normalized or "choratadbir" in normalized:
        return "instruction"
    if "natija" in normalized:
        return "deliverable"
    return "reference"
