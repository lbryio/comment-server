import os

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SRC_DIR)
CONFIG_FILE = os.path.join(ROOT_DIR, 'config', 'conf.yml')
LOGGING_DIR = os.path.join(ROOT_DIR, 'logs')
DATABASE_DIR = os.path.join(ROOT_DIR, 'database')
