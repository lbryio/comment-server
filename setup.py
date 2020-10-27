import os
from setuptools import setup, find_packages

ROOT = os.path.dirname(__name__)

setup(
    name='CommentServer',
    version='0.0.2',
    packages=find_packages(exclude=('tests',)),
    entry_points={
        'console_scripts': 'commentserv=src.main:main'
    },
    zip_safe=False,
    data_files=[('config', ['config/conf.json',])],
    include_package_data=True,
    install_requires=[
        'pymysql',
        'pyyaml',
        'Faker>=1.0.7',
        'asyncio',
        'aiohttp',
        'aiojobs',
        'ecdsa>=0.13.3',
        'cryptography==3.2',
        'PyNaCl>=1.3.0',
        'requests',
        'cython',
        'peewee'
    ]
)
