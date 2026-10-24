# Performance Improvement Plan (profiled): numpy, orjson & pyogrio

> **Implementation status (branch `perf/transform-improvements`):** Steps 1, 2a,
> 3 and 4 are implemented and committed. Step 2b (geodense deep-copy) is
> deferred to the geodense project. Step 5 (pyogrio) dropped. Measured end-to-end
> gains are recorded in the "Measured results" section near the end.

Investigation into speeding up `POST /transform` for bulk GeoJSON. **This version
is backed by profiling data** (cProfile + micro-benchmarks) collected on this
machine. The profiling revised the original priorities significantly: the single
biggest cost is **deep-copying pydantic models**, not the PROJ transform, and
numpy vectorization gives a much smaller win than first assumed.

Profiling harness: `/tmp/opencode/profile_ct.py`, `/tmp/opencode/micro.py`,
`/tmp/opencode/orjson_test.py`. Transform used: `EPSG:28992` → `EPSG:4326`.

## Measured end-to-end breakdown (`POST /transform` pipeline)

Synthetic FeatureCollections of polygons, RD → WGS84. Times in ms.

| Stage | small (2.1k coords, 62 KiB) | large (51k coords, 1.3 MiB) | xlarge (202k coords, 5.2 MiB) |
| --- | --- | --- | --- |
| parse (pydantic) | 3.6 (4.9%) | 115.6 (9.3%) | 441.6 (8.1%) |
| deepcopy (density check) | 8.6 (11.7%) | 206.9 (16.7%) | 710.4 (13.0%) |
| **transform** | **57.8 (78.4%)** | **830.1 (67.0%)** | **3950.2 (72.4%)** |
| model_dump | 2.4 (3.2%) | 56.5 (4.6%) | 210.4 (3.9%) |
| json.dumps | 1.4 (1.8%) | 29.6 (2.4%) | 143.2 (2.6%) |
| **TOTAL** | **73.8** | **1238.7** | **5455.7** |

`transform` dominates — but the cProfile below shows **most of that time is NOT
the PROJ math**.

## Where the `transform` time actually goes (cProfile, large = 51k coords)

`crs_transform` total 5.72s under cProfile (profiler inflates absolute numbers;
read the *proportions*):

| Component | cum. time | What it is |
| --- | --- | --- |
| `model_copy(deep=True)` / `copy.deepcopy` | **3.85s (67%)** | geodense `traverse_geojson_geometries` deep-copies the whole model **and every nested feature/geometry** on each traversal level |
| `transform_crs` (per-point body) | 1.66s | the per-coordinate callback |
| → `transformer.target_crs` property access | **0.63s** | **rebuilds a CRS wrapper object on every single point** to read `axis_info` |
| → `pyproj transform` (actual C call) | **0.27s** | the real PROJ math |
| → rounding (`map`/`_round`/`round`) | 0.24s | per-value Python rounding |

**Key insight: the actual PROJ transform is ~0.27s — under 5% of
`crs_transform`.** The dominant costs are (1) pydantic deep-copying inside
geodense's traversal and (2) a redundant `target_crs.axis_info` property lookup
executed once per coordinate.

## Micro-benchmark: how much does numpy vectorization actually help? (51k points)

| Approach | time |
| --- | --- |
| per-point `transform` (loop, no extra work) | 141.9 ms |
| per-point + `target_crs.axis_info` each call (current code) | 267.0 ms |
| per-point + `axis_info` cached once | 139.1 ms |
| **vectorized numpy `transform` (1 call)** | **78.5 ms** |

Takeaways:
- Vectorizing the PROJ call: **267ms → 78ms ≈ 3.4x**, but **142ms → 78ms ≈ 1.8x**
  once the redundant `axis_info` access is removed. The original plan's
  "10–100x" claim is **not supported** — PROJ per-call overhead here is modest.
- **Caching `target_crs.axis_info` once** alone recovers ~125ms (267→139) for
  near-zero effort and risk.

## Micro-benchmark: orjson vs stdlib json (large, 51k coords)

| Operation | stdlib | orjson | speedup |
| --- | --- | --- | --- |
| loads (raw decode) | 52.1 ms | 16.5 ms | 3.2x |
| dumps (serialize) | 54.5 ms | 5.7 ms | **9.6x** |

- Response serialization (`json.dumps` in `JSONResponse`) is the clear orjson win
  (~10x on that stage). Worth doing; it's low risk.
- On the request side, pydantic validation (~60ms+ on the large body) sits on top
  of the raw decode, so orjson only shaves the decode portion of parse, not the
  validation.

---

## Revised recommendation (data-driven, re-ordered)

Priorities changed after profiling. Do the cheap, high-certainty wins first.

### Step 1 — Cache `target_crs` dimension per transform (tiny change, real win)

**Evidence:** `target_crs.axis_info` access costs ~0.63s of 5.72s in cProfile and
~125ms of the 267ms per-point loop in the micro-benchmark.

- In `crs_transform.transform_crs` / `transform_compound_crs`, the `target_dim`
  (`len(transformer.target_crs.axis_info)`) is recomputed on every point. It is
  constant for a given transformer. Compute it **once** in `get_transform_crs_fun`
  and pass it into the partial (alongside the already-injected `transformer`,
  `precision`, `epoch`).
- Same for `hor`/`ver` transformers in the compound path.

**Expected:** ~1.8x on the per-point loop (`267 → ~139ms` on 51k points), i.e. a
meaningful chunk of the whole transform stage, with essentially zero correctness
risk (no numeric change).

### Step 2 — Eliminate the dominant deep-copy cost

**Evidence:** deep-copying is ~67% of `crs_transform` cumulative time, and the
`POST` density-check path adds another full `copy.deepcopy(body)` (13–17% of the
end-to-end total on its own).

Two independent sub-items:

**2a. Drop the explicit `copy.deepcopy(body)` in `main.post_transform`.**
`density_check_request_body` → `crs_transform` → geodense
`traverse_geojson_geometries` already does `model_copy(deep=True)`, so the
original `body` is never mutated by the density check. Removing the pre-copy
saves one full model clone (measured 207ms on large, 710ms on xlarge).
*Verify with a test asserting `body` is unchanged after the density check, then
remove.*

**2b. Reduce geodense's per-level deep copy (larger, upstream-ish).**
geodense's `traverse_geojson_geometries` calls `model_copy(deep=True)` at the
collection level *and* recursively per feature/geometry, so coordinate data is
deep-copied multiple times. Options, in order of preference:
- Transform **in place** where we own the flow: our `crs_transform` only needs a
  copy if the caller reuses the original. For `POST /transform` the body is
  request-scoped and discarded after — an in-place transform avoids the copy
  entirely. Investigate a geodense call path (or a local traversal) that mutates
  in place.
- If geodense cannot avoid the copy, do a **single** shallow structural copy plus
  in-place coordinate replacement instead of recursive `deep=True`.

This is the **single largest opportunity** by the data. Needs care because
geodense owns the traversal; may warrant an upstream change or a local
traversal replacement.

### Step 3 — orjson for response serialization (low effort, ~10x on that stage)

**Evidence:** `orjson.dumps` 5.7ms vs `json.dumps` 54.5ms on the large body.

- Swap `JSONResponse` → `fastapi.responses.ORJSONResponse` for the bulk
  endpoints (`POST /transform`, `/densify`, `/check-density`, and the JSON branch
  of `GET /transform`). Continue passing the `model_dump(exclude_none=True)` dict.
- Optionally use `orjson.loads` for request bodies, but the win is smaller
  (validation dominates) — treat as secondary.
- Add `orjson` to `[project].dependencies`; `uv lock`.

### Step 4 — Vectorized numpy transform (medium effort, ~1.8x after Step 1)

**Evidence:** vectorized 78ms vs 139ms (axis cached) on 51k points ≈ 1.8x; the
PROJ C call is only 0.27s of the whole transform. So this is worthwhile but **not
the headline win** the original plan implied, and it only pays off *after* Steps
1–2 remove the copy/property overhead that currently dwarfs it.

- Flatten each geometry's coordinates into numpy arrays, one
  `transformer.transform(x, y, z, t)` call, vectorized `np.round` / `np.isinf`,
  re-nest. Keep the scalar path for single-point `GET /transform`.
- **Correctness caveat (unchanged):** numpy's banker's rounding may diverge from
  Python `round()`; must be validated against `pytest tests -k validation`
  (exact-coordinate assertions). If it diverges, use a decimal-shift round to
  match.
- Add `numpy` as an **explicit** dependency (currently only transitive).

### Step 5 — `pyogrio`: not supported by the data; do not pursue now

**Evidence:** parse is only 8–9% of end-to-end time, and raw JSON decode is a
fraction of that (orjson already handles it). pyogrio would replace pydantic
validation/CityJSON/RFC7807 error handling and add a GDAL dependency for a stage
that is not the bottleneck. **Drop from scope** unless a future profile shows
parse-bound workloads.

---

## Revised impact ranking (by measured data)

| Step | Effort | Measured basis | Risk |
| --- | --- | --- | --- |
| 1. Cache target_crs dim | Trivial | 267→139ms loop (1.8x) | Negligible |
| 2a. Drop `deepcopy` in post_transform | Trivial | −207ms large / −710ms xlarge | Low |
| 2b. Avoid geodense per-level deep copy | High | ~67% of transform cum-time | Medium (upstream) |
| 3. orjson response | Low | 54→6ms serialize (≈10x) | Low |
| 4. numpy vectorized transform | Medium | 139→78ms (1.8x) | Medium (rounding) |
| 5. pyogrio | — | parse not a bottleneck | Dropped |

**Corrections vs the original plan:** numpy was overstated (claimed 10–100x;
measured ~1.8x); the real giant is pydantic deep-copying (Step 2), which the
original plan only listed as a minor "Step 3"; and the near-free `axis_info`
caching fix (Step 1) was not in the original plan at all.

## Rollout / verification checklist

**Verification tool:** `scripts/benchmark_e2e.py` drives the real endpoint
through `TestClient` (full parse → validate → density-check → transform →
serialize → HTTP response). Use it to confirm gains:

```sh
# 1. record a baseline before changes
.venv/bin/python scripts/benchmark_e2e.py -n 10 --save baseline.json
# 2. apply a change, then compare
.venv/bin/python scripts/benchmark_e2e.py -n 10 --compare baseline.json
```

It reports median / min / p95 ms and coords/s per scenario (small … xlarge,
many-points, linestrings) and a per-scenario speedup vs the baseline. Density
check is off by default (random bulk coords fail the 200m check); pass
`--density-check` to include that path.

1. Step 1 (axis_info caching) + Step 2a (drop deepcopy) — smallest, safest;
   benchmark delta with `/tmp/opencode/profile_ct.py`.
2. Step 3 (ORJSONResponse) + add `orjson` dep; `uv lock`.
3. Step 2b (deep-copy avoidance) — investigate in-place / geodense; most care.
4. Step 4 (numpy) — guard with `pytest tests -k validation`.
5. Full suite: `pytest tests`; lint/type: `prek run -a`, `ruff`, `ty`.
6. Re-profile and record before/after numbers here.

## Measured results (implemented: Steps 1, 2a, 3, 4)

End-to-end A/B via `scripts/benchmark_e2e.py` (full HTTP pipeline through
`TestClient`, RD → WGS84, density-check off). "Before" = base commit `cf77735`
run with its source on `PYTHONPATH`; "after" = branch `perf/transform-improvements`
(commits for Steps 1→4). Same host, 12–15 timed iters + 3 warmup.

| scenario | coords | before median | after median | speedup |
| --- | --- | --- | --- | --- |
| large | 51,000 | 1808.7 ms | 1013.5 ms | **1.78x** |
| xlarge | 121,000 | 3409.4 ms | 2507.8 ms | **1.36x** |
| linestrings | 75,000 | 2187.8 ms | 1838.0 ms | **1.19x** |
| many-points | 20,000 (1 pt/feature) | 2629.0 ms | 2467.8 ms | **1.07x** |

Notes:
- The shared host is noisy; medians move run-to-run. `min_ms` (best-case, least
  noisy) shows the same direction: large ~1.27x, xlarge ~1.25x, linestrings ~1.07x.
- **many-points** (20k single-Point features) is roughly break-even: each
  geometry holds a 1-element array, so numpy batching barely helps and its
  array-build/flatten-rebuild overhead nearly cancels the gain. The Step-1 axis
  caching keeps it net-positive. A future optimization could batch transform
  across the whole FeatureCollection (one PROJ call per request) to benefit this
  case — noted below.
- Correctness held throughout: 653 tests pass, incl. 594 exact-coordinate
  `test_validation.py` cases; `ruff` and `ty` clean.

## Open questions

- Can geodense transform in place (or expose a no-copy traversal), or do we
  replace its traversal locally for the transform path? (Determines Step 2b.)
- Does numpy banker's rounding diverge from `round()` on any validation fixture?
- Many tiny single-point features: vectorizing per-geometry still yields many
  small C calls — consider batching across the whole FeatureCollection later.
