# copied from https://github.com/vapor-ware/fastapi-rfc7807
import asyncio
import http
import json
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, ResponseValidationError

# from fastapi.openapi.utils import get_openapi
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from coordinate_transformation_api.constants import DENSITY_CHECK_RESULT_HEADER
from coordinate_transformation_api.models import (
    CrsNotFoundError,
    DataValidationError,
    DensityCheckFailedError,
    DensityCheckResult,
    NotFoundError,
)
from coordinate_transformation_api.settings import app_settings

PreHook = Callable[[Request, Exception], Any | Awaitable[Any]]
PostHook = Callable[[Request, Response, Exception], Any | Awaitable[Any]]


logger = logging.getLogger(__name__)


class ProblemResponse(Response):
    """A Response for RFC7807 Problems."""

    media_type: str = "application/problem+json"

    def __init__(
        self: "ProblemResponse",
        *args,  # noqa: ANN002
        debug: bool = False,
        **kwargs,  # noqa: ANN003
    ) -> None:  # type: ignore
        self.debug: bool = debug
        super().__init__(*args, **kwargs)

    def init_headers(self: "ProblemResponse", headers: Mapping[str, str] | None = None) -> None:  # type: ignore
        h = dict(headers) if headers else {}
        if hasattr(self, "problem") and self.problem.headers:
            h.update(self.problem.headers)

        super().init_headers(h)

    def render(self: "ProblemResponse", content: Any) -> bytes:  # noqa: ANN401
        """Render the provided content as an RFC-7807 Problem JSON-serialized bytes."""
        if isinstance(content, ProblemError):
            p = content
        elif isinstance(content, dict):
            p = from_dict(content)
        elif isinstance(content, HTTPException):
            p = from_http_exception(content)
        elif isinstance(content, RequestValidationError):
            p = from_request_validation_error(content)
        elif isinstance(content, DataValidationError):
            p = from_data_validation_error(content)
        elif isinstance(content, NotFoundError):
            p = from_not_found_error(content)
        elif isinstance(content, ResponseValidationError):
            p = from_response_validation_error(content)
        elif isinstance(content, Exception):
            p = from_exception(content)
        else:
            logger.error(f"Got unexpected content when trying to generate error response. Content: {content}")
            if app_settings.debug:  # if debug
                p = ProblemError(
                    status=500,
                    title="Application Error",
                    detail="Got unexpected content when trying to generate error response",
                    content=str(content),
                )
            else:
                p = get_prod_500_problem()

        p.debug = self.debug

        # Dynamically set the response status_code to match
        # the status code of the Problem.
        self.status_code = p.status

        self.problem = p
        return p.to_bytes()


class ProblemError(Exception):
    """An RFC 7807 Problem exception.

    This models a "problem" as defined in RFC 7807 (https://tools.ietf.org/html/rfc7807).
    It is intended to be subclassed to create application-specific instances of
    problems which, when raised, can be trapped by the application error handler
    and converted into HTTP responses with properly-formatted JSON response bodies.

    Default values are applied to the `type`, `status`, and `title` field if
    they are left unspecified.

    It is generally not recommended to modify the Problem instance members
    post-initialization, but nothing prevents you from doing so if you need
    more granular control over how/when values are set.
    """

    def __init__(
        self: "ProblemError",
        type: str | None = None,
        title: str | None = None,
        status: int | None = None,
        detail: str | None = None,
        instance: str | None = None,
        **kwargs,  # noqa: ANN003
    ) -> None:
        self.type: str = type or "about:blank"
        self.status: int = status or 500
        self.title: str = title or http.HTTPStatus(self.status).phrase
        self.detail: str | None = detail
        self.instance: str | None = instance
        self.kwargs: dict = kwargs
        self.headers: dict[str, str] = {}

        # The debug flag determines whether or not the response JSON is pretty-printed,
        # making it easier for humans to read while debugging.
        self.debug: bool = False

    def to_bytes(self: "ProblemError") -> bytes:
        """Render the Problem as JSON-serialized bytes.

        Returns:
            The JSON-serialized bytes representing the Problem response.
        """
        if self.debug:
            return json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
            ).encode("utf-8")
        else:
            return json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                allow_nan=False,
                indent=None,
                separators=(",", ":"),
            ).encode("utf-8")

    def to_dict(self: "ProblemError") -> dict[str, Any]:
        """Get a dictionary representation of the Problem response.

        Returns:
            A dictionary representation of the Problem exception. This can be serialized
            out to JSON and used as the response body.
        """
        d = {}

        # Update the problem dict with kwargs first. In the unlikely event that
        # a Problem instance has its kwargs supplemented with keys which conflict
        # with the keys defined in RFC7807, we do not want the kwargs to override.
        d.update(self.kwargs)

        if self.type:
            d["type"] = str(self.type)
        if self.title:
            d["title"] = str(self.title)
        if self.status:
            d["status"] = int(self.status)
        if self.detail:
            d["detail"] = str(self.detail)
        if self.instance:
            d["instance"] = str(self.instance)
        return d

    def __str__(self: "ProblemError") -> str:
        return str(f"Problem:<{self.to_dict()}>")

    def __repr__(self: "ProblemError") -> str:
        return str(self)

    def __eq__(self: "ProblemError", other: object) -> bool:
        if not isinstance(other, ProblemError):
            return False
        return self.__dict__ == other.__dict__


def from_dict(data: dict[str, Any]) -> ProblemError:
    """Create a new Problem instance from a dictionary.

    This uses the dictionary as keyword arguments for the Problem constructor.
    If the given dictionary does not contain any fields matching those defined
    in the RFC7807 spec, it will use defaults where appropriate (e.g. status
    code 500) and use the dictionary members as supplemental context in the
    Problem response.

    Args:
        data: The dictionary to convert into a Problem exception.

    Returns:
        A new Problem instance populated from the dictionary fields.
    """
    return ProblemError(
        **data,
    )


def get_prod_500_problem() -> ProblemError:
    """Create a HTTP 500 problem response for production use, to not leak implementation details to the client

    Returns:
        Problem: HTTP 500 Problem
    """
    return ProblemError(title="Internal Server Error", status=500, type="about:blank")


def from_http_exception(exc: HTTPException) -> ProblemError:
    """Create a new Problem instance from an HTTPException.

    The Problem will take on the status code of the HTTPException and generate
    a title based on that status code. If the HTTPException specifies any details,
    those will be used as the problem details.

    Args:
        exc: The HTTPException to convert into a Problem exception.

    Returns:
        A new Problem instance populated from the HTTPException.
    """
    return ProblemError(
        status=exc.status_code,
        detail=exc.detail,
    )


def from_response_validation_error(exc: ResponseValidationError) -> ProblemError:
    """Create a new Problem instance from a RequestValidationError.

    The Problem will take on a status code of 400 Bad Request, indicating that
    the user provided data which the server will not process. The title will
    be "Validation Error". The specifics of which fields failed validation
    checks are included as additional Problem context.

    Args:
        exc: The RequestValidationError to convert into a Problem exception.

    Returns:
         A new Problem instance populated from the RequestValidationError.
    """

    return ProblemError(
        title="Response Validation Error",
        status=400,
        detail="The transformed coordinates contain one or more out-of-range float values (inf), which cannot be expressed in GeoJSON",  # only error we check for
        errors=exc.errors(),
    )


def from_data_validation_error(exc: DataValidationError) -> ProblemError:
    extra = {}
    if isinstance(exc, DensityCheckFailedError):
        extra = {"report": exc.report}

    return ProblemError(
        type=exc.type_str,
        title=exc.title,
        status=400,
        detail=str(exc),
        **extra,
        **exc.extra,  # type: ignore
    )


def from_not_found_error(exc: NotFoundError) -> ProblemError:
    extra = {}
    if isinstance(exc, CrsNotFoundError):
        extra = {"crs-id": exc.crs_id}

    return ProblemError(
        type=exc.type_str,
        title=exc.title,
        status=404,
        detail=str(exc),
        **extra,  # type: ignore
    )


def from_request_validation_error(exc: RequestValidationError) -> ProblemError:
    """Create a new Problem instance from a RequestValidationError.

    The Problem will take on a status code of 400 Bad Request, indicating that
    the user provided data which the server will not process. The title will
    be "Validation Error". The specifics of which fields failed validation
    checks are included as additional Problem context.

    Args:
        exc: The RequestValidationError to convert into a Problem exception.

    Returns:
         A new Problem instance populated from the RequestValidationError.
    """

    return ProblemError(
        title="Validation Error",
        status=400,
        detail="One or more user-provided parameters are invalid",
        errors=exc.errors(),
    )


def from_exception(exc: Exception) -> ProblemError:
    """Create a new Problem instance from a broad-class Exception.

    Converting a general Exception into a Problem is indicative of a server
    error, where some exception is not handled explicitly or not wrapped in
    a Problem/HTTPException.

    When creating a Problem from Exception, the Problem will always use the
    500 Server Error status code, however instead of "Server Error" as the
    title, "Unexpected Server Error" is used to indicate that an exception
    was not properly wrapped/raised.

    The exception class is provided as additional Problem context, and the
    exception message is used as Problem details.

    Args:
        exc: The general Exception to convert into a Problem exception.

    Returns:
        A new Problem instance populated from the Exception.
    """
    logger.exception(exc, stack_info=True)
    if app_settings.debug:
        return ProblemError(
            title="Unexpected Server Error",
            status=500,
            detail=str(exc),
            exc_type=exc.__class__.__name__,
        )
    else:
        return get_prod_500_problem()


def get_exception_handler(
    debug: bool = False,
    pre_hooks: Sequence[PreHook] | None = None,
    post_hooks: Sequence[PostHook] | None = None,
) -> Callable:
    """A custom FastAPI exception handler constructor.

    The exception handler which this returns is used to return an RFC7807
    compliant ProblemResponse for the given exception.

    The constructor function lets you specify whether the application is running
    in debug mode, which will cause the error JSON to be pretty-printed for
    easier readability. Otherwise, the JSON response is serialized in a more
    compact format.

    Hooks can be specified for the handler as well. These hooks run before the
    exception is converted into a ProblemResponse and returned. Hooks must take
    a request (starlette.requests.Request) and an Exception as its arguments.
    If the hook raises an exception, the exception is ignored. Hooks can be used
    to add additional logging around exception handling, to collect application
    metrics for error counts, or for any other reason deemed suitable.

    Args:
        debug: Configure the handler for pretty-printing response JSON.
        pre_hooks: Functions which are run before generating a response.
        post_hooks: Functions which are run after generating a response.
    """

    async def exception_handler(request: Request, exc: Exception) -> ProblemResponse:
        nonlocal debug, pre_hooks, post_hooks

        await exec_hooks(pre_hooks, request, exc)
        response = ProblemResponse(exc, debug=debug)
        if response.problem.type == "nsgi.nl/density-check-failed":
            response.headers[DENSITY_CHECK_RESULT_HEADER] = DensityCheckResult.failed.value
        await exec_hooks(post_hooks, request, response, exc)

        return response

    return exception_handler


async def exec_hooks(
    hooks: Sequence[PreHook | PostHook] | None,
    *args,  # noqa: ANN002
) -> None:
    """Helper function to execute hooks, if any are defined.

    Args:
        hooks: The hooks, if any, to execute.
        args: Positional arguments to pass to the hooks.
    """
    if hooks:
        for hook in hooks:
            if asyncio.iscoroutinefunction(hook):
                await hook(*args)
            else:
                hook(*args)


def register(
    app: FastAPI,
    pre_hooks: Sequence[PreHook] | None = None,
    post_hooks: Sequence[PostHook] | None = None,
    add_schema: str | bool = False,  # noqa: ARG001
) -> None:
    """Register the FastAPI RFC7807 middleware with a FastAPI application instance.

    This function registers three things:

    1. An exception handler for HTTPExceptions. This ensures that any HTTPException
       raised by the application is properly converted to an RFC7807 Problem response.
    2. An exception handler for RequestValidationError. This ensures that any validation
       errors (e.g. incorrect params) are formatted into an RFC7807 Problem response.
    3. ProblemMiddleware. This middleware handles all other exceptions raised by the
       application and converts them to RFC7807 Problem responses.

    It is important to note that the ProblemMiddleware which gets registered with
    the application overrides starlette's internal default ServerErrorMiddleware
    by capturing all exceptions before they make it to that handler. As such, this
    means that all errors should return as JSON, but also that previous behavior, e.g.
    of having debug tracebacks for errors displayed in HTML will no longer occur.

    If the FastAPI application is configured for debug mode, this will
    pretty-print the JSON output, making it more human-readable and easier
    to debug. Otherwise, the JSON response is serialized in a more compact
    format.

    This can also add the Problem schema to the application's OpenAPI schema
    definitions. This is useful when you want to have the Problem model defined
    for other responses while preserving the application/problem+json header
    value. For example,

        @app.get(
            path='/',
            responses={
                500: {'model': Problem}
            }
        )
        def root():
            ...

    Using the "model" key would register the Scheme in the generated OpenAPI spec,
    but it would document it with the "application/json" content type. Adding the
    schema via `register` would allow the content type to be set correctly, albiet
    more manually.

        @app.get(
            path='/',
            responses={
                500: {
                    'content': {'application/problem+json': {
                        'schema': {
                            '$ref': '#/components/schemas/Problem',
                        },
                    }},
                }
            }
        )
        def root():
            ...

    Args:
        app: The FastAPI application instance to register with.
        pre_hooks: Functions which are run before generating a response.
        post_hooks: Functions which are run after generating a response.
        add_schema: Add the Problem pydantic model as a schema to the application's
            OpenAPI definitions. If this is a string, it will be added to the
            schema using the string as the name.
    """
    _handler = get_exception_handler(debug=app.debug, pre_hooks=pre_hooks, post_hooks=post_hooks)

    app.add_exception_handler(HTTPException, _handler)
    app.add_exception_handler(RequestValidationError, _handler)
    app.add_middleware(ProblemMiddleware, debug=app.debug, pre_hooks=pre_hooks, post_hooks=post_hooks)

    # if add_schema:
    #     if isinstance(add_schema, str):
    #         name = add_schema
    #     else:
    #         name = "Problem"

    #     # Override the built-in OpenAPI docs generator with the wrapper.
    #     # This allows the RFC7807 Problem schema to be added in, so it can be
    #     # referenced in API route metadata.
    #     def wrap_openapi() -> dict:
    #         if not app.openapi_schema:
    #             app.openapi_schema = get_openapi(
    #                 title=app.title,
    #                 version=app.version,
    #                 openapi_version=app.openapi_version,
    #                 description=app.description,
    #                 routes=app.routes,
    #                 tags=app.openapi_tags,
    #                 servers=app.servers,
    #             )

    #         app.openapi_schema.setdefault("components", {}).setdefault(
    #             "schemas", {}
    #         ).update(
    #             get_model_definitions(
    #                 flat_models={schema.Problem},
    #                 model_name_map={schema.Problem: name},
    #             ),
    #         )
    #         return app.openapi_schema.set

    #     app.openapi = wrap_openapi  # type: ignore


class ProblemMiddleware:
    """Middleware to catch all unhandled exceptions in the stack and return
    a corresponding RFC7807 JSON-formatted response.

    If 'debug' is set, the response JSON will be serialized in a more
    human-readable format, making it easier for debugging. Otherwise, the
    response JSON is serialized in a more compact format.
    """

    def __init__(
        self: "ProblemMiddleware",
        app: ASGIApp,
        debug: bool = False,
        pre_hooks: Sequence[PreHook] | None = None,
        post_hooks: Sequence[PostHook] | None = None,
    ) -> None:
        self.app: ASGIApp = app
        self.pre_hooks = pre_hooks or []
        self.post_hooks = post_hooks or []
        self.debug: bool = debug
        self.received = 0
        self.max_content_size = 2000

        self._handler = get_exception_handler(
            debug=self.debug,
            pre_hooks=self.pre_hooks,
            post_hooks=self.post_hooks,
        )

    # See: starlette.middleware.errors.ServerErrorMiddleware
    async def __call__(self: "ProblemMiddleware", scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def _send(message: Message) -> None:
            nonlocal response_started, send

            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except Exception as exc:
            if not response_started:
                response = await self._handler(Request(scope), exc)
                await response(scope, receive, send)

            # Continue to raise the exception. This allows the exception to
            # be logged, or optionally allows test clients to raise the error
            # in test cases.
            raise exc from None
