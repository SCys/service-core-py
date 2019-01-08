"""
database modal
"""

import asyncio
import rapidjson as json

# from functools import wraps

from gino import Gino
from sqlalchemy import create_engine
from sqlalchemy.dialects import registry
from sqlalchemy.engine import Engine

from tornado.options import parse_config_file
from .options import options

_db: Engine = None
md = Gino()


def gen_async(*args, **kwargs) -> Engine:
    global _db

    if _db is None:
        parse_config_file("config.ini")

        if not options.db:
            return None

        registry.register("postgresql.asyncpg", "gino.dialects.asyncpg", "AsyncpgDialect")
        registry.register("asyncpg", "gino.dialects.asyncpg", "AsyncpgDialect")

        kwargs.setdefault("strategy", "gino")
        kwargs.setdefault("json_serializer", lambda obj: json.dumps(obj, datetime_mode=json.DM_ISO8601))
        kwargs.setdefault("json_deserializer", lambda obj: json.loads(obj, datetime_mode=json.DM_ISO8601))

        kwargs.setdefault("echo", False)

        _db = asyncio.get_event_loop().run_until_complete(create_engine(options.db, *args, **kwargs))
        md.bind = _db

    return _db


def gen_sync(*args, **kwargs) -> Engine:
    kwargs.setdefault("pool_size", 30)
    kwargs.setdefault("pool_timeout", 30)
    kwargs.setdefault("max_overflow", 50)
    kwargs.setdefault("json_serializer", lambda obj: json.dumps(obj, datetime_mode=json.DM_ISO8601))
    kwargs.setdefault("json_deserializer", lambda obj: json.loads(obj, datetime_mode=json.DM_ISO8601))

    kwargs.setdefault("echo", False)

    return create_engine(options.db, *args, **kwargs)


class DBHelper:
    @property
    def db(self):
        global _db
        return _db


def db_helper(func):
    """
    add db:Engine as first arg  
    """

    # @wraps
    def with_db(*args, **kwargs):
        global _db
        return func(db=_db, *args, **kwargs)

    return with_db
