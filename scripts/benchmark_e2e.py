#!/usr/bin/env python
"""End-to-end performance benchmark for the Coordinate Transformation API.

Drives the real FastAPI application through `fastapi.testclient.TestClient`, so
the full request pipeline is measured: JSON parsing, pydantic validation,
density check, CRS transform, serialization and the HTTP response.

Use it to verify actual performance gains: run it on a baseline, apply changes,
run it again and compare. Results can be written to JSON for diffing.

Usage:
    python scripts/benchmark_e2e.py                      # default scenarios
    python scripts/benchmark_e2e.py -n 20 --warmup 3     # more iterations
    python scripts/benchmark_e2e.py --save baseline.json # record results
    python scripts/benchmark_e2e.py --compare baseline.json   # vs saved run
    python scripts/benchmark_e2e.py --only large          # single scenario

Run from the repository root with the project venv active, e.g.
    .venv/bin/python scripts/benchmark_e2e.py
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from dataclasses import dataclass, field

from fastapi.testclient import TestClient

from coordinate_transformation_api.main import app
from coordinate_transformation_api.settings import app_settings

# Raise the request body size limit for benchmarking so large scenarios are not
# rejected with HTTP 413 by ContentSizeLimitMiddleware (prod default is 2 MB).
# This only affects this in-process benchmark app instance.
app_settings.max_size_request_body = 64 * 1024 * 1024
for _mw in app.user_middleware:
    if _mw.cls.__name__ == "ContentSizeLimitMiddleware":
        _mw.kwargs["max_content_size"] = app_settings.max_size_request_body

# RD New (EPSG:28992) -> WGS84 (EPSG:4326): the canonical NSGI transform.
SOURCE_CRS = "EPSG:28992"
TARGET_CRS = "EPSG:4326"

# Rough RD bounding box for the Netherlands so coordinates are in-domain.
RD_X_RANGE = (10000.0, 280000.0)
RD_Y_RANGE = (300000.0, 620000.0)


@dataclass
class Scenario:
    name: str
    n_features: int
    pts_per_ring: int
    geom: str = "polygon"  # "polygon" | "point" | "linestring"


DEFAULT_SCENARIOS = [
    Scenario("small", n_features=100, pts_per_ring=20),
    Scenario("medium", n_features=500, pts_per_ring=40),
    Scenario("large", n_features=1000, pts_per_ring=50),
    Scenario("xlarge", n_features=1000, pts_per_ring=120),
    Scenario("many-points", n_features=20000, pts_per_ring=1, geom="point"),
    Scenario("linestrings", n_features=1500, pts_per_ring=50, geom="linestring"),
]


def _rnd_xy(rng: random.Random) -> list[float]:
    return [
        round(rng.uniform(*RD_X_RANGE), 3),
        round(rng.uniform(*RD_Y_RANGE), 3),
    ]


def _make_geometry(rng: random.Random, scenario: Scenario) -> dict:
    if scenario.geom == "point":
        return {"type": "Point", "coordinates": _rnd_xy(rng)}
    if scenario.geom == "linestring":
        return {
            "type": "LineString",
            "coordinates": [_rnd_xy(rng) for _ in range(scenario.pts_per_ring)],
        }
    # polygon: closed ring
    ring = [_rnd_xy(rng) for _ in range(scenario.pts_per_ring)]
    ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}


def build_payload(scenario: Scenario, seed: int = 42) -> tuple[bytes, int]:
    """Return (serialized FeatureCollection bytes, coordinate count)."""
    rng = random.Random(seed)
    features = []
    n_coords = 0
    for i in range(scenario.n_features):
        geom = _make_geometry(rng, scenario)
        # count coordinates for throughput reporting
        if geom["type"] == "Point":
            n_coords += 1
        elif geom["type"] == "LineString":
            n_coords += len(geom["coordinates"])
        else:
            n_coords += len(geom["coordinates"][0])
        features.append({"type": "Feature", "properties": {"id": i}, "geometry": geom})

    fc = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:EPSG::28992"},
        },
        "features": features,
    }
    return json.dumps(fc).encode(), n_coords


@dataclass
class Result:
    name: str
    n_features: int
    n_coords: int
    payload_kib: float
    status: int
    samples_ms: list[float] = field(default_factory=list)

    @property
    def min_ms(self) -> float:
        return min(self.samples_ms)

    @property
    def median_ms(self) -> float:
        return statistics.median(self.samples_ms)

    @property
    def mean_ms(self) -> float:
        return statistics.fmean(self.samples_ms)

    @property
    def p95_ms(self) -> float:
        if len(self.samples_ms) < 2:
            return self.samples_ms[0]
        return statistics.quantiles(self.samples_ms, n=20)[-1]

    @property
    def stdev_ms(self) -> float:
        return statistics.pstdev(self.samples_ms)

    @property
    def coords_per_sec(self) -> float:
        # based on median time
        return self.n_coords / (self.median_ms / 1000.0)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "n_features": self.n_features,
            "n_coords": self.n_coords,
            "payload_kib": round(self.payload_kib, 1),
            "status": self.status,
            "min_ms": round(self.min_ms, 2),
            "median_ms": round(self.median_ms, 2),
            "mean_ms": round(self.mean_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "stdev_ms": round(self.stdev_ms, 2),
            "coords_per_sec": round(self.coords_per_sec),
        }


def run_scenario(
    client: TestClient,
    scenario: Scenario,
    iterations: int,
    warmup: int,
    density_check: bool,
) -> Result:
    payload, n_coords = build_payload(scenario)
    url = f"/transform?source-crs={SOURCE_CRS}&target-crs={TARGET_CRS}"
    if not density_check:
        url += "&density-check=false"
    headers = {"Content-Type": "application/json"}

    # warmup (also validates the request succeeds before timing)
    status = 0
    for _ in range(max(1, warmup)):
        resp = client.post(url, content=payload, headers=headers)
        status = resp.status_code

    if status != 200:
        # surface the server error so the benchmark fails loudly
        resp = client.post(url, content=payload, headers=headers)
        raise RuntimeError(
            f"scenario {scenario.name!r} returned HTTP {resp.status_code}: {resp.text[:500]}"
        )

    samples_ms: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        resp = client.post(url, content=payload, headers=headers)
        samples_ms.append((time.perf_counter() - t0) * 1000.0)
        if resp.status_code != 200:
            raise RuntimeError(f"unexpected HTTP {resp.status_code} during timing")

    return Result(
        name=scenario.name,
        n_features=scenario.n_features,
        n_coords=n_coords,
        payload_kib=len(payload) / 1024.0,
        status=status,
        samples_ms=samples_ms,
    )


def print_table(results: list[Result]) -> None:
    header = f"{'scenario':<14}{'coords':>9}{'KiB':>8}{'median ms':>11}{'min ms':>9}{'p95 ms':>9}{'coords/s':>12}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r.name:<14}{r.n_coords:>9}{r.payload_kib:>8.0f}"
            f"{r.median_ms:>11.1f}{r.min_ms:>9.1f}{r.p95_ms:>9.1f}{r.coords_per_sec:>12,.0f}"
        )


def print_comparison(results: list[Result], baseline: dict) -> None:
    base_by_name = {b["name"]: b for b in baseline["results"]}
    header = f"{'scenario':<14}{'base ms':>10}{'now ms':>10}{'delta':>10}{'speedup':>10}"
    print("\nComparison vs baseline (median):")
    print(header)
    print("-" * len(header))
    for r in results:
        b = base_by_name.get(r.name)
        if b is None:
            print(f"{r.name:<14}{'(no baseline)':>40}")
            continue
        base_ms = b["median_ms"]
        now_ms = r.median_ms
        delta = now_ms - base_ms
        speedup = base_ms / now_ms if now_ms else float("inf")
        print(f"{r.name:<14}{base_ms:>10.1f}{now_ms:>10.1f}{delta:>+10.1f}{speedup:>9.2f}x")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", "--iterations", type=int, default=10, help="timed iterations per scenario")
    parser.add_argument("--warmup", type=int, default=2, help="warmup iterations (not timed)")
    parser.add_argument("--only", action="append", help="run only named scenario(s); repeatable")
    parser.add_argument(
        "--density-check",
        action="store_true",
        help=(
            "enable the density-check query param. Off by default: random bulk "
            "coordinates are far apart and fail the 200m density check (HTTP 400), "
            "which is an orthogonal code path. Leave off to measure transform+serialize."
        ),
    )
    parser.add_argument("--save", metavar="FILE", help="write results to JSON file")
    parser.add_argument("--compare", metavar="FILE", help="compare against a saved results JSON file")
    args = parser.parse_args()

    scenarios = DEFAULT_SCENARIOS
    if args.only:
        wanted = set(args.only)
        scenarios = [s for s in DEFAULT_SCENARIOS if s.name in wanted]
        if not scenarios:
            print(f"no scenarios match {args.only}; available: {[s.name for s in DEFAULT_SCENARIOS]}")
            return 2

    client = TestClient(app)
    results: list[Result] = []
    for scenario in scenarios:
        r = run_scenario(
            client,
            scenario,
            iterations=args.iterations,
            warmup=args.warmup,
            density_check=args.density_check,
        )
        results.append(r)

    print(
        f"\nE2E benchmark — {SOURCE_CRS} -> {TARGET_CRS}, "
        f"{args.iterations} iters, warmup {args.warmup}, "
        f"density-check={'on' if args.density_check else 'off'}\n"
    )
    print_table(results)

    if args.compare:
        with open(args.compare) as f:
            baseline = json.load(f)
        print_comparison(results, baseline)

    if args.save:
        payload = {
            "config": {
                "source_crs": SOURCE_CRS,
                "target_crs": TARGET_CRS,
                "iterations": args.iterations,
                "warmup": args.warmup,
                "density_check": args.density_check,
            },
            "results": [r.to_dict() for r in results],
        }
        with open(args.save, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"\nsaved results to {args.save}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
