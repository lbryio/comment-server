import logging.config
import logging
import os
from src.settings import config

from src.app import run_app


def config_logging_from_settings(conf):
    _config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": conf['LOGGING']['FORMAT'],
                "datefmt": conf['LOGGING']['DATEFMT']
            },
            "aiohttp": {
                "format":  conf['LOGGING']['AIOHTTP_FORMAT'],
                "datefmt": conf['LOGGING']['DATEFMT']
            }
        },
        "handlers": {
            "console": {
                "level": "DEBUG",
                "formatter": "standard",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout"
            },
            "debug": {
                "level": "DEBUG",
                "formatter": "standard",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": conf['PATH']['DEBUG_LOG'],
                "maxBytes": 10485760,
                "backupCount": 5
            },
            "error": {
                "level": "ERROR",
                "formatter": "standard",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": conf['PATH']['ERROR_LOG'],
                "maxBytes": 10485760,
                "backupCount": 5
            },
            "server": {
                "level": "NOTSET",
                "formatter": "aiohttp",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": conf['PATH']['SERVER_LOG'],
                "maxBytes": 10485760,
                "backupCount": 5
            }
        },
        "loggers": {
            "": {
                "handlers": ["console", "debug", "error"],
                "level": "DEBUG",
                "propogate": True
            },
            "aiohttp.access": {
                "handlers": ["server"],
                "level": "INFO",
                "propogate": False
            }
        }

    }
    logging.config.dictConfig(_config)


if __name__ == '__main__':
    config_logging_from_settings(config)
    logger = logging.getLogger(__name__)
    run_app(config)