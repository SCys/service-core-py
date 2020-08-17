from loguru import logger

__all__ = []
names = globals()

for name, name_long, limit_size, limit_retention in [
    ["app", "application", "10 MB", "3 months"],
    ["info", "info", "20 MB", "12 months"],
    ["access", "access", "50 MB", "12 months"],
    ["debug", "debug", "50 MB", "1 months"],
]:
    logger.add(
        f"log/{name_long}.log",
        rotation=limit_size,
        retention=limit_retention,
        compression="gz",
        delay=True,
        buffering=1024,
        filter=lambda r: f"is_{name_long}" in r["extra"],
    )
    names[f"logger_{name}"] = logger.bind(**{f"is_{name_long}": True})
    __all__.append(f"logger_{name}")
    print(f"setup logger_{name} as {name_long}")

