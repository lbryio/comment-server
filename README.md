# LBRY Comment Server

[![Maintainability](https://api.codeclimate.com/v1/badges/22f420b8b5f2373fd885/maintainability)](https://codeclimate.com/github/lbryio/comment-server/maintainability)  

This is the code for the LBRY Comment Server. 
Fork it, run it, set it on fire. Up to you.


## Before Installing

Comment Deletion requires having the [`lbry-sdk`](https://github.com/lbryio/lbry-sdk) 
in order to validate & properly delete comments. 


 
 
## Installation

#### Installing the server:
```bash

$ git clone https://github.com/osilkin98/comment-server
$ cd comment-server

# create a virtual environment
$ virtualenv --python=python3 venv

# Enter the virtual environment
$ source venv/bin/activate

# install the Server as a Executable Target
(venv) $ python setup.py develop
```

### Installing the systemd Service Monitor

As a super-user, copy the .service and .target files to the systemd directory: 
```bash 
$ sudo comment-server/config/comment-server* /etc/systemd/system
```
Then `$ sudo systemctl daemon-reload` to refresh the systemd service files.



## Usage

### Running the Server
To start the server, simply run:
```bash
$ sudo systemctl start comment-server.target
```

(Optional) Enable the server to run on booting:
```bash
$ sudo systemctl enable --now comment-server.target
```


### Testing

To Test the database, simply run: 
```bash
# To run the whole thing :
(venv) $ python -m unittest tests.database

# To run a specific TestName under a specified TestClass:
(venv) $ python -m unittest tests.database.TestClass.TestName` 
``` 

There are basic tests to run against the server, though they require 
that there is a server instance running, though the database
 chosen may have to be edited in `config/conf.json`.

Additionally there are HTTP requests that can be send with whatever 
software you choose to test the integrity of the comment server.

## Schema


![schema](schema.png)


## Contributing
Contributions are welcome, verbosity is encouraged. Please be considerate
in your posts, and make sure that you give as much context to the issue 
as possible, so that helping you is a slam dunk for us.

### Issues
If you spotted an issue from the SDK side, please replicate it using 
`curl` and one of the HTTP request templates in `tests/http_requests`. 

Then, just include that along with the rest of your information.

### Pull Requests
Make sure the code works and has been tested beforehand. 
Although we love helping out, our job is to review your code,
not test it - that's what your computer is for. 


Try to document the changes you made in a human language, 
preferably English. (but we're always up for a challenge...)
Use the level of verbosity you feel is correct, and when in doubt, 
just [KISS](https://people.apache.org/~fhanik/kiss.html).

### General 

For more details, please refer to [lbry.tech/contribute](https://lbry.tech/contribute).


## License
This project is licensed by AGPLv3. 
See [LICENSE](LICENSE.nd) for the full license.

## Security 
We take security seriously. 
Please contact [security@lbry.io](security@lbry.io) regarding any conerns you might have, 
issues you might encounter, or general outlooks on life. Our PGP key can 
be found [here](https://keybase.io/lbry/key.asc), should you need it.

## Contact Us
The primary contact for this project is 
[@osilkin98](https://github.com/osilkin98), and can be reached 
at (o.silkin98@gmail.com). 


