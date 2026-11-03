import pytest
from pyproj import Transformer

from coordinate_transformation_api.crs_transform import (
    build_input_coord,
    get_transform_crs_fun,
    get_transformer,
    needs_epoch,
)
from coordinate_transformation_api.models import TransformationNotPossibleError
from coordinate_transformation_api.util import str_to_crs


# This test needs the modified proj.time.dependent.transformations.db from
# https://github.com/GeodetischeInfrastructuur/transformations/releases to be configured
# for pyproj to run correctly.
# Assumption is that the behaviour of the modified proj.db return multiple transformations
# The first being the most 'accurate' but requiring a epoch for a correct transformation.
# The second not requiring a epoch.
@pytest.mark.parametrize(
    ("source", "target", "epoch", "expectation"),
    [
        ("EPSG:7415", "EPSG:3857", 2013.3, True),
        ("EPSG:7415", "EPSG:3857", None, False),
    ],
)
def test_time_dependant_operation_method(source, target, epoch, expectation):
    assert needs_epoch(get_transformer(str_to_crs(source), str_to_crs(target), epoch)) == expectation


@pytest.mark.parametrize("target", ["EPSG:9067", "EPSG:7931"])
def test_fixed_operation_to_dynamic_target_does_not_need_epoch(target):
    source_crs = str_to_crs("EPSG:7415")
    target_crs = str_to_crs(target)
    tf = get_transformer(source_crs, target_crs, 2010.0)

    assert tf.target_crs.datum.type_name == "Dynamic Geodetic Reference Frame"
    assert needs_epoch(tf) is False
    assert get_transformer(source_crs, target_crs, None).definition == tf.definition

    coord = (155000.0, 463000.0, 0.0)
    result = get_transform_crs_fun(source_crs, target_crs)(coord)
    for epoch in (2000.0, 2024.0):
        assert get_transform_crs_fun(source_crs, target_crs, epoch=epoch)(coord) == result


def test_time_dependent_operation_still_requires_epoch():
    source_crs = str_to_crs("EPSG:7931")
    target_crs = str_to_crs("EPSG:7789")

    assert needs_epoch(get_transformer(source_crs, target_crs, 2010.0)) is True
    with pytest.raises(TransformationNotPossibleError, match="without an input epoch"):
        get_transformer(source_crs, target_crs, None)


@pytest.mark.parametrize(
    ("pipeline", "expectation"),
    [
        ("+proj=helmert +x=1 +y=2 +z=3", False),
        ("+proj=helmert +x=1 +y=2 +z=3 +dx=0.1 +t_epoch=2010", True),
    ],
)
def test_pipeline_without_operation_metadata(pipeline, expectation):
    tf = Transformer.from_pipeline(pipeline)

    assert not tf.operations
    assert needs_epoch(tf) is expectation


@pytest.mark.parametrize(
    ("coord", "epoch", "expectation"),
    [
        (tuple([1000.0, 1000.0]), 2000.0, tuple([1000.0, 1000.0, 0.0, 2000.0])),
        (tuple([1000.0, 1000.0]), None, tuple([1000.0, 1000.0, None])),
        (tuple([1000.0, 1000.0, 10.0]), 2000.0, tuple([1000.0, 1000.0, 10.0, 2000.0])),
        (tuple([1000.0, 1000.0, 10.0]), None, tuple([1000.0, 1000.0, 10.0, None])),
    ],
)
def test_build_input_coord(coord, epoch, expectation):
    assert build_input_coord(coord, epoch) == expectation
