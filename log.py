'''
helper module
'''

import logging
import logging.config
from tornado.log import LogFormatter

__all__ = ['I', 'E', 'W', 'D', 'A']

# default formatter
formatter_default = LogFormatter('%(color)s[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d %(thread)s:%(funcName)s]%(end_color)s %(message)s')

log_root = logging.getLogger()
log_root.addHandler(logging.NullHandler())

# setup main logger
log_main_handler = logging.FileHandler('./log/main.log', encoding='utf-8', delay=True)
log_main_handler.setFormatter(formatter_default)
log_main = logging.getLogger('iscys.main')
log_main.setLevel(logging.INFO)
log_main.addHandler(log_main_handler)

# setup debug logger
log_debug = logging.getLogger('iscys.debug')
log_debug_handler = logging.FileHandler('./log/debug.log', encoding='utf-8', delay=True)
log_debug_handler.setFormatter(formatter_default)
log_debug_handler.setLevel(logging.DEBUG)
log_debug.setLevel(logging.DEBUG)
log_debug.addHandler(log_debug_handler)


# setup access logger
log_access = logging.getLogger('iscys.access')
log_access_handler = logging.FileHandler('./log/access.log')
log_access_handler.setFormatter(formatter_default)
log_access.addHandler(log_access_handler)


def I(msg, *args, **kwargs):  # noqa
    log_main.info(msg, *args, **kwargs)


def E(msg, *args, **kwargs):
    log_main.error(msg, *args, **kwargs)


def W(msg, *args, **kwargs):
    log_main.warning(msg, *args, **kwargs)


def D(msg, *args, **kwargs):
    log_debug.debug(msg, *args, **kwargs)


def A(msg, *args, **kwargs):
    log_access.info(msg, *args, **kwargs)


# manual debug handlers
# handler_stream = logging.StreamHandler()
# handler_stream.setLevel(logging.DEBUG)
# handler_stream.setFormatter(formatter_default)
# log_main.addHandler(handler_stream)
# log_debug.addHandler(handler_stream)
# log_root.addHandler(handler_stream)
# print("[debug]add stream handler to main and debug logger")
