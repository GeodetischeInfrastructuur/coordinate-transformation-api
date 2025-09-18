import pytest
from pyproj import CRS

from coordinate_transformation_api.crs_transform import get_transform_crs_fun
from coordinate_transformation_api.models import TransformationNotPossibleError


def test_get_transform_crs_fun_raises_transformation_not_possible_error():
    """Test that get_transform_crs_fun raises TransformationNotPossibleError when attempting
    transformation to an unsupported target CRS.

    This test uses NSGI:Bonaire2004_GEOGRAPHIC_2D as source CRS, which has a limited set
    of supported target CRSs, and attempts transformation to EPSG:28992 (RD New) which
    is not in its supported target CRS list.
    """
    # NSGI:Bonaire2004_GEOGRAPHIC_2D has a limited set of supported target CRSs
    # According to crs-config.yaml, it supports:
    # - NSGI:Bonaire2004_GEOGRAPHIC_2D, OGC:CRS84, EPSG:4326, EPSG:3857,
    #   OGC:CRS84h, NSGI:Bonaire_DPnet, EPSG:9000, EPSG:7912, EPSG:7789,
    #   EPSG:4979, EPSG:32619
    # But does NOT support EPSG:28992 (RD New)
    source_crs = CRS.from_authority("NSGI", "Bonaire2004_GEOGRAPHIC_2D")
    target_crs = CRS.from_authority("EPSG", "28992")  # RD New - not supported

    with pytest.raises(TransformationNotPossibleError) as exc_info:
        get_transform_crs_fun(source_crs, target_crs)

    # Check that the error contains the expected information
    error = exc_info.value
    assert error.src_crs == source_crs
    assert error.target_crs == target_crs
    assert "supported target CRSs for NSGI:Bonaire2004_GEOGRAPHIC_2D are:" in str(error)
    assert "EPSG:28992" not in error.reason  # EPSG:28992 should not be in supported list


def test_get_transform_crs_fun_succeeds_with_supported_target_crs():
    """Test that get_transform_crs_fun succeeds when target CRS is in the supported list.

    This test uses the same source CRS but with a supported target CRS to ensure
    the function works correctly for allowed transformations.
    """
    source_crs = CRS.from_authority("NSGI", "Bonaire2004_GEOGRAPHIC_2D")
    target_crs = CRS.from_authority("EPSG", "4326")  # WGS84 - supported

    # This should not raise an exception
    transform_func = get_transform_crs_fun(source_crs, target_crs)

    # Verify we got a callable function
    assert callable(transform_func)


@pytest.mark.parametrize(
    ("source_auth", "source_code", "target_auth", "target_code"),
    [
        # Test with another limited CRS - use one from the Caribbean region
        ("NSGI", "Saba2020_GEOGRAPHIC_2D", "EPSG", "28992"),  # Saba to RD New - not supported
        ("NSGI", "St_Eustatius_DPnet", "EPSG", "3035"),  # St. Eustatius to LAEA Europe - not supported
    ],
)
def test_get_transform_crs_fun_raises_error_parametrized(source_auth, source_code, target_auth, target_code):
    """Parametrized test for various unsupported transformations."""
    source_crs = CRS.from_authority(source_auth, source_code)
    target_crs = CRS.from_authority(target_auth, target_code)

    with pytest.raises(TransformationNotPossibleError) as exc_info:
        get_transform_crs_fun(source_crs, target_crs)

    error = exc_info.value
    assert error.src_crs == source_crs
    assert error.target_crs == target_crs
    assert "supported target CRSs" in str(error)
