import pytest
from geodense.geojson import CrsFeatureCollection
from pyproj import CRS

from coordinate_transformation_api.util import density_check_request_body


def _body() -> CrsFeatureCollection:
    return CrsFeatureCollection(**{
        "type": "FeatureCollection",
        "name": "lijnen",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [156264.9063, 601302.5889],
                        [165681.9644, 605544.3131],
                    ],
                },
            }
        ],
    })


@pytest.mark.parametrize(("max_segment_length", "expected_segments"), [(1000.0, 1), (20000.0, 0)])
def test_density_check_transforms_body_in_place_and_reports_in_source_crs(max_segment_length, expected_segments):
    body = _body()
    original = body.model_dump(mode="python", round_trip=True)

    report = density_check_request_body(body, CRS.from_epsg(28992), None, max_segment_length, None)

    # geodense v3 mutates the input during transformation to the density-check CRS.
    assert body.get_crs_auth_code() == "OGC:CRS84"
    assert body.model_dump(mode="python", round_trip=True) != original
    assert report is not body
    assert report.get_crs_auth_code() == "EPSG:28992"
    assert len(report.features) == expected_segments
    if expected_segments:
        segment = report.features[0]
        for actual, expected in zip(
            segment.geometry.coordinates, original["features"][0]["geometry"]["coordinates"], strict=True
        ):
            assert actual == pytest.approx(expected)
        assert segment.properties["segment_length"] > max_segment_length
