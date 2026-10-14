from project_editor.contracts import EditableFields
from project_editor.merge import merge_edit


def fields(**changes: object) -> EditableFields:
    values: dict[str, object] = {
        "name": "Original",
        "sector": "energy",
        "country": "Chile",
        "stage": "idea",
        "key_dates": [{"label": "Tender", "date": "2027-01-01"}],
    }
    return EditableFields.model_validate(values | changes)


def test_merges_changes_to_different_fields() -> None:
    result = merge_edit(fields(), fields(name="Updated"), fields(country="Peru"))

    assert result.conflicts == []
    assert result.changed is True
    assert result.merged.name == "Updated"
    assert result.merged.country == "Peru"


def test_reports_only_overlapping_fields_and_keeps_current_for_review() -> None:
    current = fields(name="First editor", country="Peru")
    result = merge_edit(fields(), fields(name="Second editor", country="Peru"), current)

    assert result.conflicts == ["name"]
    assert result.merged.name == "First editor"
    assert result.merged.country == "Peru"


def test_equal_proposed_and_current_is_already_resolved() -> None:
    result = merge_edit(fields(), fields(name="Agreed"), fields(name="Agreed"))

    assert result.conflicts == []
    assert result.changed is False


def test_key_dates_are_one_conflict_field() -> None:
    proposed = fields(key_dates=[{"label": "Mine", "date": "2028-01-01"}])
    current = fields(key_dates=[{"label": "Theirs", "date": "2029-01-01"}])

    result = merge_edit(fields(), proposed, current)

    assert result.conflicts == ["key_dates"]
    assert result.merged.key_dates == current.key_dates
