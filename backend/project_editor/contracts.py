"""The browser-facing API contract and the upstream fields we consume."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Sector = Literal["energy", "mining", "water", "transport", "oil_and_gas", "ict"]
Stage = Literal[
    "idea",
    "feasibility",
    "tender",
    "financing",
    "construction",
    "operation",
    "cancelled",
]
CompanyRole = Literal["owner", "developer", "epc_contractor", "financier", "consultant"]
EditableFieldName = Literal["name", "sector", "country", "stage", "key_dates"]


class KeyDate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    date: date

    @field_validator("label")
    @classmethod
    def nonblank_label(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("label must not be blank")
        return value


class EditableFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    sector: Sector
    country: str = Field(min_length=1)
    stage: Stage
    key_dates: list[KeyDate]

    @field_validator("name", "country")
    @classmethod
    def nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


class ProjectDetail(EditableFields):
    id: str


class ProjectSummary(BaseModel):
    id: str
    name: str
    sector: Sector
    country: str
    stage: Stage


class LinkedCompany(BaseModel):
    name: str
    role: CompanyRole


class StoredProject(ProjectDetail):
    """Accept wide upstream records, retaining the hidden field required by PUT."""

    model_config = ConfigDict(extra="ignore")

    linked_companies: list[LinkedCompany]

    def detail(self) -> ProjectDetail:
        return ProjectDetail.model_validate(
            self.model_dump(exclude={"linked_companies"})
        )

    def summary(self) -> ProjectSummary:
        return ProjectSummary.model_validate(self.model_dump())


class ProjectListResponse(BaseModel):
    projects: list[ProjectSummary]


class ProjectResponse(BaseModel):
    project: ProjectDetail


class SaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base: EditableFields
    proposed: EditableFields


class ConflictResponse(BaseModel):
    code: Literal["edit_conflict"] = "edit_conflict"
    current: ProjectDetail
    conflicting_fields: list[EditableFieldName]


class UncertainResponse(BaseModel):
    code: Literal["write_uncertain"] = "write_uncertain"
    observed: ProjectDetail | None
