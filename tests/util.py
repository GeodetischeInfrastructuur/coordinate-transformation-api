import csv
import itertools
import os
from contextlib import contextmanager
from importlib import resources as impresources

import pytest
import yaml

from coordinate_transformation_api import assets

assets_resources = impresources.files(assets)
crs_conf = assets_resources.joinpath("crs-config.yaml")
with open(str(crs_conf)) as f:
    CRS_CONFIG = yaml.safe_load(f)
TEST_DIR = os.path.dirname(os.path.abspath(__file__))


@contextmanager
def not_raises(exception, message: str | None = ""):
    try:
        yield
    except exception:
        if message != "":
            raise pytest.fail(f"DID RAISE {exception}")  # noqa: B904
        else:
            raise pytest.fail(message.format(exc=exception))  # noqa: B904


def make_entry(line):
    crs = line[0]
    coords = tuple(float(num) for num in line[1].strip("()").split(" "))
    return tuple([crs, coords])


def get_csv(test_data_file_name):
    file = os.path.join(TEST_DIR, "data/transformation_validation", test_data_file_name)

    with open(file) as fread:
        t = [make_entry(line) for line in csv.reader(fread, delimiter=",")]
        return t


def get_test_data(validation_data_filename):
    """transform validation_data containing list of CRS with the coordinates a point in the respective CRS's:

    CRS, SEED_COORDINATE
    NSGI:St_Eustatius2020_GEOCENTRIC,(2764408.9408813603 -5420906.046472443 1904924.7184807751 2000.0)
    ...

    TO:

    FROM_COORDINATE, FROM_CRS, TO_CRS
    (2764408.9408813603, -5420906.046472443, 1904924.7184807751, 2000.0), 'NSGI:St_Eustatius2020_GEOCENTRIC', 'EPSG:32620'
    ...

    Containing all combinations of FROM/TO CRS from the validation_data_filename file.
    """

    test_data = get_csv(validation_data_filename)
    crs_from_to = list(
        filter(
            lambda x: x[0] != x[1]
            and x[1]
            not in CRS_CONFIG[x[0]][
                "exclude-transformations"
            ],  # exlude transform from/to self -> epsg:28992->epsg:28992 and exlude transformations in exclude list
            itertools.product(  # make all crs from/to combinations
                list(
                    map(  # map to extract only CRS list from test_data file
                        lambda x: x[0],
                        test_data,
                    )
                ),
                repeat=2,
            ),
        )
    )
    return [
        (next(filter(lambda y: y[0] == x[0], test_data))[1], x[0], x[1]) for x in crs_from_to
    ]  # add coord to crs_from_to list
