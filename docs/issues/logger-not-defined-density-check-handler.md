# Bug: `NameError: name 'logger' is not defined` when a density check fails before `lifespan` runs

## Summary

`density_check_failed_handler` in `src/coordinate_transformation_api/main.py`
uses the module-level `logger`, but `logger` is only **assigned** inside the
`lifespan` async context manager. If a `DensityCheckFailedError` is raised before
`lifespan` has executed (e.g. under `TestClient` without triggering lifespan, or
any request handled before startup completes), the handler raises
`NameError: name 'logger' is not defined`, masking the original 400 response.

## Affected code

`src/coordinate_transformation_api/main.py`:

```python
logger: logging.Logger   # line 85 — annotation only, no value assigned


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator:
    global logger  # noqa: PLW0603
    logger = logging.getLogger(__name__)   # only assigned here, at startup
    ...


@app.exception_handler(DensityCheckFailedError)
async def density_check_failed_handler(_: Request, exc: DensityCheckFailedError) -> JSONResponse:
    logger.debug({str(exc)})   # line 141 — NameError if lifespan hasn't run
    ...
```

`logger: logging.Logger` on line 85 is only a type annotation; it does not bind a
value. The name is bound at runtime exclusively by the `global logger`
assignment inside `lifespan`.

## How to reproduce

Trigger a failing density check through `TestClient` (which does not run
`lifespan` for every call path):

```python
from fastapi.testclient import TestClient
from coordinate_transformation_api.main import app

client = TestClient(app)
# A FeatureCollection whose line segments exceed the 200m density threshold
resp = client.post(
    "/transform?source-crs=EPSG:28992&target-crs=EPSG:4326",
    content=feature_collection_bytes,
    headers={"Content-Type": "application/json"},
)
```

Instead of the expected HTTP 400 density-check response, the handler raises:

```
NameError: name 'logger' is not defined
  File ".../src/coordinate_transformation_api/main.py", line 141, in density_check_failed_handler
    logger.debug({str(exc)})
```

This was observed while running `scripts/benchmark_e2e.py` with
`--density-check` against randomly generated (sparse) coordinates.

## Expected behaviour

The density-check failure should return the RFC7807 HTTP 400 response regardless
of whether `lifespan` has run. Logging must never raise `NameError`.

## Impact

- Any `DensityCheckFailedError` raised before/without `lifespan` returns a
  `500`-style `NameError` instead of the intended `400` density-check response.
- Affects tests and tooling that use `TestClient` without lifespan, and could
  affect requests handled during a narrow startup window.
- Note: `logger.debug({str(exc)})` also passes a `set` (`{str(exc)}`) rather than
  a string — likely an unintended brace; worth fixing at the same time.

## Suggested fix

Bind the module-level logger at import time so it always exists, and let
`lifespan` reconfigure levels as needed:

```python
# module scope, replacing the bare annotation on line 85
logger: logging.Logger = logging.getLogger(__name__)
```

Then the `global logger` reassignment in `lifespan` becomes unnecessary and can
be removed (it can still adjust log levels / emit startup logs via the
module-level `logger`). Also fix the handler call:

```python
logger.debug(str(exc))   # pass a string, not a set
```

## Acceptance criteria

- A failing density check returns HTTP 400 (RFC7807 body) even when `lifespan`
  has not run.
- No `NameError` is raised from `density_check_failed_handler`.
- A regression test exercises a failing density check via `TestClient`.
