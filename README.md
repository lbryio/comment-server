# LBRY Comment Server


## Installation

Installing the server:
```bash

$ git clone https://github.com/osilkin98/comment-server
$ cd comment-server

# create a virtual environment
$ virtualenv --python=python3 venv

# Enter the virtual environment
$ source venv/bin/activate

# install the library dependencies
(venv) $ pip install -r requirements.txt
```

## Usage
To start the server, simply run:
```bash
# to enter server's venv
$ source venv/bin/activate

# to actually run server
(venv) $ python -m main &  
```

## Schema
![schema](schema.png)


## About
A lot of the design is more or less the same with the original,
except this version focuses less on performance and more on scalability.

Rewritten with python because it's easier to adjust
and maintain. Instead of doing any multithreading,
this implementation just delegates a single
database connection for write operations.

The server was originally implemented with `aiohttp`
and uses `aiojobs` for scheduling write operations.
As pointed out by several people, Python is a dinosaur
in comparison to SQLite's execution speed,
so there is no sensibility in multi-threading from the
perspective of the server code itself.
