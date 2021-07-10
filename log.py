from loguru import logger


logger.add(
    "log/application.log",
    rotation="10 MB",
    retention="3 months",
    compression="gz",
    delay=True,
    buffering=1024,
    filter=lambda r: "is_application" in r["extra"],
)
logger_app = logger.bind(is_application=True)


logger.add(
    "log/info.log",
    rotation="20 MB",
    retention="12 months",
    compression="gz",
    delay=True,
    buffering=1024,
    filter=lambda r: "is_info" in r["extra"],
)
logger_info = logger.bind(is_info=True)


logger.add(
    "log/access.log",
    rotation="50 MB",
    retention="12 months",
    compression="gz",
    delay=True,
    buffering=1024,
    filter=lambda r: "is_access" in r["extra"],
)
logger_access = logger.bind(is_access=True)


logger.add(
    "log/debug.log",
    rotation="50 MB",
    retention="1 months",
    compression="gz",
    delay=True,
    buffering=1024,
    filter=lambda r: "is_debug" in r["extra"],
)
logger_debug = logger.bind(is_debug=True)
