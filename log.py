'''
helper module
'''

import logging
from tornado.log import LogFormatter

__all__ = ['I', 'E', 'W', 'D', 'A']

# setup main logger
log_main = logging.getLogger('iscys.main')
log_main_handler = logging.FileHandler('./log/main.log')
log_main_handler.setFormatter(LogFormatter('%(color)s[%(levelname)1.1s %(asctime)s '
                                           '%(module)s:%(lineno)d %(thread)s:%(funcName)s]'
                                           '%(end_color)s %(message)s'))
log_main.addHandler(log_main_handler)
log_main.setLevel(logging.INFO)
log_main.addHandler(logging.StreamHandler())

# setup debug logger
log_debug = logging.getLogger('iscys.debug')
log_debug_handler = logging.FileHandler('./log/debug.log')
log_debug_handler.setFormatter(LogFormatter('%(color)s[%(levelname)1.1s %(asctime)s '
                                            '%(module)s:%(lineno)d %(thread)s:%(funcName)s]'
                                            '%(end_color)s %(message)s'))
log_debug_handler.setLevel(logging.DEBUG)
log_debug.addHandler(log_debug_handler)
log_debug.setLevel(logging.DEBUG)

# setup access logger
log_access = logging.getLogger('iscys.access')
log_access_handler = logging.FileHandler('./log/access.log')
log_access_handler.setFormatter(LogFormatter('%(color)s[%(levelname)1.1s %(asctime)s '
                                             '%(module)s:%(lineno)d %(thread)s:%(funcName)s]'
                                             '%(end_color)s %(message)s'))
log_access.addHandler(log_access_handler)


def I(msg, *args, **kwargs):
    log_main.info(msg, *args, **kwargs)


def E(msg, *args, **kwargs):
    log_main.error(msg, *args, **kwargs)


def W(msg, *args, **kwargs):
    log_main.debug(msg, *args, **kwargs)


def D(msg, *args, **kwargs):
    log_debug.debug(msg, *args, **kwargs)


def A(msg, *args, **kwargs):
    log_access.info(msg, *args, **kwargs)
