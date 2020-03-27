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
        'mysql-connector-python',
        'pyyaml',
        'Faker>=1.0.7',
        'asyncio>=3.4.3',
        'aiohttp==3.5.4',
        'aiojobs==0.2.2',
        'ecdsa>=0.13.3',
        'cryptography==2.5',
        'aiosqlite==0.10.0',
        'PyNaCl>=1.3.0',
        'requests',
        'cython',
        'peewee'
    ]
)
