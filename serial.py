from dataclasses import fields

from rapidjson import DM_ISO8601, dumps, loads


class DumpMethod:
    def dump(self):
        return {field.name: getattr(self, field.name) for field in fields(self.__class__)}


class HasInfoField:
    def __post_init__(self):
        if isinstance(self.info, str):
            self.info = loads(self.info)
