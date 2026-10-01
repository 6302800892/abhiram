# migrations/ — append-only schema history (NFR-05)

- Files are named `NNNN_snake_case.sql`, contiguous from `0001`. They are applied in order at
  startup by `src/repository/db.py::apply_migrations`.
- **Never edit an existing file.** Its SHA-256 is recorded in `schema_migrations`, and a change
  raises `MigrationTamperedError` at startup. The `append-only-migration-check` hook blocks the
  edit.
- To change the schema, add the next number. SQLite has limited ALTER, so prefer additive
  changes: new tables, new nullable columns.
- Each new append-only table gets both triggers (`trg_<t>_no_update`, `trg_<t>_no_delete`) and an
  entry in `src/repository/schema.py::APPEND_ONLY_TABLES`.
- Money columns are `TEXT`, never `REAL`.
