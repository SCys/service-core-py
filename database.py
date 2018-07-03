"""
database modal
"""

import asyncio

from gino import Gino
from sqlalchemy import create_engine
from sqlalchemy.dialects import registry
from sqlalchemy.engine import Engine

import rapidjson as json

from .options import options

_db: Engine = None
md = Gino()


def gen_async(*args, **kwargs) -> Engine:
    global _db

    if _db is None:
        registry.register('postgresql.asyncpg', 'gino.dialects.asyncpg', 'AsyncpgDialect')
        registry.register('asyncpg', 'gino.dialects.asyncpg', 'AsyncpgDialect')

        kwargs.setdefault('strategy', 'gino')
        kwargs.setdefault('json_serializer', lambda obj: json.dumps(obj, datetime_mode=json.DM_ISO8601))
        kwargs.setdefault('json_deserializer', lambda obj: json.load(obj, datetime_mode=json.DM_ISO8601))
        _db = asyncio.get_event_loop().run_until_complete(create_engine(options.db, *args, **kwargs))
        md.bind = _db

    return _db


def gen_sync(*args, **kwargs) -> Engine:
    kwargs.setdefault('pool_size', 30)
    kwargs.setdefault('pool_timeout', 30)
    kwargs.setdefault('max_overflow', 50)
    kwargs.setdefault('json_serializer', lambda obj: json.dumps(obj, datetime_mode=json.DM_ISO8601))
    kwargs.setdefault('json_deserializer', lambda obj: json.load(obj, datetime_mode=json.DM_ISO8601))

    return create_engine(options.db, *args, **kwargs)
