import json

from coordinate_transformation_api.cityjson.models import CityjsonV113
from coordinate_transformation_api.util import str_to_crs


def test_cityjson_transformed():
    with open("tests/data/house_1.city.json") as f:
        data = json.load(f)
        cj = CityjsonV113.model_validate(data)
        cj_original = CityjsonV113.model_validate(data)

        cj.crs_transform(str_to_crs("EPSG:7415"), str_to_crs("EPSG:7931"), 2010.0)
        assert cj.metadata.geographicalExtent != cj_original.metadata.geographicalExtent
        assert cj.vertices != cj_original.vertices
        assert cj.metadata.referenceSystem == "https://www.opengis.net/def/crs/EPSG/0/7931"
        assert cj.transform is not None
        assert cj.transform != cj_original.transform
