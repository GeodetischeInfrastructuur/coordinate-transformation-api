import contextlib
from importlib.metadata import PackageNotFoundError, version

with contextlib.suppress(PackageNotFoundError):
    __version__ = version("coordinate_transformation_api")
