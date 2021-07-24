from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import Dict, List, Optional

from asyncpg import Connection
from orjson import loads
from xid import Xid

from .exception import InvalidParams, ObjectNotFound


def _get_table(cls):
    return getattr(cls, "__table_name__"), getattr(cls, "__table_key__")


@dataclass
class BasicFields:
    id: str = field(default_factory=lambda: Xid().string())
    ts_created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ts_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    removed: bool = False
    info: Dict = field(default_factory=dict)

    __table_name__ = ""
    __table_key__ = "id"


class HasInfoField:
    info: Dict

    def __post_init__(self):
        if isinstance(self.info, str):
            self.info = loads(self.info)


class DumpMethod:
    def dump(self):
        return {i.name: getattr(self, i.name) for i in fields(self.__class__)}


class GetMethod:
    @staticmethod
    async def get(db: Connection, key: str):
        table, key = _get_table(__class__)

        row = await db.fetchrow(f"select * from {table} where {key}=$1 and not removed", key)
        if not row:
            raise ObjectNotFound()

        return __class__.__new__(**dict(row))


class FindMethod:
    @staticmethod
    async def find(db: Connection, values: dict, offset: int, limit: int, order: Optional[str] = None) -> List:
        table, _ = _get_table(__class__)

        if order:
            o = f"order by {order}"
        else:
            o = "order by ts_created,ts_updated"

        statement_filter = []
        for i in values:
            statement_filter.append(f"{i} = ${len(statement_filter) + 1}")

        q = f"select * from {table} where {'and '.join(statement_filter)} {o} offset $2 limit $3"
        rows = await db.fetchrow(q, *values.values(), offset, limit)
        if not rows:
            raise ObjectNotFound()

        return [__class__.__new__(**dict(i)) for i in rows]


class CreateMethod:
    @staticmethod
    async def create(db: Connection, values: dict):
        table, key = _get_table(__class__)
        cls_fields = fields(__class__)

        statement_keys = []
        statement_values = []

        for i in values:
            # ignore unknown key
            if i not in cls_fields:
                raise InvalidParams(i)

            statement_keys.append(i)
            statement_values.append(f"${len(statement_keys)}")

        q = f"insert into {table}({','.join(statement_keys)}) values({','.join(statement_values)}) on conflict do nothing returing {key}"
        return await db.fetchval(q, *values.values())


class UpdateMethod:
    async def update(self, db: Connection, values: dict):
        table, key = _get_table(self.__class__)
        cls_fields = fields(self.__class__)

        updated = {}

        async with db.transaction():
            for k, v in values.items():
                # ignore unknown key
                if k not in cls_fields:
                    continue

                # ignore eq old value
                if v == getattr(self, k):
                    continue

                await db.execute(f"update {table} set {k}=$2 where {key}=$1", k, v)

                setattr(self, k, v)
                updated[k] = v

        return updated
