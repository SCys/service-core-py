import os
from configparser import ConfigParser
from datetime import datetime, timezone
import aiofile

CONFIG_FILE = "main.ini"

config = ConfigParser(
    {
        "default": {
            "ts_start": datetime.now(timezone.utc).isoformat(),
            "debug": False,
            "autoreload": False,
        },
        "http": {
            "host": "127.0.0.1",
            "port": 8080,
        },
        "database": {},
    }
)


async def load() -> ConfigParser:
    global config

    if not os.path.isfile(CONFIG_FILE):
        return config

    async with aiofile.async_open(CONFIG_FILE, "r") as f:
        try:
            await config.read_file(f)
        except Exception as e:
            print(f"read main.ini error:{e}")

    return config


def reload() -> ConfigParser:
    global config

    config.clear()

    return load()
