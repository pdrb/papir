papir
=====

Papir is an acronym for "Python API Requests".

The main purpose is to make custom http requests to json APIs, prettify and
colorize the full response (headers + json content).

Json files are used to post, put, patch or delete and to customize the http
headers.

Basic http authentication and gzip compression are supported.

Simple example::

    $ papir httpbin.org/get

.. image:: https://raw.githubusercontent.com/pdrb/papir/master/papir.png


Notes
-----

- Works on Python 3.3+
- Uses only Python standard library for maximum compatibility
- Small and simple source code that can be read in a few minutes


Install
-------

Install using pip::

    pip install papir

or

Download and set executable permission on the script file::

    chmod +x papir.py

or

Download and run using the python interpreter::

    python3 papir.py


Usage
-----

::

    Usage: papir url [options] [method]

    make http requests to json apis

    Options:
    --version        show program's version number and exit
    -d DATA_FILE     json file to post, put, patch or delete
    -h HEADERS_FILE  json file containing additional headers
    -t TIMEOUT       timeout in seconds to wait for response (default: 10)
    -a AUTH          basic http authentication in the format username:password
    -f, --follow     follow redirects (default: disabled)
    -v, --verbose    show request headers (default: disabled)


Examples
--------

Assuming the file "data.json" exists containing::

    {
        "name": "Bob",
        "age": 30
    }

Make a post request using that data::

    $ papir example.org -d data.json

To use a different http method just inform it::

    $ papir example.org -d data.json put

To customize the request headers, create a json file like::

    {
        "Auth-User": "user",
        "Auth-Token": "1234",
        "User-Agent": "myagent"
    }

And add it to the request::

    $ papir example.org -h headers.json

Obviously, you can mix it with all kinds of http methods::

    $ papir example.org -h headers.json -d data.json patch

Simple basic auth::

    $ papir example.org -a user:pass
