"""Exercise the user-facing project flow through the Docker/Nginx endpoint."""

from __future__ import annotations

import argparse
import copy
import json
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

EDITABLE_FIELDS = ("name", "sector", "country", "stage", "key_dates")


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    body: Mapping[str, Any] | None = None,
) -> tuple[int, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        payload = response.read()
        parsed = json.loads(payload) if payload else None
        status = response.status
        if status is None:
            raise RuntimeError("The HTTP response did not include a status code")
        return status, parsed


def editable(project: Mapping[str, Any]) -> dict[str, Any]:
    return {field: copy.deepcopy(project[field]) for field in EDITABLE_FIELDS}


def expect_status(expected: int, actual: int, payload: Any) -> None:
    if actual != expected:
        raise AssertionError(f"Expected HTTP {expected}, got {actual}: {payload!r}")


def run(base_url: str) -> None:
    with urlopen(f"{base_url.rstrip('/')}/", timeout=10) as page:
        expect_status(200, page.status, page.read().decode("utf-8"))

    status, payload = request_json(base_url, "/api/projects")
    expect_status(200, status, payload)
    projects = payload["projects"]
    if len(projects) != 30:
        raise AssertionError(f"Expected 30 projects, got {len(projects)}")

    project_id = projects[0]["id"]
    status, payload = request_json(base_url, f"/api/projects/{project_id}")
    expect_status(200, status, payload)
    original = payload["project"]
    if "linked_companies" in original:
        raise AssertionError("The browser response exposed linked_companies")
    original_fields = editable(original)

    try:
        status, saved = request_json(
            base_url,
            f"/api/projects/{project_id}",
            method="PUT",
            body={
                "base": original_fields,
                "proposed": original_fields | {"name": "Docker smoke editor A"},
            },
        )
        expect_status(200, status, saved)

        status, saved = request_json(
            base_url,
            f"/api/projects/{project_id}",
            method="PUT",
            body={
                "base": original_fields,
                "proposed": original_fields | {"country": "Peru"},
            },
        )
        expect_status(200, status, saved)
        current = saved["project"]
        if current["name"] != "Docker smoke editor A" or current["country"] != "Peru":
            raise AssertionError("Different-field stale edits did not both survive")

        status, conflict = request_json(
            base_url,
            f"/api/projects/{project_id}",
            method="PUT",
            body={
                "base": original_fields,
                "proposed": original_fields | {"name": "Docker smoke editor B"},
            },
        )
        expect_status(409, status, conflict)
        if conflict["conflicting_fields"] != ["name"]:
            raise AssertionError(f"Unexpected conflicts: {conflict!r}")

        current_fields = editable(current)
        expanded_dates = current_fields["key_dates"] + [
            {"label": "Docker smoke date", "date": "2030-04-05"}
        ]
        status, saved = request_json(
            base_url,
            f"/api/projects/{project_id}",
            method="PUT",
            body={
                "base": current_fields,
                "proposed": current_fields | {"key_dates": expanded_dates},
            },
        )
        expect_status(200, status, saved)
        dated = saved["project"]
        dated_fields = editable(dated)
        reduced_dates = [
            item
            for item in dated_fields["key_dates"]
            if item["label"] != "Docker smoke date"
        ]
        status, saved = request_json(
            base_url,
            f"/api/projects/{project_id}",
            method="PUT",
            body={
                "base": dated_fields,
                "proposed": dated_fields | {"key_dates": reduced_dates},
            },
        )
        expect_status(200, status, saved)

        latest_fields = editable(saved["project"])
        status, error = request_json(
            base_url,
            f"/api/projects/{project_id}",
            method="PUT",
            body={
                "base": latest_fields,
                "proposed": latest_fields
                | {"key_dates": [{"label": "Invalid", "date": "2030-02-31"}]},
            },
        )
        expect_status(422, status, error)
    finally:
        status, latest = request_json(base_url, f"/api/projects/{project_id}")
        expect_status(200, status, latest)
        latest_fields = editable(latest["project"])
        if latest_fields != original_fields:
            status, restored = request_json(
                base_url,
                f"/api/projects/{project_id}",
                method="PUT",
                body={"base": latest_fields, "proposed": original_fields},
            )
            expect_status(200, status, restored)

    print(
        "PASS: UI, list/show, distinct stale edits, same-field conflict, key-date add/remove, "
        "validation, and original-data restoration."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8082")
    run(parser.parse_args().base_url)
