import enum
import json
import logging
import os
import pkgutil
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib import resources as impresources
from typing import Annotated, Any, Callable, Union

import pyproj
import uvicorn
import yaml
from fastapi import FastAPI, Header, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from geodense.geojson import CrsFeatureCollection
from geodense.lib import GeodenseError, flatten  # type: ignore  # type: ignore
from geojson_pydantic import Feature
from geojson_pydantic.geometries import Geometry, GeometryCollection

import coordinate_transformation_api
from coordinate_transformation_api import assets
from coordinate_transformation_api.cityjson.models import CityjsonV113
from coordinate_transformation_api.fastapi_rfc7807 import middleware
from coordinate_transformation_api.limit_middleware.middleware import (
    ContentSizeLimitMiddleware,
    TimeoutMiddleware,
)
from coordinate_transformation_api.models import (
    Conformance,
    Crs,
    DensityCheckReport,
    LandingPage,
    Link,
    TransformGetAcceptHeaders,
)
from coordinate_transformation_api.settings import app_settings
from coordinate_transformation_api.util import (
    accept_html,
    convert_point_coords_to_wkt,
    crs_transform,
    densify_request_body,
    density_check_request_body,
    get_src_crs_densify,
    get_transform_get_crss,
    init_oas,
    post_transform_get_crss,
    raise_req_validation_error,
    raise_response_validation_error,
    raise_validation_error,
    set_response_headers,
    transform_coordinates,
    validate_coords_source_crs,
    validate_crs_transformed_geojson,
)

assets_resources = impresources.files(assets)
logging_conf = assets_resources.joinpath("logging.conf")
api_conf = assets_resources.joinpath("config.yaml")


with open(str(api_conf)) as f:
    TRANSFORMATIONS_EXCLUDE = yaml.safe_load(f)["transformations"]["exclude"]


# logging.config.fileConfig(str(logging_conf), disable_existing_loggers=False)
# logger = logging.getLogger("uvicorn")
# # logger.addHandler(logging.StreamHandler())


# logger = logging.getLogger("uvicorn")


OPEN_API_SPEC: dict
API_VERSION: str
CRS_LIST: list[Crs]
OPEN_API_SPEC, API_TITLE, API_VERSION = init_oas()
crs_identifiers: list[str] = OPEN_API_SPEC["components"]["schemas"]["crs-enum"]["enum"]
CRS_LIST = [Crs.from_crs_str(x) for x in crs_identifiers]
BASE_DIR: str = os.path.dirname(__file__)
logger: logging.Logger

CrsEnum: enum = enum.Enum("CrsEnum", {f"{x}": x for x in crs_identifiers})  # type: ignore


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator:
    global logger  # noqa: PLW0603
    logger = logging.getLogger(__name__)
    logger.info(f"settings: {app_settings}")
    logger.info(f"pyproj datadir: {pyproj.datadir.get_data_dir()}")
    if not app_settings.debug:  # suppres pyproj warnings in prod
        logging.getLogger("pyproj").setLevel(logging.ERROR)
    yield


app: FastAPI = FastAPI(docs_url=None, lifespan=lifespan)
# note: order of adding middleware is required for it to work
middleware.register(app)
app.add_middleware(
    ContentSizeLimitMiddleware, max_content_size=app_settings.max_size_request_body
)
app.add_middleware(TimeoutMiddleware, timeout_seconds=app_settings.request_timeout)

if app_settings.cors_allow_origins:
    allow_origins: list[str]
    if app_settings.cors_allow_origins == "*":
        allow_origins = [app_settings.cors_allow_origins]
    else:
        allow_origins = [str(x).rstrip("/") for x in app_settings.cors_allow_origins]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.mount(
    "/static",
    StaticFiles(directory=f"{BASE_DIR}/assets/static"),
    name="static",
)


def exclude_transformation(source_crs_str: str, target_crs_str: str) -> bool:
    if source_crs_str in TRANSFORMATIONS_EXCLUDE and (
        target_crs_str in TRANSFORMATIONS_EXCLUDE[source_crs_str]
    ):
        return True

    return False


@app.middleware("http")
async def add_api_version(request: Request, call_next: Callable) -> Response:
    response_body = {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Not Found",
    }
    response = Response(
        content=json.dumps(response_body),
        status_code=404,
        media_type="application/problem+json",
    )

    if request.url.path != "/" and request.url.path.endswith("/"):
        # overwrite response in case route is a know route with trailing slash
        for route in app.routes:
            if isinstance(route, APIRoute) and request.url.path == f"{route.path}/":
                response_body[
                    "detail"
                ] = f"not found, path contains trailing slash try {route.path}"
                response = Response(
                    content=json.dumps(response_body),
                    status_code=404,
                    media_type="application/problem+json",
                )
    else:
        response = await call_next(request)
    response.headers["API-Version"] = API_VERSION
    return response


@app.get("/openapi", include_in_schema=False)
@app.get("/openapi.html", include_in_schema=False)
async def openapi(
    request: Request, format: Annotated[str | None, Query(alias="f")] = None
) -> Response:
    if format == "html" or (
        accept_html(request) and format != "json"
    ):  # return html when format=html, return json when format=json, but return html when accept header accepts html
        return get_swagger_ui_html(
            openapi_url="./openapi.json",
            title=f"{API_TITLE} - Swagger UI",
            swagger_favicon_url="https://www.nsgi.nl/o/iv-kadaster-business-theme/images/favicon.ico",
        )
    else:  # by default return JSON
        return JSONResponse(
            content=app.openapi(),
            status_code=200,
            media_type="application/json",
        )


@app.get("/", response_model=LandingPage)
async def landingpage():  # type: ignore  # noqa: ANN201
    self = Link(
        title="API Landing Page",
        rel="self",
        href=f"{app_settings.base_url.rstrip('/')}/?f=json",
        type="application/json",
    )

    oas = Link(
        title="Open API Specification as JSON",
        rel="service-desc",
        href=f"{app_settings.base_url.rstrip('/')}/openapi?f=json",
        type="application/openapi+json",
    )

    oas_html = Link(
        title="Open API Specification as HTML",
        rel="service-desc",
        href=f"{app_settings.base_url.rstrip('/')}/openapi?f=html",
        type="text/html",
    )

    conformance = Link(
        title="Conformance Declaration as JSON",
        rel="http://www.opengis.net/def/rel/ogc/1.0/conformance",
        href=f"{app_settings.base_url.rstrip('/')}/conformance",
        type="application/json",
    )
    return LandingPage(
        title=API_TITLE,
        description="Landing page describing the capabilities of this service",
        links=[self, oas, oas_html, conformance],
    )


@app.get("/crss", response_model=list[Crs])
async def crss() -> list[Crs]:
    return CRS_LIST


@app.get("/crss/{crs_id}", response_model=Crs)
async def crs(crs_id: str) -> Crs | Response:
    gen = (crs for crs in CRS_LIST if crs.crs_auth_identifier == crs_id)
    result = next(gen, None)

    if result is None:
        return Response(
            content=json.dumps(
                {
                    "type": "unknown-crs",
                    "title": "Crs Not Found",
                    "status": 404,
                    "detail": crs_id,
                }
            ),
            status_code=404,
            media_type="application/problem+json",
        )
    return result


@app.get("/conformance", response_model=Conformance)
async def conformance() -> Conformance:
    return Conformance(
        conformsTo=[
            "https://docs.ogc.org/is/19-072/19-072.html",
            "https://gitdocumentatie.logius.nl/publicatie/api/adr/",
        ]
    )


@app.post(
    "/densify",
    response_model=Union[Feature, CrsFeatureCollection, Geometry],
    response_model_exclude_none=True,
)
async def densify(  # noqa: ANN201
    body: Union[Feature, CrsFeatureCollection, Geometry, GeometryCollection],
    source_crs: Annotated[CrsEnum | None, Query(alias="source-crs")] = None,
    content_crs: Annotated[CrsEnum | None, Header(alias="content-crs")] = None,
    max_segment_deviation: Annotated[
        float | None, Query(alias="max-segment-deviation", ge=0.0001)
    ] = None,
    max_segment_length: Annotated[
        float | None, Query(alias="max-segment-length", ge=200)
    ] = 200,
):
    source_crs_str: str
    content_crs_str: str

    source_crs_str, content_crs_str = (
        x.value if x is not None else None for x in [source_crs, content_crs]
    )

    s_crs = get_src_crs_densify(body, source_crs_str, content_crs_str)
    densify_request_body(body, s_crs, max_segment_deviation, max_segment_length)
    return JSONResponse(
        content=body.model_dump(exclude_none=True),
        headers=set_response_headers(("content-crs", s_crs)),
    )


@app.post(
    "/density-check",
    response_model=DensityCheckReport,
    response_model_exclude_none=True,
)
async def density_check(  # noqa: ANN201
    body: Union[Feature, CrsFeatureCollection, Geometry, GeometryCollection],
    source_crs: Annotated[CrsEnum | None, Query(alias="source-crs")] = None,
    content_crs: Annotated[CrsEnum | None, Header(alias="content-crs")] = None,
    max_segment_deviation: Annotated[
        float | None, Query(alias="max-segment-deviation", ge=0.0001)
    ] = None,
    max_segment_length: Annotated[
        float | None, Query(alias="max-segment-length", ge=200)
    ] = 200,
):
    source_crs_str: str
    content_crs_str: str

    source_crs_str, content_crs_str = (
        x.value if x is not None else None for x in [source_crs, content_crs]
    )

    s_crs = get_src_crs_densify(body, source_crs_str, content_crs_str)
    try:  # raises GeodenseError when all geometries in body are (multi)point
        report = density_check_request_body(
            body, s_crs, max_segment_deviation, max_segment_length
        )
    except GeodenseError as e:
        raise_req_validation_error(str(e))

    result = DensityCheckReport.from_report(list(flatten(report)))
    return result


@app.get("/transform")
async def transform(  # noqa: PLR0913, ANN201
    coordinates: Annotated[
        str,
        Query(alias="coordinates", pattern=r"^(\d+\.?\d*),(\d+\.?\d*)(,\d+\.?\d*)?$"),
    ],
    source_crs: Annotated[CrsEnum | None, Query(alias="source-crs")] = None,
    target_crs: Annotated[CrsEnum | None, Query(alias="target-crs")] = None,
    content_crs: Annotated[CrsEnum | None, Header(alias="content-crs")] = None,
    accept_crs: Annotated[CrsEnum | None, Header(alias="accept-crs")] = None,
    epoch: Annotated[float | None, Query(alias="epoch")] = None,
    accept: Annotated[str, Header()] = TransformGetAcceptHeaders.json.value,
):
    # get string values from CrsEnum|None parameters
    source_crs_str: str
    target_crs_str: str
    content_crs_str: str
    accept_crs_str: str
    source_crs_str, target_crs_str, content_crs_str, accept_crs_str = (
        x.value if x is not None else None
        for x in [source_crs, target_crs, content_crs, accept_crs]
    )

    if exclude_transformation(source_crs_str, target_crs_str):
        raise_validation_error(
            f"Transformation not possible between {source_crs_str} and {target_crs_str}",
            [("query", "source-crs"), ("query", "target-crs")],
        )

    s_crs, t_crs = get_transform_get_crss(
        source_crs_str, target_crs_str, content_crs_str, accept_crs_str, CRS_LIST
    )

    validate_coords_source_crs(coordinates, s_crs, CRS_LIST)

    transformed_coordinates = transform_coordinates(
        coordinates, s_crs, t_crs, epoch, CRS_LIST
    )

    if float("inf") in [abs(x) for x in transformed_coordinates]:
        raise_response_validation_error(
            "Out of range float values are not JSON compliant", ["responseBody"]
        )
    headers = set_response_headers(("content-crs", t_crs), ("epoch", epoch))
    if accept == str(TransformGetAcceptHeaders.wkt.value):
        wkt_string = convert_point_coords_to_wkt(coordinates)
        PlainTextResponse(wkt_string, headers=headers)
    else:  # default case serve json
        return JSONResponse(
            content={"type": "Point", "coordinates": transformed_coordinates},
            headers=headers,
        )


@app.post(
    "/transform",
    response_model=Union[
        Feature, CrsFeatureCollection, Geometry, GeometryCollection, CityjsonV113
    ],
    response_model_exclude_none=True,
)
async def post_transform(  # noqa: ANN201, PLR0913
    response: Response,
    body: Union[
        Feature, CrsFeatureCollection, Geometry, GeometryCollection, CityjsonV113
    ],
    source_crs: Annotated[CrsEnum | None, Query(alias="source-crs")] = None,
    target_crs: Annotated[CrsEnum | None, Query(alias="target-crs")] = None,
    content_crs: Annotated[CrsEnum | None, Header(alias="content-crs")] = None,
    accept_crs: Annotated[CrsEnum | None, Header(alias="accept-crs")] = None,
    epoch: Annotated[float | None, Query(alias="epoch")] = None,
    density_check: Annotated[bool, Query(alias="density-check")] = True,
    max_segment_deviation: Annotated[
        float | None, Query(alias="max-segment-deviation", ge=0.0001)
    ] = None,
    max_segment_length: Annotated[
        float | None, Query(alias="max-segment-length", ge=200)
    ] = 200,
):
    # get string values from CrsEnum|None parameters
    source_crs_str: str
    target_crs_str: str
    content_crs_str: str
    accept_crs_str: str
    source_crs_str, target_crs_str, content_crs_str, accept_crs_str = (
        x.value if x is not None else None
        for x in [source_crs, target_crs, content_crs, accept_crs]
    )

    if exclude_transformation(source_crs_str, target_crs_str):
        raise_validation_error(
            f"Transformation not possible between {source_crs_str} and {target_crs_str}",
            [("query", "source-crs"), ("query", "target-crs")],
        )

    s_crs, t_crs = post_transform_get_crss(
        body, source_crs_str, target_crs_str, content_crs_str, accept_crs_str, CRS_LIST
    )
    response_headers: dict = {}
    if density_check:
        # TODO: run density_check

        try:  # raises GeodenseError when all geometries in body are (multi)point
            report = density_check_request_body(
                body, s_crs, max_segment_deviation, max_segment_length
            )
            result = DensityCheckReport.from_report(list(flatten(report)))
            if result.passes_check:
                response_headers = set_response_headers(
                    ("density-check-result", "success")
                )
            else:
                response_headers = set_response_headers(
                    ("density-check-result", "failed")
                )
                response.headers.update(
                    {k: v for k, v in response_headers.items() if v}
                )
                raise_validation_error(
                    "density-check failed, run the density-check request to obtain the density-check report",
                    loc=("body",),
                    ctx={"report": result.model_dump_json()},
                )
        except GeodenseError as e:
            if str(e) == "GeoJSON contains only (Multi)Point geometries":
                response_headers = set_response_headers(
                    ("density-check-result", "NotApplicableGeometryType"),
                    headers=response_headers,
                )
            else:
                raise_req_validation_error(str(e), loc=tuple("body"))
    if isinstance(body, CityjsonV113):
        body.crs_transform(s_crs, t_crs, epoch)
        return Response(
            content=body.model_dump_json(exclude_none=True),
            media_type="application/city+json",
        )
    else:
        crs_transform(body, s_crs, t_crs, epoch)
        validate_crs_transformed_geojson(body)
        response_headers = set_response_headers(
            ("content-crs", t_crs), ("epoch", epoch), headers=response_headers
        )
        response_body = body.model_dump(exclude_none=True)
        return JSONResponse(
            content=response_body,
            headers=response_headers,
        )


app.openapi = lambda: OPEN_API_SPEC  # type: ignore


def get_logging_config() -> Any:  # noqa: ANN401
    logging_config = uvicorn.config.LOGGING_CONFIG
    logging_config["loggers"]["uvicorn"]["level"] = app_settings.log_level
    logging_config["loggers"]["uvicorn.error"]["level"] = app_settings.log_level
    logging_config["loggers"]["uvicorn.access"]["level"] = app_settings.log_level

    package = coordinate_transformation_api
    for _importer, modname, _ispkg in pkgutil.walk_packages(
        path=package.__path__, prefix=package.__name__ + ".", onerror=lambda _: None
    ):
        logging_config["loggers"][modname] = {
            "handlers": ["default"],
            "level": app_settings.log_level,
            "propagate": False,
        }
    return logging_config


def main() -> None:
    uvicorn.run(
        f"{__name__}:app",
        workers=1,
        port=8000,
        host="0.0.0.0",  # noqa: S104
        log_level=app_settings.log_level.lower(),
        log_config=get_logging_config(),
        access_log=app_settings.access_log,
        loop="uvloop",
        server_header=False,
        date_header=False,
    )


if __name__ == "__main__":
    main()
