import argparse
import os
from pathlib import Path

import yaml
from pyproj import transformer

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
filename = Path(f"{TEST_DIR}/../src/coordinate_transformation_api/assets/crs-config.yaml").resolve()


with open(str(filename)) as f:
    CRS_CONFIG = yaml.safe_load(f)


def get_allowed_tranformation(seed_crs):
    all_crs = set(CRS_CONFIG.keys())
    excluded_crs = set(CRS_CONFIG[seed_crs]["exclude-transformations"])

    if "test-exclude-time-dependent-transformations" in CRS_CONFIG[seed_crs]:
        excluded_crs_time_dependent_test = set(CRS_CONFIG[seed_crs]["test-exclude-time-dependent-transformations"])
        excluded_crs = excluded_crs.union(excluded_crs_time_dependent_test)
    result = list(all_crs.difference(excluded_crs))
    result.sort()
    return result  # difference:  Elements in all_crs but not in excluded_crs


get_allowed_tranformation("NSGI:Bonaire_DPnet_KADpeil")


def do_pyproj_transformation(source_crs: str, target_crs: str, coords: tuple[float, ...]) -> tuple[float, ...]:
    tfg = transformer.TransformerGroup(source_crs, target_crs, allow_ballpark=False, always_xy=True)

    if len(tfg.transformers) == 0:
        return (float("inf"), float("inf"), float("inf"), float("inf"))

    return tfg.transformers[0].transform(*coords)  # type: ignore


def make_entry(line):
    crs = line[0]
    coords = tuple(float(num) for num in line[1].strip("()").split(" "))
    return tuple([crs, coords])


def validation_data(crs_list, seed_crs, seed_coord, output_file_name, overwrite=False):
    file = os.path.join(TEST_DIR, "data/transformation_validation", output_file_name)

    if os.path.isfile(file) is True and os.stat(file).st_size != 0 and not overwrite:
        raise FileExistsError(f"{file} already exists, use overwrite flag to overwrite existing file")
    else:
        with open(file, "w") as fwrite:
            for target_crs in crs_list:
                source_coord = do_pyproj_transformation(seed_crs, target_crs, seed_coord)
                fwrite.write(
                    "{},{}\n".format(
                        target_crs,
                        "({} {} {} {})".format(*source_coord),
                    )
                )


def main(area, overwrite):
    if area == "bonaire":
        seed_crs = "NSGI:Bonaire_DPnet_KADpeil"
        seed_coord = (23000.0000, 18000.0000, 10.0000, 2000)
        filename = "bonaire_validation_data.csv"

    elif area == "nl":
        seed_crs = "EPSG:7415"
        seed_coord = (0, 400000, 43, 2000)
        filename = "nl_validation_data.csv"

    elif area == "saba":
        seed_crs = "NSGI:Saba_DPnet_Height"
        seed_coord = (5000.0000, 1000.0000, 300.0000, 2000)
        filename = "saba_validation_data.csv"

    elif area == "st_eustatius":
        seed_crs = "NSGI:St_Eustatius_DPnet_Height"
        seed_coord = (502000.0000, 1934000.0000, 100.0000, 2000)
        filename = "st_eustatius_validation_data.csv"

    crs_list = get_allowed_tranformation(seed_crs)
    validation_data(crs_list, seed_crs, seed_coord, filename, overwrite)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate test data for one of the four areas, run this script from the test directory to regenerate test data. Test data should be checked manunally to ensure it is correct (since we are testing against it).",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    areas = ["nl", "saba", "st_eustatius", "bonaire"]
    parser.add_argument(
        "area",
        type=str,
        choices=[*areas, "all"],
        help="Specify one of the following areas:\n"
        "  nl - The Netherlands\n"
        "  saba - Saba\n"
        "  st_eustatius - Sint Eustatius\n"
        "  bonaire - Bonaire\n"
        "  all - Generate for all areas",
    )
    parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite existing files if they exist")
    args = parser.parse_args()
    if args.area != "all":
        areas = [args.area]

    for area in areas:
        print(area)
        main(area, args.overwrite)
