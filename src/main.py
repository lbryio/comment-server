import argparse
import json
import yaml
import logging
import logging.config
import os
import sys

from src.server.app import run_app
from src.definitions import LOGGING_DIR, CONFIG_FILE, DATABASE_DIR


def setup_logging_from_config(conf: dict):
    # set the logging directory here from the settings file
    if not os.path.exists(LOGGING_DIR):
        os.mkdir(LOGGING_DIR)

    _config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": conf['logging']['format'],
                "datefmt": conf['logging']['datefmt']
            },
            "aiohttp": {
                "format": conf['logging']['aiohttp_format'],
                "datefmt": conf['logging']['datefmt']
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
                "filename": os.path.join(LOGGING_DIR, 'debug.log'),
                "maxBytes": 10485760,
                "backupCount": 5
            },
            "error": {
                "level": "ERROR",
                "formatter": "standard",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOGGING_DIR, 'error.log'),
                "maxBytes": 10485760,
                "backupCount": 5
            },
            "server": {
                "level": "NOTSET",
                "formatter": "aiohttp",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOGGING_DIR, 'server.log'),
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


def get_config(filepath):
    with open(filepath, 'r') as cfile:
        config = yaml.load(cfile, Loader=yaml.FullLoader)
    return config


def setup_db_from_config(config: dict):
    if 'sqlite' in config['database']:
        if not os.path.exists(DATABASE_DIR):
            os.mkdir(DATABASE_DIR)

        config['db_path'] = os.path.join(
            DATABASE_DIR, config['database']['sqlite']
        )


def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser(description='LBRY Comment Server')
    parser.add_argument('--port', type=int)
    parser.add_argument('--config', type=str)
    args = parser.parse_args(argv)

    config = get_config(CONFIG_FILE) if not args.config else args.config
    setup_logging_from_config(config)
    setup_db_from_config(config)

    if args.port:
        config['port'] = args.port

    run_app(config)


if __name__ == '__main__':
    sys.exit(main())
