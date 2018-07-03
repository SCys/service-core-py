"""
database modal
"""

from gino import Gino
import gino
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from sqlalchemy.dialects import registry
import rapidjson as json

from .options import options


db: Engine = None
md = Gino()

# registry.register('sqlalchemy.asyncpg', 'gino.dialects.asyncpg', 'AsyncpgDialect')
# registry.register('asyncpg', 'gino.dialects.asyncpg', 'AsyncpgDialect')

def gen_async(*args, **kwargs) -> Engine:
    global db

    if db is None:
        registry.register('sqlalchemy.asyncpg', 'gino.dialects.asyncpg', 'AsyncpgDialect')
        registry.register('asyncpg', 'gino.dialects.asyncpg', 'AsyncpgDialect')
        kwargs.setdefault('strategy', 'gino')
        db = gen_sync(*args, **kwargs)
        md.bind = db

    return db


def gen_sync(*args, **kwargs) -> Engine:
    kwargs.setdefault('pool_timeout', 30)
    kwargs.setdefault('json_serializer', lambda obj: json.dumps(obj, datetime_mode=json.DM_ISO8601))
    kwargs.setdefault('json_deserializer', lambda obj: json.load(obj, datetime_mode=json.DM_ISO8601))
    kwargs.setdefault('pool_size', 30)
    kwargs.setdefault('max_overflow', 50)

    return create_engine(options.db, *args, **kwargs)
