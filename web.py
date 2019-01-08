import asyncio
import configparser
import sys
from decimal import Decimal
from rapidjson import DM_ISO8601, dumps, loads

import aiohttp.web
import asyncio_redis
from asyncpg import Connection, create_pool

from .logging import app_logger, access_logger

if sys.platform != "win32":
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def _custom_json_dump(obj):
    if hasattr(obj, "dump"):
        return obj.dump()

    elif isinstance(obj, Decimal):
        return float(obj)


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
    app_logger.warning("%s" % (msg), *args, **kwargs)


def e(msg, *args, **kwargs):
    # logger.error("[%s]%s" % (self.__class__.__name__, msg), *args, **kwargs)
    app_logger.error("%s" % (msg), *args, **kwargs)


def i(msg, *args, **kwargs):
    # logger.info("[%s]%s" % (self.__class__.__name__, msg), *args, **kwargs)
    app_logger.info("%s" % (msg), *args, **kwargs)


def d(msg, *args, **kwargs):
    # logger.debug("[%s]%s" % (self.__class__.__name__, msg), *args, **kwargs)
    app_logger.debug("%s" % (msg), *args, **kwargs)


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
    request.redis = request.app.redis

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

    # run handler and handle the exception
    try:
        trunk = await handler(request)
        if isinstance(trunk, dict):
            response = aiohttp.web.Response(
                body=dumps(trunk, datetime_mode=DM_ISO8601, default=_custom_json_dump),
                status=200,
                content_type="application/json",
            )

        elif isinstance(trunk, str):
            response = aiohttp.web.Response(text=str, status=200)

        else:
            response = trunk

    except ErrorBasic as exc:
        a(request, exc)
        response = aiohttp.web.Response(
            body=dumps({"code": exc.code, "error": exc.error}, datetime_mode=DM_ISO8601, default=_custom_json_dump),
            status=200,
            content_type="application/json",
        )
    else:
        a(request)
    return response


class Application(aiohttp.web.Application):
    __version__ = "0.2.6"

    db: Connection
    redis: asyncio_redis.Pool
    config: configparser.ConfigParser

    def __init__(self, routes, **kwargs):
        self.db = None
        self.redis = None
        self.server = None

        # read main.ini
        self.config = configparser.ConfigParser()
        self.config.read("./main.ini")

        kwargs["client_max_size"] = 1024 * 1024 * 512  # 512M
        super().__init__(**kwargs)

        self.middlewares.append(middleware_default)

        self.logger = app_logger

        for route in routes:
            method = getattr(self.router, "add_%s" % route[0])
            method(route[1], route[2])
            app_logger.info("add route %s %s %s", *route)

        app_logger.info("application(%s) initialized", self.__version__)

    def start(self):
        self.middlewares.freeze()
        self.on_startup.append(self.setup)

        host = self.config["default"].get("host", "0.0.0.0")
        port = self.config["default"].get("port", 80)

        aiohttp.web.run_app(self, host=host, port=port)

    @staticmethod
    async def setup(app):
        db_dsn = app.config["default"]["dsn"]
        db_size = app.config["default"].get("db_size", 50)
        app.db = await create_pool(
            dsn=db_dsn, min_size=5, max_size=db_size, command_timeout=5.0, max_inactive_connection_lifetime=600
        )

        app.redis = await asyncio_redis.Pool.create(
            host=app.config["default"].get("redis_host"), port=int(app.config["default"].get("redis_port"))
        )

