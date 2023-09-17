import asyncio
import configparser
import signal
from decimal import Decimal
from typing import Any, Callable, Dict, Optional

import asyncpg
import asyncpg.pool
import orjson as json
import sqlalchemy.ext.asyncio
from aiohttp import web, typedefs
import orjson

from . import config, ipgeo, log
from .exception import ErrorBasic, InvalidParams

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

typedefs.DEFAULT_JSON_ENCODER = orjson.dumps
typedefs.DEFAULT_JSON_DECODER = orjson.loads


def _custom_json_dump(obj):
    if hasattr(obj, "dump"):
        return obj.dump()

    elif isinstance(obj, Decimal):
        return float(obj)


class CustomRequest(web.Request):
    db: Optional[asyncpg.pool.Pool | sqlalchemy.ext.asyncio.AsyncSession]
    data: Dict
    params: Dict

    i: Callable = log.info
    e: Callable = log.error
    w: Callable = log.warning
    d: Callable = log.debug
    x: Callable = log.exception

    get_info: Callable


class BasicHandler(web.View):
    user: Any = None

    i = log.info
    d = log.debug
    e = log.error
    w = log.warning
    x = log.exception

    request: CustomRequest

    def get_info(self):
        return get_info(self.request)

    @property
    def db(self) -> Optional[asyncpg.pool.Pool | sqlalchemy.ext.asyncio.AsyncSession]:
        return self.request.db

    @property
    def data(self) -> Dict:
        return self.request.data

    @property
    def params(self) -> Dict:
        return self.request.params

    @property
    def config(self) -> configparser.ConfigParser:
        app: "Application" = self.request.app
        return app.config


def get_info(request):
    return {
        "remote_ip": request.remote,
        "user_agent": request.headers.get("User-Agent"),
        "referrer": request.headers.get("Referrer"),
    }


@web.middleware
async def middleware_default(request: web.Request, handler):
    # get X-Forwarded-For
    request: CustomRequest = request.clone(remote=request.headers.get("X-Forwarded-For", request.remote))
    app: "Application" = request.app

    request.get_info = lambda: get_info(request)

    # inspect
    request.db = app.db

    # parse json
    data: Dict = {}
    params: Dict = {}
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
        log.error(f"global logic error handle:{str(exc)}")

        log.access(request, exc)
        resp = web.Response(body=exc.dump(), status=200, content_type="application/json")
    except Exception as exc:
        log.error(f"global unknown exception:{exc}")

        log.access(request, exc)
        resp = web.Response(body=json.dumps({"code": 500, "error": str(exc)}), status=200, content_type="application/json")
    else:
        log.access(request)

    if isinstance(resp, dict):
        resp = web.Response(body=json.dumps(resp, default=_custom_json_dump), status=200, content_type="application/json")

    elif isinstance(resp, str):
        resp = web.Response(text=resp, status=200)

    elif isinstance(resp, ErrorBasic):
        exc = resp
        resp = web.Response(body=exc.dumps(), status=200, content_type="application/json")

    return resp


class Application(web.Application):
    db: Optional[asyncpg.pool.Pool | sqlalchemy.ext.asyncio.AsyncSession]
    config: configparser.ConfigParser

    def __init__(self, routes, **kwargs):
        self.db = None
        self.config = config.load()

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
                log.info(f"add route {route[0]} {route[1]} {route[2]}")

            elif len(route) == 2:
                self.router.add_view(route[0], route[1])
                log.info(f"add view {route[0]} {route[1]}")

            else:
                log.error("invalid route:%s", route)
                raise InvalidParams(400, "invalid route")

        self.loop.add_signal_handler(signal.SIGUSR1, self.reload)

        log.info(f"application initialized")

    def start(self):
        self.middlewares.freeze()
        self.on_startup.append(self.setup)

        section = self.config.get("http")
        host = section.get("host", "127.0.0.1")
        port = section.getint("port", 8080)

        web.run_app(self, host=host, port=port, loop=self.loop)

    def reload(self):
        self.config = config.reload()

    @staticmethod
    async def setup(app: "Application"):
        section = app.config["database"]
        debug = app.config.getboolean("default", "debug", fallback=False)

        # setup postgresql connections
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

                app.db = await asyncpg.create_pool(
                    dsn=dsn,
                    min_size=1,
                    init=conn_init,
                    command_timeout=5.0,
                    max_inactive_connection_lifetime=600,
                )

                log.info(f"postgresql pool created")

            except ConnectionRefusedError:
                log.exception(f"postgresql pool create failed")

        if "sqlalchemy" in section:
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy.orm import sessionmaker

            engine = await create_async_engine(section["sqlalchemy"], echo=debug)
            app.db = sessionmaker(bind=engine)

            log.info(f"sqlalchemy pool created")

        await ipgeo.load()
