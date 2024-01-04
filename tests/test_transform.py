import pytest
from coordinate_transformation_api.crs_transform import (
    get_transformer,
)


@pytest.mark.parametrize(
    ("s_crs", "t_crs"),
    [
        ("EPSG:7415", "EPSG:9000"),
        ("EPSG:7415", "EPSG:4258"),
    ],
)
def test_get_transformer(s_crs, t_crs):
    tfg = get_transformer(s_crs, t_crs)

    assert tfg
