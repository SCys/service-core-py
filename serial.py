from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import Dict, List, Optional

from asyncpg import Connection
from orjson import loads
from xid import Xid

from .web import InvalidParams, ObjectNotFound


def _get_table(cls):
    return getattr(cls, "__table_name__"), getattr(cls, "__table_key__")


@dataclass
class BasicFields:
    uuid: str = field(default_factory=lambda: Xid().string())
    info: Dict = field(default_factory=dict)
    ts_created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ts_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    removed: bool = False

    __table_name__ = ""
    __table_key__ = "uuid"


class HasInfoField:

    info: Dict

    def __post_init__(self):
        if isinstance(self.info, str):
            self.info = loads(self.info)


class DumpMethod:
    def dump(self):
        return {field.name: getattr(self, field.name) for field in fields(self.__class__)}


class GetMethod:
    @staticmethod
    async def get(db: Connection, key: str):
        tname, tkey = _get_table(__class__)

        row = await db.fetchrow(f"select * from {tname} where {tkey}=$1 and not removed", key)
        if not row:
            raise ObjectNotFound()

        return __class__.__new__(**dict(row))


class FindMethod:
    @staticmethod
    async def find(db: Connection, values: dict, offset: int, limit: int, order: Optional[str] = None) -> List:
        tname, _ = _get_table(__class__)

        if order:
            o = f"order by {order}"
        else:
            o = "order by ts_created,ts_updated"

        statment_filter = []
        for key in values:
            statment_filter.append(f"{key} = ${len(statment_filter) + 1}")

        q = f"select * from {tname} where {'and '.join(statment_filter)} {o} offset $2 limit $3"
        rows = await db.fetchrow(q, *values.values(), offset, limit)
        if not rows:
            raise ObjectNotFound()

        return [__class__.__new__(**dict(i)) for i in rows]


class CreateMethod:
    @staticmethod
    async def create(db: Connection, values: dict):
        tname, tkey = _get_table(__class__)
        cls_fields = fields(__class__)

        statment_keys = []
        statment_values = []

        for key in values:
            # ignore unknown key
            if key not in cls_fields:
                raise InvalidParams(key)

            statment_keys.append(key)
            statment_values.append(f"${len(statment_keys)}")

        q = f"insert into {tname}({','.join(statment_keys)}) values({','.join(statment_values)}) on conflict do nothing returing {tkey}"
        return await db.fetchval(q, *values.values())


class UpdateMethod:
    async def update(self, db: Connection, values: dict):
        tname, tkey = _get_table(self.__class__)
        cls_fields = fields(self.__class__)

        updated = {}

        async with db.transaction():
            for key, value in values.items():
                # ignore unknown key
                if key not in cls_fields:
                    continue

                # ignore eq old value
                if value == getattr(self, key):
                    continue

                await db.execute(f"update {tname} set {key}=$2 where {tkey}=$1", key, value)

                setattr(self, key, value)
                updated[key] = value

        return updated
