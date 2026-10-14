"""Extraction metrics against manually checked reference outputs."""
import re
from difflib import SequenceMatcher


def normalize(text):
    if text is None:
        return ""
    text = re.sub(r"[‘’ʻʼ`´]", "'", text)
    return " ".join(text.casefold().split())


def _text(value):
    return value.get("text") if isinstance(value, dict) else value


def _instruction(task):
    return re.sub(r"^\d+[.)]\s*", "", normalize(_text(task["instruction"])))


def evaluate(gold: dict, predicted: dict) -> dict:
    pairs = []
    for gi, expected in enumerate(gold["tasks"]):
        for pi, actual in enumerate(predicted["tasks"]):
            similarity = SequenceMatcher(None, _instruction(expected), _instruction(actual)).ratio()
            if similarity >= .65:
                pairs.append((similarity, gi, pi))
    matched_gold, matched_predicted = set(), set()
    matches = []
    for similarity, gi, pi in sorted(pairs, reverse=True):
        if gi not in matched_gold and pi not in matched_predicted:
            matched_gold.add(gi)
            matched_predicted.add(pi)
            matches.append((gi, pi, similarity))
    executor_errors = 0
    deadline_errors = 0
    instruction_errors = 0
    kind_errors = 0
    details = []
    for gi, pi, similarity in matches:
        expected, actual = gold["tasks"][gi], predicted["tasks"][pi]
        executor_wrong = {normalize(_text(x)) for x in expected["executors"]} != {
            normalize(_text(x)) for x in actual["executors"]
        }
        deadline_wrong = normalize(_text(expected["deadline"])) != normalize(_text(actual["deadline"]))
        instruction_wrong = _instruction(expected) != _instruction(actual)
        kind_wrong = "kinds" in expected and set(expected["kinds"]) != set(actual.get("kinds", []))
        executor_errors += executor_wrong
        deadline_errors += deadline_wrong
        instruction_errors += instruction_wrong
        kind_errors += kind_wrong
        details.append({"gold_index": gi, "prediction_index": pi, "similarity": similarity,
                        "executor_wrong": executor_wrong, "deadline_wrong": deadline_wrong,
                        "instruction_wording_wrong": instruction_wrong, "kind_wrong": kind_wrong})
    metadata = {key: normalize(_text(value)) == normalize(_text(predicted["metadata"].get(key)))
                for key, value in gold["metadata"].items()}
    expected_texts = [_instruction(t).rstrip(".") for t in gold["tasks"]]
    actual_texts = [_instruction(t).rstrip(".") for t in predicted["tasks"]]
    split_groups = sum(sum(len(a) >= 10 and a in e for a in actual_texts) >= 2 for e in expected_texts)
    merged_groups = sum(sum(len(e) >= 10 and e in a for e in expected_texts) >= 2 for a in actual_texts)
    return {
        "expected_tasks": len(gold["tasks"]), "predicted_tasks": len(predicted["tasks"]),
        "matched_tasks": len(matches), "missed_tasks": len(gold["tasks"])-len(matches),
        "spurious_tasks": len(predicted["tasks"])-len(matches), "executor_errors": executor_errors,
        "deadline_errors": deadline_errors, "instruction_wording_errors": instruction_errors,
        "kind_errors": kind_errors, "metadata_correct": sum(metadata.values()), "metadata_fields": len(metadata),
        "grouping_errors": split_groups + merged_groups,
        "grouping_splits": split_groups, "grouping_merges": merged_groups,
        "metadata": metadata, "matched_details": details,
        "unmatched_gold_indices": [i for i in range(len(gold["tasks"])) if i not in matched_gold],
        "unmatched_prediction_indices": [i for i in range(len(predicted["tasks"])) if i not in matched_predicted],
        "review_tasks": sum(bool(task.get("review_reasons")) for task in predicted["tasks"]),
        "matching_note": "Greedy instruction-similarity matching >=0.65; inspect ambiguous matches manually",
    }
