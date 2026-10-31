"""Data model: taxonomy, objects, documents, run state and the structured answers requested from the LLM."""

from __future__ import annotations

import hashlib
import json
from typing import Literal, Optional

from pydantic import BaseModel, Field

from .config import InputSpec

NO_INFO = "no_information"   # the passages say nothing about the dimension for the object
MISFIT = "misfit"            # the passages concern the dimension, but no characteristic fits the object

# --------------------------------------------------------------------------- taxonomy


class Characteristic(BaseModel):
    id: str
    name: str
    definition: str = ""
    negation: bool = False                                       # e.g. "none": closes the dimension
    origin: Literal["empirical", "conceptual"] = "empirical"
    derived_from: list[str] = Field(default_factory=list)       # elements it replaces (split, merge, promote, demote)
    iteration: int = 0


class Dimension(BaseModel):
    id: str
    name: str
    definition: str = ""
    application_rule: str = ""
    perspective: str = ""
    characteristics: list[Characteristic] = Field(default_factory=list)
    origin: Literal["empirical", "conceptual"] = "empirical"
    derived_from: list[str] = Field(default_factory=list)
    iteration: int = 0

    def characteristic(self, cid: str) -> Optional[Characteristic]:
        return next((c for c in self.characteristics if c.id == cid), None)

    def signature(self) -> str:
        """Fingerprint of the structure a classification depends on (the characteristics and their kind): when it
        changes, the cells of the dimension are stale."""
        data = [[(c.id, c.negation) for c in self.characteristics]]
        return hashlib.sha1(json.dumps(data).encode()).hexdigest()[:16]

    def wording(self) -> str:
        """Fingerprint of the names, definitions and application rule. A change of wording keeps the cells that name
        a characteristic; only the cells without one (misfit, no information) are examined again."""
        data = [self.name, self.definition, self.application_rule,
                [(c.name, c.definition) for c in self.characteristics]]
        return hashlib.sha1(json.dumps(data).encode()).hexdigest()[:16]


class Taxonomy(BaseModel):
    """Dimensions grouped in perspectives. Identifiers are permanent and never reused."""

    dimensions: list[Dimension] = Field(default_factory=list)
    next_dimension: int = 1
    next_characteristic: dict[str, int] = Field(default_factory=dict)

    def dimension(self, did: str) -> Optional[Dimension]:
        return next((d for d in self.dimensions if d.id == did), None)

    def locate(self, cid: str) -> tuple[Optional[Dimension], Optional[Characteristic]]:
        for d in self.dimensions:
            c = d.characteristic(cid)
            if c is not None:
                return d, c
        return None, None

    def new_dimension_id(self) -> str:
        did = f"D{self.next_dimension}"
        self.next_dimension += 1
        return did

    def new_characteristic_id(self, did: str) -> str:
        n = self.next_characteristic.get(did, 1)
        self.next_characteristic[did] = n + 1
        return f"{did}.C{n}"

    def element_ids(self) -> set[str]:
        return {d.id for d in self.dimensions} | {c.id for d in self.dimensions for c in d.characteristics}


# --------------------------------------------------------------------------- objects and documents


class Evidence(BaseModel):
    doc_id: str
    quote: str
    page: Optional[int] = None


class Cell(BaseModel):
    """Classification of one object in one dimension."""

    value: str = NO_INFO                                   # characteristic id, MISFIT or NO_INFO
    key: str = ""                                          # structure signature of the dimension when classified
    text: str = ""                                         # wording of the dimension when classified


class DomainObject(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str = ""
    evidence: list[Evidence] = Field(default_factory=list)  # passages that mention the object
    mentions: int = 0
    iteration: int = 0
    role: Literal["building", "evaluation"] = "building"
    cells: dict[str, Cell] = Field(default_factory=dict)   # dimension id -> classification


class Document(BaseModel):
    id: str
    source: Literal["scholarly", "web", "llm"]
    title: str = ""
    url: Optional[str] = None
    doi: Optional[str] = None
    year: Optional[int] = None
    query: str = ""
    iteration: int = 0
    status: Literal["processed", "no_fulltext", "too_short"] = "processed"


class Code(BaseModel):
    """A characteristic of an object coded in Step 8e (open coding)."""

    id: str
    object_id: str
    label: str
    definition: str = ""


class Concept(BaseModel):
    """A dimension or characteristic proposed in the literature (Step 7c)."""

    id: str
    kind: Literal["dimension", "characteristic"]
    name: str
    definition: str = ""
    dimension: str = ""        # for a characteristic: the dimension the source assigns it to
    doc_id: str = ""


class OperationLog(BaseModel):
    iteration: int
    op: str
    targets: list[str] = Field(default_factory=list)
    created: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    reason: str = ""


class IterationRecord(BaseModel):
    number: int
    kind: Literal["c", "e", "r"]                  # conceptual-to-empirical, empirical-to-conceptual, revision
    reason: str = ""
    queries: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    new_objects: list[str] = Field(default_factory=list)
    codes: int = 0
    concepts: int = 0
    attempts: list[list[str]] = Field(default_factory=list)   # violations of each proposal ([] = valid)
    rejected: bool = False
    operations: list[OperationLog] = Field(default_factory=list)
    cells_classified: int = 0
    meta_review: str = ""
    objective: dict[str, bool] = Field(default_factory=dict)
    objective_details: dict[str, str] = Field(default_factory=dict)
    subjective: dict[str, dict] = Field(default_factory=dict)
    evaluation: dict = Field(default_factory=dict)
    exit: Optional[str] = None                                  # failed check: "12", "14" or "17"
    entry: Optional[str] = None                                 # re-entry chosen: "4", "6" or "10"
    entry_reason: str = ""
    tokens: int = 0


class Work(BaseModel):
    """Intermediate results of the current iteration."""

    new_object_ids: list[str] = Field(default_factory=list)
    codes: list[Code] = Field(default_factory=list)
    concepts: list[Concept] = Field(default_factory=list)
    proposal: Optional[Taxonomy] = None
    operations: list[OperationLog] = Field(default_factory=list)


class RunState(BaseModel):
    run_id: str
    status: Literal["running", "completed", "max_iterations_reached", "budget_exhausted", "failed"] = "running"
    message: str = ""
    input: InputSpec
    meta_characteristic: Optional[str] = None
    meta_reviewed: bool = False
    evaluation_plan: list[dict] = Field(default_factory=list)
    taxonomy: Taxonomy = Field(default_factory=Taxonomy)
    objects: dict[str, DomainObject] = Field(default_factory=dict)
    next_object: int = 1
    next_code: int = 1
    next_concept: int = 1
    documents: dict[str, Document] = Field(default_factory=dict)
    iterations: list[IterationRecord] = Field(default_factory=list)
    operations_log: list[OperationLog] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)          # open issues: unmet conditions and suggestions
    issues_from: int = 0                                      # iteration that raised them (ids I<iteration>.<n>)
    queries: list[str] = Field(default_factory=list)
    evaluation: dict = Field(default_factory=dict)            # last evaluation (Steps 15–17)
    next_step: str = "1-3"
    work: Work = Field(default_factory=Work)
    tokens_used: int = 0
    tokens_by_step: dict[str, int] = Field(default_factory=dict)
    tokens_by_task: dict[str, int] = Field(default_factory=dict)

    @property
    def current(self) -> IterationRecord:
        return self.iterations[-1]

    def building_objects(self) -> list[DomainObject]:
        return [o for o in self.objects.values() if o.role == "building"]

    def new_object_id(self) -> str:
        oid = f"O{self.next_object}"
        self.next_object += 1
        return oid


# --------------------------------------------------------------------------- answers of the LLM


class MetaOut(BaseModel):
    meta_characteristic: str


class MetaReviewOut(BaseModel):
    keep: bool
    meta_characteristic: str = Field("", description="The refined meta-characteristic when keep is false.")
    reason: str = ""


class QueryOut(BaseModel):
    query: str = Field(description="3 to 8 plain keywords.")


class ObjectOut(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str = ""
    instance: bool = Field(True, description="true only if the object is a named instance of the domain of objects.")


class ObjectsOut(BaseModel):
    objects: list[ObjectOut] = Field(default_factory=list)


class ObjectText(BaseModel):
    name: str
    text: str = Field("", description="Paragraph of sentences, each naming the object and stating a characteristic.")


class DescriptionsOut(BaseModel):
    descriptions: list[ObjectText] = Field(default_factory=list)


class CellOut(BaseModel):
    dimension_id: str
    value: str = Field(description="A characteristic id of the dimension, 'misfit' or 'no_information'.")


class CodeOut(BaseModel):
    label: str
    definition: str = ""


class ObjectExamOut(BaseModel):
    object_id: str
    cells: list[CellOut] = Field(default_factory=list)
    codes: list[CodeOut] = Field(default_factory=list)


class ExamOut(BaseModel):
    objects: list[ObjectExamOut] = Field(default_factory=list)


class ConceptOut(BaseModel):
    kind: Literal["dimension", "characteristic"]
    name: str
    definition: str = ""
    dimension: str = Field("", description="For a characteristic: the dimension the text assigns it to.")


class ConceptsOut(BaseModel):
    concepts: list[ConceptOut] = Field(default_factory=list)


class CharSpec(BaseModel):
    name: str
    definition: str = ""
    negation: bool = False


class DimSpec(BaseModel):
    name: str
    definition: str = ""
    application_rule: str = ""
    perspective: str = ""
    characteristics: list[CharSpec] = Field(default_factory=list)


OPERATIONS = ("add_dimension", "add_characteristic", "rename", "swap", "split", "merge", "promote", "demote", "delete")


class OperationOut(BaseModel):
    op: Literal["add_dimension", "add_characteristic", "rename", "swap", "split", "merge", "promote", "demote",
                "delete"]
    target: list[str] = Field(default_factory=list, description="Ids of the existing elements concerned.")
    name: str = ""
    definition: str = ""
    application_rule: str = ""
    perspective: str = ""
    negation: bool = False
    characteristics: list[CharSpec] = Field(default_factory=list)
    parts: list[DimSpec] = Field(default_factory=list, description="split of a dimension: the new dimensions.")
    evidence: list[str] = Field(default_factory=list, description="Ids of objects, concepts or open issues.")
    reason: str = ""


class OperationsOut(BaseModel):
    operations: list[OperationOut] = Field(default_factory=list)


class JudgeItem(BaseModel):
    condition: Literal["concise", "robust", "comprehensive", "extendible", "explanatory"]
    passed: bool
    justification: str = ""
    suggestions: list[str] = Field(default_factory=list)


class JudgeOut(BaseModel):
    evaluations: list[JudgeItem]


class ChoiceOut(BaseModel):
    choice: str
    reason: str = ""


class BaselineOut(BaseModel):
    meta_characteristic: str = ""
    dimensions: list[DimSpec] = Field(default_factory=list)
