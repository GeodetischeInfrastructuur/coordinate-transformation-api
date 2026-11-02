import contextlib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pyproj

with contextlib.suppress(PackageNotFoundError):
    __version__ = version("coordinate_transformation_api")

_default_proj_data_dir = Path(pyproj.datadir.get_data_dir())
pyproj.datadir.set_data_dir(_default_proj_data_dir.parent / "proj_time_dependent")
