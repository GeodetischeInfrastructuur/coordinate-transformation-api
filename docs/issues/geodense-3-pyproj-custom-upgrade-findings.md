# Geodense 3.0.0rc1 & Custom PyProj Upgrade Findings

**Date**: 2026-10-24
**Status**: Incomplete — documented for future resolution

## Summary

Attempted to update to:
- **geodense**: 3.0.0rc1 (from 2.0.2)
- **pyproj**: 3.7.2.post1 from custom transformations project
  - Required for NSGI-specific CRS definitions (e.g., NSGI:Bonaire_DPnet)
- **geojson-pydantic**: ≥2.0.0 (required by geodense 3.0.0rc1)

**Result**: Both updates introduced incompatibilities. See below for details.

## Critical Finding: Custom PyProj is Required

The API requires NSGI-specific CRS systems (e.g., NSGI:Bonaire_DPnet, NSGI:Saba_DPnet) which are **not** in standard PyPI pyproj 3.7.2. These only exist in the custom wheel from the transformations project:
```
https://github.com/GeodetischeInfrastructuur/transformations/releases/download/9.7.1-post1-rc17/pyproj-3.7.2.post1-cp312-cp312-linux_x86_64.whl
```

Without it, the app fails to initialize:
```
pyproj.exceptions.CRSError: Invalid projection: NSGI:Bonaire_DPnet: (Internal Proj Error...)
```

**Implication**: The custom pyproj wheel must be used. It cannot be replaced with standard PyPI pyproj.

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

