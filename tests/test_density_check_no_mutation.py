from geodense.geojson import CrsFeatureCollection
from pyproj import CRS

from coordinate_transformation_api.util import density_check_request_body


def _body() -> CrsFeatureCollection:
    return CrsFeatureCollection(
        **{
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
        }
    )


def test_density_check_does_not_mutate_body_default_path():
    body = _body()
    reference = body.model_copy(deep=True)

    density_check_request_body(body, CRS.from_epsg(28992), None, 1000.0, None)

    assert body == reference
    assert body.bbox == reference.bbox
    assert body.model_dump() == reference.model_dump()
