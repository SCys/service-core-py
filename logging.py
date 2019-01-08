import logging

app_logger = logging.getLogger('laplus-main')
app_logger.setLevel(logging.INFO)
app_logger.addHandler(logging.FileHandler('log/main.log'))

access_logger = logging.getLogger('laplus-access')
access_logger.setLevel(logging.INFO)
access_logger.addHandler(logging.FileHandler('log/access.log'))

debug_logger = logging.getLogger('laplus-debug')
debug_logger.setLevel(logging.DEBUG)
debug_logger.addHandler(logging.FileHandler('log/debug.log'))

console = logging.StreamHandler()
console.setLevel(logging.INFO)

app_logger.addHandler(console)
access_logger.addHandler(console)
