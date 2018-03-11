import asyncio
import os

import tornado.options
import tornado.web

from .log import A, I
from .options import options

__all__ = ['Application']


class Application(tornado.web.Application):
    '''
    overlay default Application, add more helper settings or options
    '''

    def __init__(self, *args, **kwargs):
        self.load_config()

        super().__init__(*args, **kwargs)

    def load_config(self):
        tornado.options.parse_command_line()

        if os.path.isfile(options.config):
            path = options.config
            try:
                tornado.options.parse_config_file(path)
            except Exception as e:
                I('load config error:%s', e)
            else:
                I('load config from %s', path)

    def start(self):
        I('service on %s:%d version %s', options.address, options.port, options.version)
        self.listen(options.port, options.address, xheaders=True)

        asyncio.get_event_loop().run_forever()

    def stop(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

    def log_request(self, handler):
        '''overwrite parent log handler''',

        request_time = 1000.0 * handler.request.request_time()
        A("%d %s %.2fms", handler.get_status(), handler._request_summary(), request_time)
