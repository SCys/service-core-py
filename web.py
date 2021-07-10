import asyncio
import time
import configparser
import signal
import sys
from decimal import Decimal
from typing import Any, Optional

from aiohttp import web
import asyncpg.pool
import orjson as json
from asyncpg import create_pool

from . import ipgeo
from .config import load_config
from .log import logger_access
from .log import logger_app as logger
from .utils import setup_autoreload

if sys.platform != "win32":
    # import uvloop not on win32 platform
    try:
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass


def _custom_json_dump(obj):
    if hasattr(obj, "dump"):
        return obj.dump()

    elif isinstance(obj, Decimal):
        return float(obj)


class BasicHandler(web.View):

    user: Any = None

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
    def data(self) -> dict:
        return self.request.data

    @property
    def params(self) -> dict:
        return self.request.params

    @property
    def config(self) -> configparser.ConfigParser:
        return self.request.app.config


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
    remote = request.remote
    url = request.url

    if exception is None:
        logger_access.info(f"{remote} - {url}")
        return

    logger_access.info(f"{remote} - {url} - {exception.code}:{exception.error}")


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


@web.middleware
async def middleware_default(request: web.Request, handler):
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
            data = json.loads(content)
            params = data.get("params", {})
        else:
            data = {"params": {}}
            params = {}
    request.data = data
    request.params = params

    # run handler and handle the exception
    try:
        resp = await handler(request)
        if isinstance(resp, dict):
            resp = web.Response(
                body=json.dumps(resp, default=_custom_json_dump),
                status=200,
                content_type="application/json",
            )

        elif isinstance(resp, str):
            resp = web.Response(text=resp, status=200)

        else:
            resp = resp

    except ErrorBasic as exc:
        a(request, exc)
        resp = web.Response(
            body=json.dumps({"code": exc.code, "error": exc.error}, default=_custom_json_dump),
            status=200,
            content_type="application/json",
        )
    else:
        a(request)

    return resp


class Application(web.Application):
    db: Optional[asyncpg.pool.Pool] = None
    config: configparser.ConfigParser

    def __init__(self, routes, **kwargs):
        self.db = None

        self.config = load_config()

        if "client_max_size" not in kwargs:
            kwargs["client_max_size"] = 1024 * 1024 * 64  # 64M

        if "loop" not in kwargs:
            kwargs["loop"] = asyncio.get_event_loop()

        super().__init__(**kwargs)

        self.middlewares.append(middleware_default)
        self.on_startup.append(self.setup)

        self.logger = logger

        for route in routes:
            key = route[0]
            if key in ["post", "get", "delete", "put", "option", "head"]:
                method = getattr(self.router, "add_%s" % route[0])
                method(route[1], route[2])
                logger.info(f"add route {route[0]} {route[1]} {route[2]}")

            elif len(route) == 2:
                self.router.add_view(route[0], route[1])
                logger.info(f"add view {route[0]} {route[1]}")

            else:
                logger.error("invalid route:%s", route)
                raise InvalidParams(400, "invalid route")

        self.loop.add_signal_handler(signal.SIGUSR1, self.reload)

        logger.info(f"application initialized")

    def start(self):
        self.middlewares.freeze()
        self.on_startup.append(self.setup)

        config = load_config()
        section = config["http"]

        host = section.get("host", "127.0.0.1")
        port = section.getint("port", 8080)

        web.run_app(self, host=host, port=port)

    def reload(self):
        self.config = load_config()

    @staticmethod
    async def setup(app):
        config = load_config()
        section = config["database"]

        # setup database connection
        if "dsn" in section:
            db_dsn = section.get("dsn")
            app.db = await create_pool(dsn=db_dsn, min_size=1, command_timeout=5.0, max_inactive_connection_lifetime=600)

        await ipgeo.load()
