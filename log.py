from loguru import logger

for name, config in {
    "debug": ["5 mb", "7 days", lambda r: "is_debug" in r["extra"]],
    "info": ["10 mb", "6 months", lambda r: "is_info" in r["extra"]],
    "warning": ["10 mb", "3 months", lambda r: "is_warning" in r["extra"]],
    "error": ["20 mb", "6 months", lambda r: "is_error" in r["extra"]],
    "access": ["50 mb", "12 months", lambda r: "is_access" in r["extra"]],
}.items():
    logger.add(f"log/{name}.log", rotation=config[0], retention=config[1], compression="gz", buffering=2048, filter=config[2])

logger_debug = logger.bind(is_debug=True)
logger_info = logger.bind(is_info=True)
logger_warning = logger.bind(is_warning=True)
logger_error = logger.bind(is_error=True)

logger_access = logger.bind(is_access=True)


debug = logger_debug.debug
info = logger_info.info
warning = logger_warning.warning
error = logger_error.error

# error display exception track strace
exception = logger_error.exception


def access(request, exception=None):
    remote = request.remote
    url = request.url

    if exception is None:
        logger_access.info(f"{remote} - {url}")
        return

    logger_access.info(f"{remote} - {url} - {exception.code}:{exception.error}")
