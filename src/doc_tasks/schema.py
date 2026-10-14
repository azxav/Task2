from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceSpan(StrictModel):
    id: str
    page: int = Field(ge=1)
    text: str
    bbox: tuple[float, float, float, float] | None = None
    parent_id: str | None = None


class Passage(StrictModel):
    id: str
    kind: Literal["header", "paragraph", "clause", "table_row", "footer", "heading"]
    span_ids: list[str]
    clause_ref: str | None = None
    table_cells: dict[str, list[str]] = Field(default_factory=dict)


class Document(StrictModel):
    spans: list[SourceSpan]
    passages: list[Passage]
    warnings: list[str] = Field(default_factory=list)
    provenance: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_references(self):
        ids = {span.id for span in self.spans}
        if len(ids) != len(self.spans):
            raise ValueError("Duplicate source IDs")
        for passage in self.passages:
            if not passage.span_ids or not set(passage.span_ids) <= ids:
                raise ValueError("Passage has missing source references")
            if any(not set(refs) <= ids for refs in passage.table_cells.values()):
                raise ValueError("Table cell has missing source references")
        return self


class FieldValue(StrictModel):
    text: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    status: Literal["supported", "not_specified", "needs_review"] = "supported"

    @model_validator(mode="after")
    def evidence_required(self):
        if self.status == "supported" and (
            self.text is None or not self.text.strip() or not self.source_ids
        ):
            raise ValueError("Supported fields require nonempty text and source evidence")
        if self.status == "not_specified" and (self.text is not None or self.source_ids):
            raise ValueError("Unspecified fields cannot contain asserted values")
        if self.text is not None and not self.source_ids:
            raise ValueError("Populated fields require evidence even when ambiguous")
        return self

    @classmethod
    def missing(cls):
        return cls(status="not_specified")


class TaskRecord(StrictModel):
    id: str
    kinds: list[Literal["execution", "approval", "oversight", "reporting", "other"]]
    instruction: FieldValue
    executors: list[FieldValue] = Field(default_factory=list)
    deadline: FieldValue = Field(default_factory=FieldValue.missing)
    clause_ref: str | None = None
    review_reasons: list[str] = Field(default_factory=list)


class Metadata(StrictModel):
    sender: FieldValue = Field(default_factory=FieldValue.missing)
    number: FieldValue = Field(default_factory=FieldValue.missing)
    date: FieldValue = Field(default_factory=FieldValue.missing)
    signer: FieldValue = Field(default_factory=FieldValue.missing)


class AnalysisResult(StrictModel):
    metadata: Metadata
    tasks: list[TaskRecord]
    sources: list[SourceSpan] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_source_references(self):
        source_ids = {source.id for source in self.sources}
        fields = list(self.metadata.__dict__.values())
        for task in self.tasks:
            fields.extend([task.instruction, task.deadline, *task.executors])
        for value in fields:
            if not set(value.source_ids) <= source_ids:
                raise ValueError("Result refers to nonexistent source evidence")
        return self
