import json
import pathlib

root_dir = pathlib.Path(__file__).parent.parent
config_path = root_dir / 'config' / 'conf.json'


def get_config(filepath):
    with open(filepath, 'r') as cfile:
        conf = json.load(cfile)
    for key, path in conf['PATH'].items():
        conf['PATH'][key] = str(root_dir / path)
    return conf


config = get_config(config_path)
# print(json.dumps(config, indent=4))
