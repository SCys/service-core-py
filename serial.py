from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import Dict

from orjson import dumps, loads
from xid import Xid


class DumpMethod:
    def dump(self):
        return {field.name: getattr(self, field.name) for field in fields(self.__class__)}


@dataclass
class BasicFields:
    uuid: str = field(default_factory=lambda: Xid().string())
    info: Dict = field(default_factory=dict)
    ts_created: str = field(default_factory=lambda: datetime.now(timezone.utc))
    ts_updated: str = field(default_factory=lambda: datetime.now(timezone.utc))
    removed: bool = False

    __table_name__ = ""
    __table_key__ = "uuid"


class HasInfoField:
    def __post_init__(self):
        if isinstance(self.info, str):
            self.info = loads(self.info)
