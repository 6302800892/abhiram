# PM-001 — Debugging log: environment-first resolution

Project-specific debugging log for MediCard. Each incident was resolved **environment first**: we
proved what the runtime, toolchain and OS actually do before suspecting application code, and
only then changed code or specs. Times are 2026-10-01 (IST).

---

## Incident 1 — Harness guardrail hooks silently did nothing on Windows

| | |
|---|---|
| Symptom | Writes that should trip harness hooks (e.g. `check-architecture.js`) were never blocked |
| First suspicion (rejected) | A bug in our layering or in our use of the hooks |
| Environment check | Ran a hook by hand with a payload on stdin in Git Bash on Windows. Exit 0, no output. Reading the source showed every harness hook calls `fs.readFileSync('/dev/stdin')` inside `try { … } catch { exit 0 }`. On Windows `/dev/stdin` does not exist for Node, so the read throws, the hook swallows the error, and it "passes" |
| Root cause | OS assumption in the vendored hooks (POSIX `/dev/stdin`), hidden by a deliberate fail-open `catch` |
| Resolution | The MediCard hooks are bash and read stdin with `cat` (`.claude/hooks/lib/hook-input.sh`). `scripts/test-hooks.sh` asserts each hook blocks a bad file (exit 2) and passes a clean one (exit 0). CI runs it. The harness files are left unmodified (vendored) |
| Proof | During Sprint 2 and 3 the MediCard hooks blocked real edits live in this session (`role-boundary-check`, `phi-redaction-check`, `settlement-cap-check`) |
| Deposit | KD-01 |

## Incident 2 — The route-guard architecture test passed vacuously

| | |
|---|---|
| Symptom | `test_public_allowlist_is_minimal` failed: the set of `/api` routes was **empty** |
| First suspicion (rejected) | Routers not registered in `create_app` |
| Environment check | Printed `type(r)` for `app.routes` under the installed FastAPI (0.142.2). The included routers are `fastapi.routing._IncludedRouter` objects that hold `original_router`, not copied `APIRoute`s as in older FastAPI |
| Root cause | Framework behaviour change in the installed version, not our code. The companion test `test_every_api_route_is_guarded…` would have passed while checking nothing |
| Resolution | `_flatten()` walks nested routers. The allowlist test acts as a tripwire that fails whenever discovery finds no routes |
| Deposit | KD-07 |

## Incident 3 — Playwright web server "cannot find the path specified"

| | |
|---|---|
| Symptom | `npx playwright test` → `[WebServer] The system cannot find the path specified`, exit 1 |
| First suspicion (rejected) | Uvicorn import error or a broken FastAPI app |
| Environment check | Ran the same command by hand from `frontend/` (failed) and from the repo root (worked). The config sets `webServer.cwd: ".."`, so the command runs from the repo root, but the Python path was built relative to `frontend/` (`../.venv/...`) |
| Root cause | Working-directory mismatch between the config's process and the spawned web server |
| Resolution | The Python path is relative to the repo root (`.venv/Scripts/python.exe`), or `MEDICARD_PYTHON` in CI (`.venv/bin/python`) |

## Incident 4 — Port 8000 answered 404 for `/health`

| | |
|---|---|
| Symptom | The Sprint 1 evaluator saw `/health` return 404 and MediCard fail to bind |
| Environment check | The process listening on 8000 was a different local project (`…\guard\backend`), not MediCard |
| Resolution | Each evaluator round uses its own port (8010–8015) and a throwaway DB in `$TEMP`. Playwright uses 8123. The unrelated process was left alone |

## Incident 5 — `/health` measured at ~210 ms on `localhost`

| | |
|---|---|
| Symptom | NFR-07 measurements via `curl http://localhost:…` were 0.21–0.24 s |
| Environment check | The same request to `127.0.0.1` took 0.006 s. Windows tries IPv6 `::1` first, and uvicorn was bound to IPv4 only |
| Resolution | No code change. Evaluators and Playwright use `127.0.0.1`. NFR-07 is met with a wide margin (< 10 ms server time) |

## Incident 6 — `poetry install` crashed with `'charmap' codec can't encode characters`

| | |
|---|---|
| Symptom | `poetry install` → `UnicodeEncodeError … position 24-29`, so the `medicard` console script was never created and `poetry run medicard` failed with "not recognized" |
| First suspicion (rejected) | Bad `pyproject.toml`. But `poetry check` said "All set!" and `poetry lock` succeeded |
| Environment check | `poetry install -vvv` stack: `masonry/builders/editable.py:_add_pth → site_packages.write_text`. Positions 24–29 of the project path `C:\Users\Pandu\OneDrive\ドキュメント\abhiram` are `ドキュメント` (the Japanese-locale "Documents" folder). Poetry writes the editable `.pth` file in the Windows ANSI code page (cp1252), which cannot represent those characters. `PYTHONUTF8=1` did not change Poetry's explicit encoding |
| Root cause | Toolchain bug: Poetry editable install plus a non-ASCII project path on Windows. Not project code |
| Resolution | `pip install --no-deps -e .` (pip writes the `.pth` correctly) registers the same `medicard` entry point. After that, `poetry run medicard` works. Verified: `/health` → 200, SPA `/` and deep link `/cases/1` → 200, `/api/nope` → JSON 404, JSON logs. CI (Linux, ASCII path) is unaffected. Documented in the README |
| Side finding | The live JSON logs showed uvicorn's `color_message` (ANSI codes) leaking into JSON. Dropped in `JsonFormatter` and covered by `test_uvicorn_server_logs_are_json_too` |

---

## Lessons

1. Reproduce outside the tool that reported the failure: a hook by hand, uvicorn by hand, `type()` of runtime objects.
2. A test that can pass while checking nothing needs a tripwire, such as the allowlist test.
3. Record OS and toolchain assumptions (Windows paths, `/dev/stdin`, IPv6) in `docs/knowledge-deposits.md`, so later agents do not rediscover them.
