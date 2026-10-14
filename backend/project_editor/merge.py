"""Pure three-way merge of one editor's fields against a fresh upstream read."""

from dataclasses import dataclass
from typing import TypeVar

from project_editor.contracts import EditableFieldName, EditableFields

T = TypeVar("T")


@dataclass(frozen=True)
class MergeResult:
    merged: EditableFields
    conflicts: list[EditableFieldName]
    changed: bool


def _choose(base: T, proposed: T, current: T) -> tuple[T, bool]:
    if proposed == base:
        return current, False
    if current != base and current != proposed:
        return current, True
    return proposed, False


def merge_edit(
    base: EditableFields, proposed: EditableFields, current: EditableFields
) -> MergeResult:
    name, name_conflict = _choose(base.name, proposed.name, current.name)
    sector, sector_conflict = _choose(base.sector, proposed.sector, current.sector)
    country, country_conflict = _choose(base.country, proposed.country, current.country)
    stage, stage_conflict = _choose(base.stage, proposed.stage, current.stage)
    key_dates, dates_conflict = _choose(
        base.key_dates, proposed.key_dates, current.key_dates
    )
    conflicts: list[EditableFieldName] = []
    if name_conflict:
        conflicts.append("name")
    if sector_conflict:
        conflicts.append("sector")
    if country_conflict:
        conflicts.append("country")
    if stage_conflict:
        conflicts.append("stage")
    if dates_conflict:
        conflicts.append("key_dates")
    merged = EditableFields(
        name=name,
        sector=sector,
        country=country,
        stage=stage,
        key_dates=key_dates,
    )
    return MergeResult(merged=merged, conflicts=conflicts, changed=merged != current)
