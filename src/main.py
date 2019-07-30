import logging.config
import logging
import argparse
import sys

from src.settings import config
from src.server.app import run_app


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
                "format": conf['LOGGING']['AIOHTTP_FORMAT'],
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


def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser(description='LBRY Comment Server')
    parser.add_argument('--port', type=int)
    args = parser.parse_args(argv)
    config_logging_from_settings(config)
    if args.port:
        config['PORT'] = args.port
    config_logging_from_settings(config)
    run_app(config)


if __name__ == '__main__':
    sys.exit(main())
