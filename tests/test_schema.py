import pytest
from pydantic import ValidationError

from doc_tasks.schema import FieldValue, TaskRecord


def test_supported_field_requires_evidence():
    with pytest.raises(ValidationError):
        FieldValue(text="IT Department", source_ids=[])


def test_missing_field_is_not_specified():
    value = FieldValue.missing()
    assert value.text is None
    assert value.status == "not_specified"


def test_multiple_executors_and_verbatim_deadline():
    task = TaskRecord(
        id="t1",
        kinds=["execution"],
        instruction=FieldValue(text="Develop and submit the draft.", source_ids=["p1"]),
        executors=[
            FieldValue(text="IT Department", source_ids=["p1"]),
            FieldValue(text="Legal Department", source_ids=["p1"]),
        ],
        deadline=FieldValue(text="uch ish kuni ichida", source_ids=["p1"]),
    )
    data = task.model_dump()
    assert len(data["executors"]) == 2
    assert data["deadline"]["text"] == "uch ish kuni ichida"


def test_supported_field_cannot_be_empty():
    with pytest.raises(ValidationError):
        FieldValue(text="  ", source_ids=["p1"])
