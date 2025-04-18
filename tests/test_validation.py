import math
from functools import partial

import pytest

from coordinate_transformation_api.crs_transform import InfValCoordinateError, _round, get_transform_crs_fun
from coordinate_transformation_api.models import TransformationNotPossibleError, get_x_unit_crs
from coordinate_transformation_api.util import str_to_crs
from tests.util import get_test_data


def _test_transformation(source_coord, source_crs, target_crs, test_data):
    source_crs_crs = str_to_crs(source_crs)
    target_crs_crs = str_to_crs(target_crs)

    source_crs_dim = len(source_crs_crs.axis_info)
    target_crs_dim = len(target_crs_crs.axis_info)
    unit = get_x_unit_crs(target_crs_crs)

    inf_val = False
    target_crs_precision = 4 if unit == "metre" else 9
    try:
        api_transformed_coord = get_transform_crs_fun(
            source_crs_crs,
            target_crs_crs,
            precision=target_crs_precision,
            epoch=source_coord[3],
        )(source_coord[0:3])

    except InfValCoordinateError as _:
        inf_val = True
    except TransformationNotPossibleError as e:
        if source_crs_dim < target_crs_dim:
            with pytest.raises(
                TransformationNotPossibleError,
                match=r"number of dimensions source-crs: [0-9], number of dimensions target-crs: [0-9]",
            ):
                raise e
            return  # if we get here source_crs_nr_dim < target_crs_nr_dim and correct excpetion raised test is ok
        else:
            with pytest.raises(
                TransformationNotPossibleError,
                match=r"Transformation not possible between .* and .*, Transformation Excluded",
            ):
                raise e
            return  # if we get here transformation is exluded and test should be OK

    if inf_val:
        api_transformed_coord = (math.inf, math.inf, math.inf)
    f_h_round = partial(_round, target_crs_precision - 1)
    f_v_round = partial(_round, 4)
    coord_test_data = next(filter(lambda x: x[1] == target_crs, test_data))[0]

    coord_test_data_round = tuple(map(f_h_round, coord_test_data[0:2]))

    # if target_crs 3d than add vertical coordinate
    if target_crs_dim == 3:  # noqa: PLR2004
        coord_test_data_round = tuple((*coord_test_data_round, f_v_round(coord_test_data[2])))

    assert api_transformed_coord[0] == pytest.approx(coord_test_data_round[0], 10 ** -(target_crs_precision - 1))
    assert api_transformed_coord[1] == pytest.approx(coord_test_data_round[1], 10 ** -(target_crs_precision - 1))

    if target_crs_dim == 3:  # noqa: PLR2004
        assert api_transformed_coord[2] == pytest.approx(coord_test_data_round[2], 10 ** -(4 - 1))


@pytest.mark.parametrize(("source_coord", "source_crs", "target_crs"), get_test_data("saba_validation_data.csv"))
def test_transformations_nl_saba(source_coord, source_crs, target_crs):
    _test_transformation(source_coord, source_crs, target_crs, get_test_data("saba_validation_data.csv"))


@pytest.mark.parametrize(
    ("source_coord", "source_crs", "target_crs"), get_test_data("st_eustatius_validation_data.csv")
)
def test_transformations_nl_st_eustatius(source_coord, source_crs, target_crs):
    _test_transformation(source_coord, source_crs, target_crs, get_test_data("st_eustatius_validation_data.csv"))


@pytest.mark.parametrize(("source_coord", "source_crs", "target_crs"), get_test_data("bonaire_validation_data.csv"))
def test_transformations_bonaire(source_coord, source_crs, target_crs):
    _test_transformation(source_coord, source_crs, target_crs, get_test_data("bonaire_validation_data.csv"))


@pytest.mark.parametrize(("source_coord", "source_crs", "target_crs"), get_test_data("nl_validation_data.csv"))
def test_transformations_nl_eu(source_coord, source_crs, target_crs):
    _test_transformation(source_coord, source_crs, target_crs, get_test_data("nl_validation_data.csv"))
