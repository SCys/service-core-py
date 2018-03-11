
from rapidjson import dumps, DM_ISO8601, DM_NAIVE_IS_UTC

__all__ = ['CustomDict']


class CustomDict(object):

    _data: dict

    def __init__(self, raw=None):
        if isinstance(raw, dict):
            self._data = raw

        elif isinstance(raw, CustomDict):
            self._data = raw.data

        else:
            self._data = {}

    def __eq__(self, other):
        if isinstance(other, CustomDict):
            return self._data == other._data
        elif isinstance(other, dict):
            return self._data == other

        return False

    def __bool__(self):
        return self._data.__bool__()

    def __contains__(self, key):
        return key in self._data

    def __hasattr__(self, key):
        return hasattr(self._data, key)

    # Getter by name
    def __getitem__(self, name):
        value = self.data.get(name)
        if isinstance(value, dict):
            return CustomDict(value)

        return value

    def __getattr__(self, name):
        if hasattr(super(), name):
            return getattr(super(), name)

        if name in self.__dict__:
            return self.__dict__[name]

        if name in self._data:
            return self.__getitem__(name)

        return None

    # Setter by name with value
    def __setitem__(self, name, value):
        if isinstance(value, CustomDict):
            self._data[name] = value._data
        else:
            self._data[name] = value

    def __setattr__(self, name, value):
        self.__setitem__(name, value)

    def __delitem__(self, name):
        if name in self._data:
            del self._data

    def __delattr__(self, name):
        self.__delattr__(name)

    def update(self, source=None):
        if source is None:
            pass

        elif isinstance(source, dict):
            self._data.update(source)

        elif isinstance(source, CustomDict):
            self._data.update(source._data)

    def keys(self):
        return self._data.keys()

    def dumps(self):
        return dumps(self.__data__, datetime_mode=DM_ISO8601 | DM_NAIVE_IS_UTC)

