'''
helper module
'''

from distutils.version import LooseVersion

import tornado.web
from xid import Xid

import asyncpg
from rapidjson import DM_ISO8601, DM_NAIVE_IS_UTC, dumps, loads

from .custom_dict import CustomDict
from .log import D, E, I, W
from .options import options

__all__ = ['JSONError', 'RequestHandler']


class JSONError(object):
    """
    custom error with json format
    """

    code = 204
    message = None

    def __init__(self, code, msg):
        self.code = code
        self.message = msg


class RequestHandler(tornado.web.RequestHandler):
    '''
    overlay default RequestHandler
    '''

    auth = None
    params = None

    _db = None

    id = None

    def initialize(self):
        self.id = Xid().string()
        self._db = None
        self.auth = CustomDict({})
        self.params = CustomDict({})

    def I(self, msg, *args, **kwargs):
        I(f'[{self.id}]{msg}', *args, **kwargs)

    def E(self, msg, *args, **kwargs):
        E(f'[{self.id}]{msg}', *args, **kwargs)

    def W(self, msg, *args, **kwargs):
        W(f'[{self.id}]{msg}', *args, **kwargs)

    def D(self, msg, *args, **kwargs):
        D(f'[{self.id}]{msg}', *args, **kwargs)

    async def prepare(self):
        """
        support request body is json text:

        {
            "version": "api version string, default 0.0.0",
            "auth": { ... auth object ... },
            "params": {
                ... request params ...
            }
        }
        """
        self.data = CustomDict()
        self.params = CustomDict()
        self.auth = CustomDict()
        self.version = LooseVersion('0.0.0')

        # dump request json text body to json object
        if self.request.method in ('POST', 'PUT'):
            try:
                data = loads(self.request.body, datetime_mode=DM_ISO8601)
            except Exception as e:
                self.E('convert body to json failed:%s', e)
            else:
                self.data.update(data)
                self.auth.update(data.get('auth'))
                self.params.update(data.get('params'))
                self.version = LooseVersion(data.get('version', '0.0.0'))

    def write(self, chunk):

        # output dict as unicode and setup header
        if isinstance(chunk, dict):
            self.set_header('Content-Type', 'application/json')
            chunk = dumps(chunk, datetime_mode=DM_ISO8601 | DM_NAIVE_IS_UTC)

        elif isinstance(chunk, CustomDict):
            self.set_header('Content-Type', 'application/json')
            chunk = chunk.dumps()

        elif isinstance(chunk, JSONError):
            self.set_header('Content-Type', 'application/json')
            self.set_status(200)
            self.write(dumps({
                'error': {
                    'code': chunk.code,
                    'message': chunk.message,
                    'id': self.id,
                }
            }))
            return

        super().write(chunk)

    def check_params(self):
        if not hasattr(self, 'params_required'):
            return None

        params = CustomDict({})
        for key, trunk in self.params_required.items():
            if key not in self.params:
                self.E(f'param {key} is missed')
                return None

            value = self.params[key]
            if not isinstance(value, trunk[0]):
                self.E(f'param {key} is missed')
                return None

            if trunk[0] == int:
                if len(trunk) > 1 and value < trunk[1]:
                    self.E(f'param {key} value {value} small than {trunk[1]}')
                    return None

                if len(trunk) > 2 and value > trunk[1]:
                    self.E(f'param {key} value {value} large than {trunk[2]}')
                    return None

            elif trunk[0] == str:
                if len(trunk) > 1 and len(value) < trunk[1]:
                    self.E(f'param {key} value {value} length small than {trunk[1]}')
                    return None

                if len(trunk) > 2 and len(value) > trunk[1]:
                    self.E(f'param {key} value {value} length large than {trunk[2]}')
                    return None

            params[key] = value

        return params

    async def db(self):
        if self._db is None:
            self._db = await asyncpg.create_pool(
                options.db,
                max_size=60,
                command_timeout=60,)

        return self._db
