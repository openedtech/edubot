"""
Read the config into the global scope when the library is imported.
"""
from configparser import ConfigParser
from os import environ, path


def _read_cfg() -> ConfigParser:
    try:
        config_fp = environ["EDUBOT_CONFIG"]
    except KeyError:
        raise EnvironmentError("EDUBOT_CONFIG environment variable not set.")

    config = ConfigParser()

    if not config.read(config_fp):
        if path.exists(config_fp):
            raise PermissionError(f"Cannot read {config_fp}.")
        raise FileNotFoundError(f"File {config_fp} doesn't exist.")
    return config


CONFIG = _read_cfg()

OPENAI_KEY: str | None = CONFIG.get("edubot", "openai_key", fallback=None)
DREAMSTUDIO_KEY: str | None = CONFIG.get("edubot", "dreamstudio_key", fallback=None)
DATABASE: str = CONFIG.get("edubot", "database")
