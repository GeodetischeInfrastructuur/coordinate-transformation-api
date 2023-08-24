import json
import logging
import os
from importlib import resources as impresources
from typing import Union

import uvicorn
from fastapi import FastAPI, Header, Query, Request, Response
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import PlainTextResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from geojson_pydantic import Feature, FeatureCollection
from geojson_pydantic.geometries import Geometry, GeometryCollection
from pyproj import network

from coordinates_transformation_api import assets
from coordinates_transformation_api.cityjson.models import CityjsonV113
from coordinates_transformation_api.fastapi_rfc7807 import middleware
from coordinates_transformation_api.limit_middleware.middleware import (
    ContentSizeLimitMiddleware, TimeoutMiddleware)
from coordinates_transformation_api.models import (Conformance, Crs,
                                                   CrsFeatureCollection,
                                                   LandingPage, Link,
                                                   TransformGetAcceptHeaders)
from coordinates_transformation_api.settings import app_settings
from coordinates_transformation_api.util import (get_source_crs_body,
                                                 get_transform_callback,
                                                 get_transformer, init_oas,
                                                 transform_request_body,
                                                 traverse_geojson_coordinates,
                                                 validate_coords_source_crs,
                                                 validate_crss)

assets_resources = impresources.files(assets)
logging_conf = assets_resources.joinpath("logging.conf")


logging.config.fileConfig(str(logging_conf), disable_existing_loggers=False)
logger = logging.getLogger(__name__)
logger.setLevel(app_settings.log_level)
if not app_settings.debug:  # suppres pyproj warnings in prod
    logging.getLogger("pyproj").setLevel(logging.ERROR)


OPEN_API_SPEC: dict
API_VERSION: str
CRS_LIST: list[Crs]
OPEN_API_SPEC, API_TITLE, API_VERSION, CRS_LIST = init_oas()
BASE_DIR: str = os.path.dirname(__file__)

network.set_network_enabled(True)  # TODO: remove before commit

app: FastAPI = FastAPI(docs_url=None)
# note: order of adding middleware is required for it to work
middleware.register(app)
app.add_middleware(
    ContentSizeLimitMiddleware, max_content_size=app_settings.max_size_request_body
)
app.add_middleware(TimeoutMiddleware, timeout_seconds=app_settings.request_timeout)


app.mount(
    "/static",
    StaticFiles(directory=f"{BASE_DIR}/assets/static"),
    name="static",
)


@app.middleware("http")
async def add_api_version(request: Request, call_next):
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
            if isinstance(route, APIRoute):
                if request.url.path == f"{route.path}/":
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
async def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{API_TITLE} - Swagger UI",
        swagger_favicon_url="https://www.nsgi.nl/o/iv-kadaster-business-theme/images/favicon.ico",
    )


@app.get("/", response_model=LandingPage)
async def landingpage():
    self = Link(
        title="This document as JSON",
        rel="self",
        href="http://localhost:8000/?f=json",
        type="application/json",
    )

    return LandingPage(
        title="Coordinatetransformation API",
        description="Landing page describing what the capabilities are of this service",
        links=[self],
    )


@app.get("/crss", response_model=list[Crs])
async def crss():
    return CRS_LIST


@app.get("/crss/{crs_id}", response_model=Crs)
async def crs(crs_id: str):
    gen = (crs for crs in CRS_LIST if crs.crs_auth_identifier == crs_id)
    result = next(gen, None)

    if result == None:
        # TODO: return not found 404

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
async def conformance():
    return Conformance(conformsTo={"mekker", "blaat"})


@app.get("/transform")
async def transform(
    source_crs: str = Query(alias="source-crs"),
    target_crs: str = Query(alias="target-crs"),
    coordinates: str = Query(alias="coordinates"),
    accept: str = Header(default=TransformGetAcceptHeaders.json),
):
    validate_crss(source_crs, target_crs, CRS_LIST)
    validate_coords_source_crs(coordinates, source_crs, CRS_LIST)

    transformer = get_transformer(source_crs, target_crs)

    coordinates_list: list = [float(x) for x in coordinates.split(",")]

    transformed_coordinates = traverse_geojson_coordinates(
        coordinates_list, callback=get_transform_callback(transformer)
    )

    if accept == str(TransformGetAcceptHeaders.wkt.value):
        if len(transformed_coordinates) == 3:
            return PlainTextResponse(
                f"POINT Z ({' '.join([str(x) for x in transformed_coordinates])})"
            )

        return PlainTextResponse(
            f"POINT({' '.join([str(x) for x in transformed_coordinates])})"
        )
    else:  # default case serve json
        return {"type": "Point", "coordinates": transformed_coordinates}


@app.post("/transform", response_model=Union[Feature, FeatureCollection, Geometry, GeometryCollection, CityjsonV113], response_model_exclude_none=True)  # type: ignore
async def transform(
    body: Union[Feature, FeatureCollection, Geometry, GeometryCollection, CityjsonV113],
    source_crs: str | None = Query(alias="source-crs", default=None),
    target_crs: str = Query(alias="target-crs"),
):
    if source_crs is None:
        source_crs = get_source_crs_body(body)
    validate_crss(
        source_crs, target_crs, CRS_LIST
    )  # TODO: add check for crs's in combination with CityJSON (should only allow 3D CRS)
    transformer = get_transformer(source_crs, target_crs)
    if isinstance(body, CityjsonV113):
        callback = get_transform_callback(transformer)


        body.crs_transform(callback, source_crs ,target_crs)
        return Response(
            content=body.model_dump_json(exclude_none=True),
            media_type="application/city+json",
        )
    else:
        transform_request_body(body, transformer)
        return body


app.openapi = lambda: OPEN_API_SPEC  # type: ignore


def main():
    uvicorn.run(
        "coordinates_transformation_api.main:app", workers=2, port=8000, host="0.0.0.0"
    )


if __name__ == "__main__":
    main()
