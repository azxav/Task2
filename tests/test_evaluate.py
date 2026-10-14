from doc_tasks.evaluate import evaluate


def test_metrics_count_missing_task_and_wrong_executor():
    gold = {"metadata": {"sender": {"text": "Agency"}}, "tasks": [
        {"instruction": "1. Launch system.", "executors": ["IT"], "deadline": "one month", "page": 1},
        {"instruction": "2. Report results.", "executors": ["HR"], "deadline": None, "page": 1},
    ]}
    predicted = {"metadata": {"sender": {"text": "Agency"}}, "tasks": [
        {"instruction": {"text": "1. Launch system."}, "executors": [{"text": "Legal"}],
         "deadline": {"text": "one month"}, "review_reasons": []},
    ]}
    metrics = evaluate(gold, predicted)
    assert metrics["matched_tasks"] == 1
    assert metrics["missed_tasks"] == 1
    assert metrics["spurious_tasks"] == 0
    assert metrics["executor_errors"] == 1
    assert metrics["deadline_errors"] == 0


def test_original_deadline_is_compared_without_date_calculation():
    gold = {"metadata": {}, "tasks": [{"instruction": "Submit report", "executors": [],
                                          "deadline": "uch ish kuni ichida", "page": 1}]}
    predicted = {"metadata": {}, "tasks": [{"instruction": {"text": "Submit report"}, "executors": [],
                                            "deadline": {"text": "2026-09-18"}, "review_reasons": []}]}
    assert evaluate(gold, predicted)["deadline_errors"] == 1
def test_split_compound_instruction_is_counted_as_grouping_error():
    from doc_tasks.evaluate import evaluate
    gold = {"metadata": {}, "tasks": [{"instruction": "Develop the draft and submit it to the Council",
                                       "executors": [], "deadline": None}]}
    predicted = {"metadata": {}, "tasks": [
        {"instruction": {"text": "Develop the draft"}, "executors": [], "deadline": {"text": None}},
        {"instruction": {"text": "submit it to the Council"}, "executors": [], "deadline": {"text": None}}]}
    assert evaluate(gold, predicted)["grouping_errors"] == 1
