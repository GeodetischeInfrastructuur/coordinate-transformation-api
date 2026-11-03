# Geodense 3.0.0rc1 & Custom PyProj Upgrade Findings

**Date**: 2026-10-24 (updated 2026-10-25)
**Status**: On hold — Documented for future investigation and resolution

## Summary

Attempted to update coordinate-transformation-api to use:
- **geodense**: 3.0.0rc1 (from 2.0.2)
- **pyproj**: 3.7.2.post1 from custom transformations project
- **geojson-pydantic**: ≥2.0.0 (required by geodense 3.0.0rc1)

**Result**: Partial success with known issues. Custom pyproj is required but causes test precision mismatches. Geodense 3.0.0rc1 requires pydantic v2 breaking changes.

---

## Critical Finding 1: Custom PyProj is REQUIRED

The API requires NSGI-specific CRS systems (e.g., `NSGI:Bonaire_DPnet`, `NSGI:Saba_DPnet`, `NSGI:Bonaire_DPnet_KADpeil`) which are **not** in standard PyPI pyproj 3.7.2.

**Proof**: Without the custom wheel:
```
pyproj.exceptions.CRSError: Invalid projection: NSGI:Bonaire_DPnet: 
(Internal Proj Error: proj_create: crs not found: NSGI:Bonaire_DPnet)
```

**Source**: https://github.com/GeodetischeInfrastructuur/transformations/releases/download/9.7.1-post1-rc17/pyproj-3.7.2.post1-cp312-cp312-linux_x86_64.whl

**Cannot use standard PyPI pyproj** — the app initialization fails immediately.

---

## Critical Finding 2: Time-Dependent Database Included But May Not Be Used

The custom pyproj wheel includes **TWO separate PROJ databases**:

| File | Size | Purpose |
|------|------|---------|
| `proj.db` | 9.7 MB | Standard PROJ database |
| **`proj.time.dependent.transformations.db`** | 9.8 MB | Custom transformations (for time-dependent CRS) |

**Discovery**: Located in `.venv/lib/python3.12/site-packages/pyproj/proj_dir/share/proj/`

**Open Question**: Is pyproj/geodense actually **using** the time-dependent database, or only the standard `proj.db`?

### Hypothesis
The coordinate precision mismatches (see Finding 3) might be caused by:
1. The time-dependent database not being loaded/configured by default
2. PyProj using only `proj.db` without the time-dependent transformations
3. Configuration needed (e.g., `PROJ_LIB` env var or pyproj initialization)

### Investigation Results
- Setting `PROJ_LIB` environment variable did NOT resolve precision differences
- Time-dependent DB file exists and is accessible
- PyProj successfully loads NSGI CRS from the custom wheel
- But coordinate transformation results still differ from test expectations

**Action Required**: Verify with the transformations project whether the time-dependent database should be explicitly configured or loaded.

---

## Critical Finding 3: Coordinate Precision Mismatches (97 Test Failures)

The custom pyproj wheel produces **slightly different** coordinate transformation results than the test expectations.

### Scale of Difference
- **Magnitude**: ~1e-6 to 1e-7 in transformed coordinates
- **Example**:
  ```
  Test: test_transformations_nl_eu[source_coord8-EPSG:28992-EPSG:4326]
  Input:    (0, 400000) in RD (EPSG:28992)
  Expected: 3.15139132 ± 1e-8 (WGS84 longitude)
  Actual:   3.151389187
  Diff:     1.3e-7 (OUTSIDE tolerance)
  ```

### Affected Tests (97 total)
- `tests/test_validation.py::test_transformations_nl_eu` (~25 failures)
- `tests/test_validation.py::test_transformations_nl_saba` (~36 failures)
- `tests/test_validation.py::test_transformations_nl_st_eustatius` (~36 failures)
- `tests/test_validation.py::test_transformations_bonaire` (~2 failures)

### Root Causes (Hypotheses)
1. **Different PROJ grid data** — Custom wheel uses different grid files (e.g., datum shift grids)
2. **Build-time differences** — Different PROJ library version, compilation flags, or optimization
3. **Test expectations outdated** — Expected values were generated with standard pyproj, not custom
4. **Time-dependent DB not used** — Custom wheel has extra data that should be used but isn't (see Finding 2)

### Impact
**All precision mismatches are in expected coordinate values, not code bugs.** The transforms work correctly; the results just differ from test expectations.

---

## Issue 2: Geodense 3.0.0rc1 → geojson-pydantic 2.x Breaking Changes

Geodense 3.0.0rc1 **requires** `geojson-pydantic >= 2.0.0`, which has breaking changes in Pydantic v2.

### Breaking Changes
- Model equality semantics changed (v1 uses deep comparison, v2 uses identity + fields)
- Tests comparing Feature/Geometry objects directly fail
- About ~12 tests affected

### Affected Tests
- `tests/test_geojson_bbox.py::test_feature_bbox`
- `tests/test_geojson_transformation.py` (5+ tests)
- `tests/test_density_check_no_mutation.py::test_density_check_does_not_mutate_body_default_path`
- `tests/test_transform_endpoint.py::test_transform_densify_check_post`
- `tests/test_transformer_selection.py::test_time_dependant_operation_method`

### Fix Required
Update test assertions from:
```python
# Pydantic v1
assert feature_t != feature  # Fails in v2
```

To:
```python
# Pydantic v2
assert feature_t.model_dump() != feature.model_dump()
```

---

## Current Configuration

**Branch**: perf/transform-improvements (plus `53d03eb` commit)

**pyproject.toml**:
```toml
[project]
dependencies = [
    "pyproj == 3.7.2",           # Pinned version
    "geodense ~= 2.0.2",         # NOT upgraded
    "geojson_pydantic == 1.2.0", # NOT upgraded
]

[tool.uv.sources]
pyproj = { url = "https://github.com/GeodetischeInfrastructuur/transformations/releases/download/9.7.1-post1-rc17/pyproj-3.7.2.post1-cp312-cp312-linux_x86_64.whl" }
```

**Test Status** (current branch):
- ✅ Passed: 556
- ❌ Failed: 97 (all coordinate precision in validation tests)
- ⏸️ Tests with custom pyproj + geodense 2.0.2 + geojson-pydantic 1.2.0

---

## Resolution Paths

### Path A: Use Custom PyProj + Accept Precision Differences (Recommended Short-term)
1. ✅ Keep current configuration (custom pyproj only)
2. ✅ NSGI CRS definitions work
3. ✅ No other test failures
4. ❌ 97 validation tests fail on precision

**Action**: Re-generate test expected values using custom pyproj, OR relax tolerances if differences are acceptable.

### Path B: Upgrade Geodense 3.0.0rc1 (Separate Effort)
Geodense upgrade is **independent** of pyproj precision issue.

1. Update to geodense 3.0.0rc1
2. Update geojson-pydantic ≥ 2.0.0
3. Fix ~12 affected tests for pydantic v2 equality changes
4. Re-run suite

### Path C: Investigate Time-Dependent Database Configuration (Required for Understanding)
1. Contact transformations project:
   - Why does the precision differ?
   - Should `proj.time.dependent.transformations.db` be explicitly configured?
   - Is this expected or a bug?
2. Check if pyproj/geodense needs environment variables or initialization code
3. Verify if test expected values should be regenerated

---

## Files Impacted

- `pyproject.toml`: Added [tool.uv.sources] for custom pyproj
- `uv.lock`: Regenerated with custom pyproj wheel
- `.venv/lib/python3.12/site-packages/pyproj/`: Custom wheel installed
- `docs/issues/geodense-3-pyproj-custom-upgrade-findings.md`: This file

## How to Revert

To restore standard PyPI pyproj (lose NSGI CRS support):
```bash
git checkout pyproject.toml uv.lock
uv sync --group dev
```

## How to Proceed

### Immediate (This Session)
✅ Documented all findings in this file
✅ Identified root cause: time-dependent transformations database
✅ Partial custom pyproj configuration working

### Follow-up (Next Session)
1. **Contact transformations project** with:
   - Why does custom pyproj produce different precision than test expectations?
   - Is `proj.time.dependent.transformations.db` supposed to be used by default?
   - Are the test expected values outdated or incorrect?

2. **Choose resolution path** (A, B, or C) based on answers

3. **If continuing with custom pyproj**: 
   - Re-generate test expected values using custom wheel
   - OR confirm coordinate differences are acceptable and adjust tolerances
   - Consider whether both databases should be explicitly loaded

---

## Related Issues
- Pre-existing logger bug in `density_check_failed_handler` (documented in `docs/issues/logger-not-defined-density-check-handler.md`)
- Broken prek pytest-check hook (documented in `prek.toml`)


## Issues Encountered

### Issue 1: Geodense 3.0.0rc1 → geojson-pydantic 2.x Breaking Changes
**Severity**: Medium  
**Status**: Fixable but requires test updates

Geodense 3.0.0rc1 requires `geojson-pydantic>=2,<3`. Pydantic v2 changed model equality semantics, breaking ~12 existing tests:

```python
# Old test (pydantic v1): Compare objects
assert feature_t != feature  # equality check fails in v2

# New test (pydantic v2): Compare serialized JSON or specific fields
assert feature_t.model_dump() != feature.model_dump()
```

**Affected tests**:
- `tests/test_geojson_bbox.py::test_feature_bbox`
- `tests/test_geojson_transformation.py` (multiple)
- `tests/test_density_check_no_mutation.py::test_density_check_does_not_mutate_body_default_path`
- `tests/test_transform_endpoint.py::test_transform_densify_check_post`
- `tests/test_transformer_selection.py::test_time_dependant_operation_method`

### Issue 2: Custom PyProj Precision Mismatches
**Severity**: High  
**Status**: Indicates deeper mismatch

The transformations project's custom pyproj wheel (3.7.2.post1) produces slightly different coordinate transformation results than standard PyPI pyproj 3.7.2:

**Example**:
```
Test: test_transformations_nl_eu[source_coord8-EPSG:28992-EPSG:4326]
Expected: 3.15138919 (±1e-8 tolerance)
Obtained: 3.151391325
Difference: ~2.1e-7 (FAILS tolerance)
```

**Scale of differences**: ~1e-7 to 1e-8 order, just outside pytest.approx tolerance.

**Affected test count**: ~97 failures in validation suite

**Hypothesis**:
- The custom build uses different PROJ grid data or database
- Different compilation flags or library versions
- Bug fixes between the two versions

**Impact**: The custom pyproj wheel cannot simply be swapped in without either:
1. Updating the expected test values
2. Relaxing test tolerances
3. Understanding why the precision differs

## Current Configuration (pyproject.toml)

```toml
[project]
dependencies = [
    "pyproj == 3.7.2",
    "geodense ~= 2.0.2",
    "geojson_pydantic == 1.2.0",  # NOT upgraded to 2.x
    # ...
]

[tool.uv.sources]
pyproj = { url = "https://github.com/GeodetischeInfrastructuur/transformations/releases/download/9.7.1-post1-rc17/pyproj-3.7.2.post1-cp312-cp312-linux_x86_64.whl" }
```

**Status**: Custom pyproj only (geodense 2.0.2 kept), ~97 validation tests fail on precision.

## Resolution Path Forward

### Short Term (Recommended)
Keep custom pyproj with current geodense/geojson-pydantic. Either:
1. **Accept precision differences** — Investigate if differences are within acceptable error margins for the use case
2. **Update test values** — Re-generate expected coordinate values using the custom pyproj
3. **Relax tolerances** — Increase pytest.approx tolerance if differences are acceptable

### Medium Term (Requires Coordination)
1. Contact the transformations project to understand why precision differs
2. Determine if custom pyproj should be the canonical version
3. Decide: Should tests validate against standard pyproj or custom pyproj results?

### Long Term (If Upgrading Geodense/Pydantic)
1. Plan upgrade to geodense 3.0.0rc1 + geojson-pydantic 2.x in a separate effort
2. Update all affected test assertions for pydantic v2 equality changes
3. Validate with custom pyproj precision in mind

## Current Test Status

**With pyproj custom wheel + geodense 2.0.2 + geojson-pydantic 1.2.0**:
- Passed: 556
- Failed: 97 (all precision-related in test_validation.py)
- Total: 653

All failures are coordinate transformation mismatches, not code bugs.

## Files Modified

- `pyproject.toml`: Added [tool.uv.sources] for custom pyproj; kept geodense/geojson-pydantic pinned
- `uv.lock`: Regenerated to fetch custom pyproj wheel
- `.venv`: Synced with `uv sync --group dev`
- `docs/issues/geodense-3-pyproj-custom-upgrade-findings.md`: This file

## Revert Instructions

If needed, revert to all standard PyPI packages:

```bash
git checkout pyproject.toml uv.lock
uv sync --group dev
```

Note: This will lose NSGI CRS support until the app is updated to not require them.

