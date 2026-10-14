# Decisions and trade-offs

## Working slice

The deliverable has three browser-facing routes: list projects, show one, and save edits to the four core fields and key dates. The backend narrows wide upstream records for the browser and holds the upstream API key. The frontend uses relative `/api` requests through a local Vite proxy. Search, pagination, authentication, a database, linked-company editing, and visual polish were deferred so the whole editing path could be exercised within the time limit. The cost is a full-list read and a basic single-screen UI.

## Save and conflict model

Each save sends the values originally opened (`base`) and the editor's desired values (`proposed`). The backend reads the latest upstream record, then compares each editable field separately. It preserves current values for untouched fields, applies nonconflicting edits, and returns `409` with the current record and field names for overlapping changes. The editor chooses current or mine for each conflicting field and resubmits on the new base. This stateless contract works across three backend instances and keeps the client and server independently testable. Its cost is a larger request and a second round trip when an editor must resolve conflicts.

The whole `key_dates` array is one conflict field. Rows have no stable IDs, and the upstream replaces the list, so a row-level merge could misread a rename, reorder, or removal. Separate row edits may therefore conflict unnecessarily. The UI still supports adding, editing, and removing rows. The backend sends `linked_companies` from its latest read in the upstream's required full `PUT`; this avoids erasing companies through an old browser snapshot, though a later competing writer can still overwrite that value.

## Safety boundary and uncertain writes

The fresh read and full upstream `PUT` are separate operations. Another backend instance or the nightly importer can write between them. Our merge handles sequential stale editors but cannot guarantee no lost updates for simultaneous writers. A process lock would cover neither other instances nor the importer. A strict guarantee requires upstream revisions with conditional writes, or one transactional write path used by every writer.

An upstream `504` or lost PUT response might follow an applied write. The backend does not retry automatically. It makes one diagnostic read and returns `write_uncertain` with the observed record or null. This avoids a blind second write, at the cost of asking the editor to review and reload. An observed match is only a snapshot, not proof that this request applied or that the value will stay.

## Implementation and verification trade-offs

The small React screen currently keeps view and save state in one `App.tsx`; one frontend owner built it. This reduced integration overhead for the one-hour slice, but separate view components would make future parallel frontend changes easier. The SDD and task DAG identify file-disjoint ownership for that future work.

Ruff, ty, eight backend tests, the frontend build, and the full pre-commit gate pass. The backend tests cover shape and validation, distinct-field and same-field saves, date-list conflicts and edits, linked-company preservation, and both applied and unapplied timeout outcomes. A live local smoke check listed 30 projects, showed one, merged different-field saves, returned a same-field conflict, and reached the backend through Vite's `/api` proxy. Browser interactions were not manually exercised in this environment.

With 50 editors, the read/merge/write race and conflict rate are the first correctness limits. Full-list reads and per-save upstream round trips then become load and latency concerns. Upstream conditional writes are the first production change; list sizing and throughput should be measured before adding pagination or caching.
