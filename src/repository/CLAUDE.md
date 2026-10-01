# src/repository/ — SQLite data access

- Functions take an open `sqlite3.Connection` and **never commit**. The calling service wraps
  writes in `with conn:`.
- Parameterised SQL only (`?` / `:name`). Never use string-formatted values.
- Money columns are TEXT written with `money_str()` and read with `to_money()`.
- Append-only tables are listed in `schema.py::APPEND_ONLY_TABLES`. Never write UPDATE or DELETE
  against them. The DB triggers would abort anyway, and `tests/architecture/test_append_only.py`
  checks the triggers exist.
- The current state of an append-only stream is its latest row (highest `seq` / `version`).
- Schema changes go in a **new** `migrations/NNNN_*.sql` (see `migrations/CLAUDE.md`).
