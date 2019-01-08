from rapidjson import dumps, DM_ISO8601, DM_NAIVE_IS_UTC


__all__ = ["CustomDict"]


class CustomDict(object):

    _custom_data: dict

    def __init__(self, raw=None):
        data = {}

        if isinstance(raw, dict):
            data.update(raw)

        elif isinstance(raw, CustomDict):
            data.update(raw._custom_data)

        object.__setattr__(self, "_custom_data", data)

    def __str__(self):
        return "<CustomDict %d %s>" % (id(self), self._custom_data)

    def __eq__(self, other):
        if isinstance(other, CustomDict):
            return self._custom_data == other._custom_data
        elif isinstance(other, dict):
            return self._custom_data == other

        return False

    def __bool__(self):
        return self._custom_data.__bool__()

    def __contains__(self, key):
        return key in self._custom_data

    def __hasattr__(self, key):
        return hasattr(self._custom_data, key)

    # Getter by name
    def __getitem__(self, name):
        value = self._custom_data.get(name)
        if isinstance(value, dict):
            return CustomDict(value)

        return value

    def __getattr__(self, name):
        data = object.__getattribute__(self, "_custom_data")
        if name in data:
            return data.get(name)

        if hasattr(super(), name):
            return getattr(super(), name)

        return None

    # Setter by name with value
    def __setitem__(self, name, value):
        if isinstance(value, CustomDict):
            self._custom_data[name] = value._custom_data
        else:
            self._custom_data[name] = value

    def __setattr__(self, name, value):
        self.__setitem__(name, value)

    def __delitem__(self, name):
        if name in self._custom_data:
            del self._custom_data

    def __delattr__(self, name):
        self.__delattr__(name)

    def update(self, source=None):
        if source is None:
            pass

        elif isinstance(source, dict):
            self._custom_data.update(source)

        elif isinstance(source, CustomDict):
            self._custom_data.update(source._custom_data)

    def keys(self):
        return self._custom_data.keys()

    def dumps(self):
        return dumps(self._custom_data, datetime_mode=DM_ISO8601 | DM_NAIVE_IS_UTC)
