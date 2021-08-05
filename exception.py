import orjson as json


class ErrorBasic(Exception):
    code = 500
    error = "unknown error"

    def __init__(self, code=None, msg=None):
        if code is not None:
            self.code = code
        if msg is not None:
            self.error = msg

        self.status_code = self.code
        self.reason = self.error
        self.log_message = None

    def dump(self):
        return {"code": self.code, "error": self.error}

    def dumps(self):
        return json.dumps(self.dump())


class ServerError(ErrorBasic):
    code = 500
    error = "server error"


class InvalidParams(ErrorBasic):
    code = 400
    error = "invalid params"


class ObjectNotFound(ErrorBasic):
    code = 404
    error = "object not found"


class Unauthorized(ErrorBasic):
    code = 401
    error = "unauthorized"


class KeyConflict(ErrorBasic):
    code = 409
    error = "key conflict"


class NoPermission(ErrorBasic):
    code = 403
    error = "no permission"


class RemoteServerError(ErrorBasic):
    code = 502
    error = "remote server error"
