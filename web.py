import asyncio
from core import exception
from core.exception import ErrorBasic, InvalidParams
import configparser
import signal
from decimal import Decimal
from typing import Any, Optional

from aiohttp import web
import asyncpg.pool
import orjson as json
from asyncpg import create_pool

from . import ipgeo
from .config import load_config
from .log import access, info, error, warning, exception, debug

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

    i = info
    d = debug
    e = error
    w = warning
    x = exception

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


def get_info(request):
    return {
        "remote_ip": request.remote,
        "user_agent": request.headers.get("User-Agent"),
        "referrer": request.headers.get("Referer"),
    }


@web.middleware
async def middleware_default(request: web.Request, handler):
    # get X-Forwarded-For
    request = request.clone(remote=request.headers.get("X-Forwarded-For", request.remote))

    # loggers
    request.i = info
    request.e = error
    request.w = warning
    request.d = debug
    request.x = exception

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
    except ErrorBasic as exc:
        error(f"global logic error handle:{str(exc)}")

        access(request, exc)
        resp = web.Response(body=exc.dump(), status=200, content_type="application/json")
    except Exception as exc:
        error(f"global unknown exception:{exc}")

        access(request, exc)
        resp = web.Response(body=json.dumps({"code": 500, "error": str(exc)}), status=200,
                            content_type="application/json")
    else:
        access(request)

    if isinstance(resp, dict):
        resp = web.Response(body=json.dumps(resp, default=_custom_json_dump), status=200,
                            content_type="application/json")

    elif isinstance(resp, str):
        resp = web.Response(text=resp, status=200)

    elif isinstance(resp, ErrorBasic):
        exc = resp
        resp = web.Response(body=exc.dump(), status=200, content_type="application/json")

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

        for route in routes:
            key = route[0]
            if key in ["post", "get", "delete", "put", "option", "head"]:
                method = getattr(self.router, "add_%s" % route[0])
                method(route[1], route[2])
                info(f"add route {route[0]} {route[1]} {route[2]}")

            elif len(route) == 2:
                self.router.add_view(route[0], route[1])
                info(f"add view {route[0]} {route[1]}")

            else:
                error("invalid route:%s", route)
                raise InvalidParams(400, "invalid route")

        self.loop.add_signal_handler(signal.SIGUSR1, self.reload)

        info(f"application initialized")

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
        if "postgresql" in section:
            dsn = section["postgresql"]
            try:
                async def conn_init(con):
                    await con.set_type_codec(
                        "jsonb",
                        schema="pg_catalog",
                        encoder=lambda x: json.dumps(x).decode(),
                        decoder=lambda x: json.loads(x),
                    )

                app.db = await create_pool(
                    dsn=dsn,
                    min_size=1,
                    init=conn_init,
                    command_timeout=5.0,
                    max_inactive_connection_lifetime=600,
                )

            except ConnectionRefusedError:
                exception(f"database pool create failed")

        await ipgeo.load()
