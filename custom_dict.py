
from rapidjson import dumps, DM_ISO8601, DM_NAIVE_IS_UTC


__all__ = ['CustomDict']


class CustomDict(object):

    __data__: dict

    def __init__(self, raw=None):
        # setattr(self, '__data__', {})
        self.__dict__['__data__'] = {}

        if isinstance(raw, dict):
            self.__data__.update(raw)

        elif isinstance(raw, CustomDict):
            self.__data__.update(raw.__data__)

    def __eq__(self, other):
        if isinstance(other, CustomDict):
            return self.__data__ == other.__data__
        elif isinstance(other, dict):
            return self.__data__ == other

        return False

    def __bool__(self):
        return self.__data__.__bool__()

    def __contains__(self, key):
        return key in self.__data__

    def __hasattr__(self, key):
        return hasattr(self.__data__, key)

    # Getter by name
    def __getitem__(self, name):
        value = self.data.get(name)
        if isinstance(value, dict):
            return CustomDict(value)

        return value

    def __getattr__(self, name):
        if name in self.__data__:
            return self.__getitem__(name)

        if hasattr(super(), name):
            return getattr(super(), name)

        return None

    # Setter by name with value
    def __setitem__(self, name, value):
        if isinstance(value, CustomDict):
            self.__data__[name] = value.__data__
        else:
            self.__data__[name] = value

    def __setattr__(self, name, value):
        self.__setitem__(name, value)

    def __delitem__(self, name):
        if name in self.__data__:
            del self.__data__

    def __delattr__(self, name):
        self.__delattr__(name)

    def update(self, source=None):
        if source is None:
            pass

        elif isinstance(source, dict):
            self.__data__.update(source)

        elif isinstance(source, CustomDict):
            self.__data__.update(source.__data__)

    def keys(self):
        return self.__data__.keys()

    def dumps(self):
        return dumps(self.___data____, datetime_mode=DM_ISO8601 | DM_NAIVE_IS_UTC)
