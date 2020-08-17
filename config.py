from configparser import ConfigParser
from datetime import datetime, timezone
from typing import Optional

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

        try:
            config.read_file("./main.ini")
        except Exception as e:
            print(f"read main.ini error:{e}")

    return config
