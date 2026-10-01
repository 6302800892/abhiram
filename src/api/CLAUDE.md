# src/api/ — controllers (authentication boundary, NFR-04)

- Routers live in `routes/*_routes.py` and are registered in `src/main.py::ROUTERS`.
- **Every** handler takes a guard alias from `deps.py`: `CustomerUser`, `HospitalUser`,
  `InsurerUser`, `AdminUser`, `StaffUser`, `CaseViewer` or `AnyUser`. Only login and register are
  public, and they are marked `# public-endpoint`. Checked by the `role-boundary-check` hook and
  `tests/architecture/test_controllers_guarded.py`.
- Request bodies are `schemas.py` models with `extra="forbid"`. Money fields use the `Money` /
  `Percent` types, which reject JSON floats.
- Controllers stay thin: parse, call one service function, return its dict. No SQL here.
- Errors come from domain exceptions, mapped in `errors.py` to `{"error":{"code","message"}}`.
  Validation errors never echo submitted values (PHI).
- `middleware.py` binds `X-Correlation-ID`. Services bind `case_id` for log lines.
