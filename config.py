import os
from configparser import ConfigParser
from datetime import datetime, timezone
from typing import Optional

CONFIG_FILE = "./main.ini"

config: Optional[ConfigParser] = None


def load_config() -> ConfigParser:
    global config

    if config is None:
        config = ConfigParser()

        config["default"] = {
            # service start at
            "ts_start": datetime.now(timezone.utc).isoformat(),
            # debug flag
            "debug": False,
            "autoreload": False,
        }

        config["http"] = {
            # http listen on
            "host": "127.0.0.1",
            "port": 8080,
        }

        config["database"] = {}

        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as fobj:
                try:
                    config.read_file(fobj)
                except Exception as e:
                    print(f"read main.ini error:{e}")
    return config
