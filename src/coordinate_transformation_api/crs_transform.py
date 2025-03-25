import math
from collections.abc import Callable, Generator
from functools import partial, wraps
from importlib import resources as impresources
from itertools import chain
from typing import Any, cast

import yaml
from geodense.lib import (  # type: ignore
    GeojsonObject,
    InfValCoordinateError,
    transform_geojson_geometries,
)
from geodense.types import GeojsonGeomNoGeomCollection
from geojson_pydantic.geometries import _GeometryBase
from geojson_pydantic.types import (
    BBox,
    MultiLineStringCoords,
    MultiPointCoords,
    MultiPolygonCoords,
    Position,
    Position2D,
    Position3D,
)
from pyproj import CRS, Transformer, transformer
from shapely import GeometryCollection as ShpGeometryCollection
from shapely.geometry import shape

from coordinate_transformation_api import assets
from coordinate_transformation_api.constants import (
    DEFAULT_DIGITS_FOR_ROUNDING,
    HEIGHT_DIGITS_FOR_ROUNDING,
    THREE_DIMENSIONAL,
    TWO_DIMENSIONAL,
)
from coordinate_transformation_api.models import (
    TransformationNotPossibleError,
)
from coordinate_transformation_api.types import CoordinatesType, ShapelyGeometry

assets_resources = impresources.files(assets)
crs_conf = assets_resources.joinpath("crs-config.yaml")
with open(str(crs_conf)) as f:
    CRS_CONFIG = yaml.safe_load(f)


def get_precision(crs: CRS) -> int:
    unit = crs.axis_info[0].unit_name
    if unit == "degree":
        return DEFAULT_DIGITS_FOR_ROUNDING + 5
    return DEFAULT_DIGITS_FOR_ROUNDING


def get_shapely_objects(
    body: GeojsonObject,
) -> list[ShapelyGeometry]:
    def _shapely_object(geometry: GeojsonGeomNoGeomCollection) -> ShapelyGeometry:
        return shape(geometry)  # type: ignore

    result = transform_geojson_geometries(body, _shapely_object)
    flat_result: list[ShapelyGeometry] = []
    # check if result iterable
    if hasattr(result, "__iter__"):
        for item in result:
            if isinstance(item, list):
                flat_result.append(ShpGeometryCollection(item))
            else:
                flat_result.append(item)
    else:
        flat_result = [result]
    return flat_result


def mutate_geom_coordinates(
    coordinates_callback: Callable[
        [Position],
        Position,
    ],
    geom: GeojsonGeomNoGeomCollection,
) -> None:
    """CRS transform geojson geometry objects

    Arguments:
        geom -- geojson geometry object, coordinates of geometry are edited in place
    """
    geom.coordinates = traverse_geojson_coordinates(
        coordinates_callback,
        geom.coordinates,
    )


def traverse_geojson_coordinates(
    callback: Callable[
        [Position],
        Position,
    ],
    geojson_coordinates: (Position | MultiPointCoords | MultiLineStringCoords | MultiPolygonCoords),
) -> Any:  # noqa: ANN401
    """traverse GeoJSON coordinates object and apply callback function to coordinates-nodes

    Args:
        obj: GeoJSON coordinates object
        callback (): callback function to transform coordinates-nodes

    Returns:
        GeoJSON coordinates object
    """
    if not (hasattr(geojson_coordinates, "latitude") and hasattr(geojson_coordinates, "longitude")):
        coords = cast(list[list], geojson_coordinates)
        _self = partial(traverse_geojson_coordinates, callback)
        return list(map(_self, coords))
    else:
        geojson_coordinates_pos = cast(Position, geojson_coordinates)
        position = callback(geojson_coordinates_pos)
        return position


def get_coordinate_from_geometry(
    item: _GeometryBase,
) -> list:
    return list(chain(explode(item.coordinates)))


def explode(coords: Any) -> Generator[Any, Any, None]:  # noqa: ANN401
    """Explode a GeoJSON geometry's coordinates object and yield coordinate tuples.
    As long as the input is conforming, the type of the geometry doesn't matter.
    Source: https://gis.stackexchange.com/a/90554
    """
    for e in coords:
        if isinstance(e, float | int):
            yield coords
            break
        else:
            yield from explode(e)


def get_bbox_from_coordinates(coordinates: Any) -> BBox:  # noqa: ANN401
    coordinate_tuples = list(zip(*list(explode(coordinates)), strict=False))
    if len(coordinate_tuples) == TWO_DIMENSIONAL:
        x, y = coordinate_tuples
        return min(x), min(y), max(x), max(y)
    elif len(coordinate_tuples) == THREE_DIMENSIONAL:
        x, y, z = coordinate_tuples
        return min(x), min(y), min(z), max(x), max(y), max(z)
    else:
        raise ValueError(f"expected dimension of coordinates is either 2 or 3, got {len(coordinate_tuples)}")


def exclude_transformation(source_crs_str: str, target_crs_str: str) -> bool:
    return source_crs_str in CRS_CONFIG and (target_crs_str in CRS_CONFIG[source_crs_str]["exclude-transformations"])


def needs_epoch(tf: Transformer) -> bool:
    # Currently the time-dependent & specific operation method code are hardcoded
    # These are extracted from the 'coordinate_operation_method' table in the proj.db
    static_coordinate_operation_methode_time_dependent = [
        "1053",
        "1054",
        "1056",
        "1057",
    ]
    static_coordinate_operation_methode_time_specific = ["1065", "1066"]
    time_coordinate_operation_methodes = (
        static_coordinate_operation_methode_time_dependent + static_coordinate_operation_methode_time_specific
    )

    has_epoch = False

    if (
        tf.target_crs is not None
        and tf.target_crs.datum is not None
        and tf.target_crs.datum.type_name == "Dynamic Geodetic Reference Frame"
    ):
        has_epoch = True

    if tf.operations is not None:
        for operation in tf.operations:
            if (
                operation.type_name == "Transformation" and operation.method_code in time_coordinate_operation_methodes
            ) or (
                operation.type_name == "Other Coordinate Operation" and "t_epoch=" in operation.to_proj4()
            ):  # fallback voor concatenated operations
                has_epoch = True

    return has_epoch


def check_axis(s_crs: CRS, t_crs: CRS) -> None:
    if len(s_crs.axis_info) < len(t_crs.axis_info):
        raise TransformationNotPossibleError(
            src_crs=s_crs,
            target_crs=t_crs,
            reason=f"number of dimensions source-crs: {len(s_crs.axis_info)}, number of dimensions target-crs: {len(t_crs.axis_info)}",
        )


def get_transformer(source_crs: CRS, target_crs: CRS, epoch: float | None) -> Transformer:  # quit
    # Get available transformer through TransformerGroup
    # TODO check/validate if always_xy=True is correct
    tfg = transformer.TransformerGroup(source_crs, target_crs, allow_ballpark=False, always_xy=True)

    # If everything is 'right' we should always have a transformer
    # based on our configured proj.db. Therefore this error.
    if len(tfg.transformers) == 0:
        raise TransformationNotPossibleError(src_crs=source_crs, target_crs=target_crs)

    # When no input epoch is given we need to check that we don't perform an time-dependent transformation. Otherwise
    # the transformation would be done with a default epoch value, which isn't correct. So we need to search for the "best"
    # transformation that doesn't include a time-dependent operation methode.
    if epoch is None:
        for tf in tfg.transformers:
            if needs_epoch(tf) is not True:
                return tf

    # When reaching this point and the 'only' transformation available is an time-dependent transformation, but no epoch is provided,
    # we don't want to use the 'default' epoch associated with the transformation. Instead, we won't execute the transformation. Because
    # when the transformation is done with the default epoch (e.g. 2010), but the coords are from 2023 this
    # results in wrong results. We prefer giving an exception, rather than a wrong result.
    if needs_epoch(tfg.transformers[0]) is True and epoch is None:
        raise TransformationNotPossibleError(
            src_crs=source_crs,
            target_crs=target_crs,
            reason="Transformation is not possible without an input epoch",
        )

    # Select 1st result. The first result is based on the input parameters the "best" result
    return tfg.transformers[0]


def build_input_coord(coord: CoordinatesType, epoch: float | None) -> CoordinatesType:
    # When 2D input is given with an epoch we need to add a height. So pyproj knows to
    # that the epoch is an epoch and not the height, without this intervention the epoch
    # would be place in the firth position of the tuple.
    if len(coord) == TWO_DIMENSIONAL and epoch is not None:
        return tuple([*coord, 0.0, epoch])

    # Default behaviour
    # The input_coord == coord that are given. When an epoch is provided with a 3D coord
    # this is added or the value None is given for any other. Note: with 2D the additional None
    # is the height. But this doesn't influence the result, because it's None.
    input_coord = tuple(
        [
            *coord,
            (float(epoch) if len(coord) == THREE_DIMENSIONAL and epoch is not None else None),
        ]
    )

    return input_coord


def get_transform_crs_fun_city_json(
    source_crs: CRS,
    target_crs: CRS,
    precision: int | None = None,
    epoch: float | None = None,
) -> Callable[
    [list[float]],
    list[float],
]:
    fun = get_transform_crs_fun(source_crs, target_crs, precision, epoch)

    @wraps(fun)
    def inner(val: list[float]) -> list[float]:
        """wrapper function for transform_crs function to accept and return tuple[float,float,float] for cityjson to satisfy mypy"""
        val_pos = Position3D(*val)
        val_pos_t = fun(val_pos)
        return list(val_pos_t)

    return inner


def get_transform_crs_fun(
    source_crs: CRS,
    target_crs: CRS,
    precision: int | None = None,
    epoch: float | None = None,
) -> Callable[
    [Position],
    Position,
]:
    """TODO: improve type annotation/handling geojson/cityjson transformation, with the current implementation mypy is not complaining"""

    if precision is None:
        precision = get_precision(target_crs)

    check_axis(source_crs, target_crs)
    if exclude_transformation(
        "{}:{}".format(*source_crs.to_authority()),
        "{}:{}".format(*target_crs.to_authority()),
    ):
        raise TransformationNotPossibleError(
            source_crs,
            target_crs,
            "Transformation Excluded",
        )

    # We need to do something special for transformation involving a Compound CRS of 2D coordinates with another height system, like NAP or a LAT height
    # - RD + NAP (EPSG:7415)
    # - ETRS89 + NAP (EPSG:9286)
    # - ETRS89 + LAT-NL (EPSG:9289)
    # These transformations need to be splitted in a horizontal and vertical transformation (vertical transformation actually attempts the 3d transformation).
    if target_crs is not None and source_crs is not target_crs and (target_crs.is_compound or source_crs.is_compound):
        target_crs_horizontal = target_crs.to_2d()
        try:
            h_transformer = get_transformer(source_crs, target_crs_horizontal, epoch)
            v_transformer = get_transformer(
                source_crs, target_crs, epoch
            )  # this will do the 3d transformation that might fail, in that case Z/H value is dropped
        except TransformationNotPossibleError as e:
            raise TransformationNotPossibleError(source_crs, target_crs, reason=e.reason) from e

        # note transformers are injected in transform_compound_crs so they are instantiated only once
        _transform_compound_crs = partial(
            transform_compound_crs, h_transformer, v_transformer, target_crs, precision, epoch
        )
        return _transform_compound_crs
    else:
        transformer = get_transformer(source_crs, target_crs, epoch)
        # note transformer is injected in transform_crs is instantiated once
        # creating transformers is expensive
        _transform_crs = partial(transform_crs, transformer, precision, epoch)
        return _transform_crs


def _round(precision: int | None, val: float) -> float | int:
    if precision is None:
        return val
    else:
        return round(val, precision)


def transform_compound_crs(  # noqa: PLR0913
    hor_transformer: Transformer,
    ver_transformer: Transformer,
    target_crs: CRS,
    precision: int | None,
    epoch: float | None,
    input_pos: Position,
) -> Position:
    target_dim = len(target_crs.axis_info)
    val_epoch = tuple([*input_pos, float(epoch)]) if epoch is not None else tuple([*input_pos])

    round_hor_f = partial(_round, precision)
    round_ver_f = partial(_round, HEIGHT_DIGITS_FOR_ROUNDING)

    hor = tuple(map(round_hor_f, hor_transformer.transform(*val_epoch)))[
        :2
    ]  # can contain z coordinate, since PROJ retains Z value even if target-crs is 2d, so limit to two coordinates

    pos_2d = Position2D(*hor[:2])

    output_pos: Position = pos_2d

    if target_dim == THREE_DIMENSIONAL:
        ver = tuple(map(round_ver_f, ver_transformer.transform(*val_epoch)))  # only
        if len(
            ver
        ) >= THREE_DIMENSIONAL and not math.isinf(  # note len(v) can be larger than three when epoch is supplied
            ver[2]
        ):
            output_pos = Position3D(*pos_2d, ver[2])
        else:
            # height coordinate dropped
            pass

    if any(
        [math.isinf(x) for x in output_pos]
    ):  # checks only positional coordinates, not height. since check if h isinf is already done, and dropped if isinf
        raise InfValCoordinateError("Coordinates contain inf val")

    return output_pos


def transform_crs(
    transformer: Transformer,
    precision: int | None,
    epoch: float | None,
    input_pos: Position,
) -> Position:
    if (
        transformer.target_crs is None
    ):  # check required for retreiving axis_info, otherwise mypy error -> transformer.target_crs: CRS | None
        raise ValueError("transformer.target_crs is None")
    target_dim = len(transformer.target_crs.axis_info)

    # TODO: fix epoch handling, should only be added in certain cases
    # when one of the src or tgt crs has a dynamic time component
    # or the transformation used has a datetime component
    # for now simple check on coords length (which is not correct)
    val_epoch = build_input_coord(input_pos, epoch)

    # GeoJSON and CityJSON by definition has coordinates always in lon-lat-height (or x-y-z) order. Transformer has been created with `always_xy=True`,
    # to ensure input and output coordinates are in in lon-lat-height (or x-y-z) order.
    # Regarding the epoch: this is stripped from the result of the transformer. It's used as a input parameter for the transformation but is not
    # 'needed' in the result, because there is no conversion of time, e.i. an epoch value of 2010.0 will stay 2010.0 in the result. Therefor the result
    # of the transformer is 'stripped' with [0:dim]
    round_hor_f = partial(_round, precision)
    round_ver_f = partial(_round, HEIGHT_DIGITS_FOR_ROUNDING)

    hor_ver = tuple(map(round_hor_f, transformer.transform(*val_epoch)[0:target_dim]))

    pos_2d = Position2D(*hor_ver[:2])

    output_pos: Position = pos_2d

    if len(hor_ver) >= THREE_DIMENSIONAL:  # note len(v) can be larger than three when epoch is supplied
        height = round_ver_f(hor_ver[2])
        if not math.isinf(height):
            output_pos = Position3D(*pos_2d, height)
        else:
            # height coordinate dropped
            pass

    if any([math.isinf(x) for x in output_pos]):
        raise InfValCoordinateError("Coordinates contain inf val")
    return output_pos
