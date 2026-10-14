import re


def explicit_action(text):
    return bool(re.search(
        r"\b[\w‘’ʻʼ'-]+sin\b|\b(?:so[‘’ʻʼ']raymiz|so[‘’ʻʼ']raladi|must|shall|required)\b",
        text, re.IGNORECASE))
