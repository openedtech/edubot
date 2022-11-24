"""
Read the config into the global scope when the library is imported.
"""
from configparser import ConfigParser
from os import environ
from sys import stderr


def _read_cfg() -> ConfigParser:
    config_fp = ""
    try:
        config_fp = environ["EDUBOT_CONFIG"]
    except KeyError:
        print("EDUBOT_CONFIG environment variable not set.", stderr)
        exit(1)

    config = ConfigParser()

    config.read(config_fp)
    return config


CONFIG = _read_cfg()

# ConfigParser will automatically throw user-friendly errors, no need to check for KeyError
OPENAI_KEY: str = CONFIG["edubot"]["openai_key"]
DATABASE: str = CONFIG["edubot"]["database"]
