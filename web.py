import asyncio
import configparser
import gzip
import io
import sys
from decimal import Decimal
from typing import Optional

import aiohttp.web
import asyncpg.pool
from asyncpg import create_pool

from orjson import dumps, loads

from . import ipgeo
from .logging import access_logger
from .logging import app_logger as logger

if sys.platform != "win32":
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def _custom_json_dump(obj):
    if hasattr(obj, "dump"):
        return obj.dump()

    elif isinstance(obj, Decimal):
        return float(obj)


class BasicHandler(aiohttp.web.View):

    request: aiohttp.web.Request

    def i(self, *args, **kwargs):
        self.request.i(*args, **kwargs)

    def d(self, *args, **kwargs):
        self.request.d(*args, **kwargs)

    def e(self, *args, **kwargs):
        self.request.e(*args, **kwargs)

    def w(self, *args, **kwargs):
        self.request.w(*args, **kwargs)

    def get_info(self):
        return get_info(self.request)

    @property
    def db(self) -> Optional[asyncpg.pool.Pool]:
        return self.request.db

    @property
    def data(self):
        return self.request.data

    @property
    def params(self):
        return self.request.params


class ErrorBasic(Exception):
    code = 500
    error = "unknown error"

    def __init__(self, code=None, msg=None):
        if code is not None:
            self.code = code
        if msg is not None:
            self.error = msg

        self.status_code = self.code
        self.reason = self.error
        self.log_message = None

    def dump(self):
        return {"code": self.code, "error": self.error}


class ServerError(ErrorBasic):
    code = 500
    error = "server error"


class InvalidParams(ErrorBasic):
    code = 400
    error = "invalid params"


class ObjectNotFound(ErrorBasic):
    code = 404
    error = "object not found"


class Unauthorized(ErrorBasic):
    code = 401
    error = "unauthorized"


class KeyConflict(ErrorBasic):
    code = 409
    error = "key conflict"


class NoPermission(ErrorBasic):
    code = 403
    error = "no permission"


class RemoteServerError(ErrorBasic):
    code = 502
    error = "remote server error"


def get_info(request):
    return {
        "remote_ip": request.remote,
        "user_agent": request.headers.get("User-Agent"),
        "referrer": request.headers.get("Referer"),
    }


def a(request, exception=None):
    if exception is None:
        access_logger.info("%s - %s 200 -", request.remote, request.url)
    else:
        access_logger.info("%s - %s 200 - %d %s", request.remote, request.url, exception.code, exception.error)


def w(msg, *args, **kwargs):
    # logger.warning("[%s]%s" % (self.__class__.__name__, msg), *args, **kwargs)
    logger.warning("%s" % (msg), *args, **kwargs)


def e(msg, *args, **kwargs):
    # logger.error("[%s]%s" % (self.__class__.__name__, msg), *args, **kwargs)
    logger.error("%s" % (msg), *args, **kwargs)


def i(msg, *args, **kwargs):
    # logger.info("[%s]%s" % (self.__class__.__name__, msg), *args, **kwargs)
    logger.info("%s" % (msg), *args, **kwargs)


def d(msg, *args, **kwargs):
    # logger.debug("[%s]%s" % (self.__class__.__name__, msg), *args, **kwargs)
    logger.debug("%s" % (msg), *args, **kwargs)


@aiohttp.web.middleware
async def middleware_default(request: aiohttp.web.Request, handler):
    # get X-Forwarded-For
    request = request.clone(remote=request.headers.get("X-Forwarded-For", request.remote))

    # loggers
    request.w = w
    request.e = e
    request.i = i
    request.d = d

    request.get_info = lambda: get_info(request)

    # inspect
    request.db = request.app.db

    # parse json
    data: dict = {}
    params: dict = {}
    if request.body_exists and ("application/json" in request.content_type or "text/plain" in request.content_type):
        content = await request.text()
        if content:
            data = loads(content, datetime_mode=DM_ISO8601)
            params = data.get("params", {})
        else:
            data = {"params": {}}
            params = {}
    request.data = data
    request.params = params

    # parse ipgeo

    # run handler and handle the exception
    try:
        trunk = await handler(request)
        if isinstance(trunk, dict):
            response = aiohttp.web.Response(
                body=dumps(trunk, default=_custom_json_dump), status=200, content_type="application/json",
            )

        elif isinstance(trunk, str):
            response = aiohttp.web.Response(text=trunk, status=200)

        else:
            response = trunk

    except ErrorBasic as exc:
        a(request, exc)
        response = aiohttp.web.Response(
            body=dumps({"code": exc.code, "error": exc.error}, default=_custom_json_dump),
            status=200,
            content_type="application/json",
        )
    else:
        a(request)
    return response


class Application(aiohttp.web.Application):
    __version__ = "0.2.6"

    db: Optional[asyncpg.pool.Pool] = None
    config: configparser.ConfigParser

    def __init__(self, routes, **kwargs):
        self.db = None

        # read main.ini
        config = configparser.ConfigParser()
        config["default"] = {}
        self.config = config
        self.config.read("./main.ini")

        kwargs["client_max_size"] = 1024 * 1024 * 512  # 512M
        super().__init__(**kwargs)

        self.middlewares.append(middleware_default)

        self.logger = logger

        for route in routes:
            key = route[0]
            if key in ["post", "get", "delete", "put", "option", "head"]:
                method = getattr(self.router, "add_%s" % route[0])
                method(route[1], route[2])
                logger.info("add route %s %s %s", *route)
            elif len(route) == 2:
                self.router.add_view(route[0], route[1])
                logger.info("add view %s %s", *route)
            else:
                logger.error("invalid route:%s", route)
                raise InvalidParams(400, "invalid route")

        logger.info("application(%s) initialized", self.__version__)

    def start(self):
        self.middlewares.freeze()
        self.on_startup.append(self.setup)

        section = self.config["default"]
        host = section.get("host", "0.0.0.0")
        port = int(section.get("port", 80))

        aiohttp.web.run_app(self, host=host, port=port)

    @staticmethod
    async def setup(app):
        section = app.config["default"]

        # setup database connection
        db_dsn = section.get("dsn")
        if db_dsn:
            db_size = app.config["default"].get("db_size", 50)
            app.db = await create_pool(
                dsn=db_dsn, min_size=5, max_size=db_size, command_timeout=5.0, max_inactive_connection_lifetime=600
            )

        await ipgeo.ip2region_update()
