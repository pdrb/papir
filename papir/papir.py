#!/usr/bin/env python
# -*- coding: utf-8 -*-

# papir 0.3.0
# author: Pedro Buteri Gonring
# email: pedro@bigode.net
# date: 2020-12-04

import sys
import json
import optparse
import urllib.request as urllib
import urllib.parse as url_parse
import ssl
import base64
import socket
import gzip
import re


_version = "0.3.0"


# Terminal colors ANSI escape sequences
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    END = "\033[0m"


# Class used to disable urllib redirects
class NoRedirect(urllib.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        pass


# Parse and validate arguments
def get_parsed_args():
    usage = "usage: %prog url [options] [method]"
    # Create the parser
    parser = optparse.OptionParser(
        description="make http requests to json apis",
        usage=usage,
        version=_version,
        add_help_option=False,
    )
    parser.add_option(
        "-d", dest="data_file", help="json file to post, put, patch or delete"
    )
    parser.add_option(
        "-h", dest="headers_file", help="json file containing additional headers"
    )
    parser.add_option(
        "-j", dest="json_data", help="json string to post, put, patch or delete"
    )
    parser.add_option(
        "-e", dest="json_headers", help="json string containing additional headers"
    )
    parser.add_option(
        "-t",
        dest="timeout",
        default=10,
        type=int,
        help="timeout in seconds to wait for response (default: %default)",
    )
    parser.add_option(
        "-a",
        dest="auth",
        help="basic http authentication in the format username:password",
    )
    parser.add_option(
        "-f",
        "--follow",
        action="store_true",
        default=False,
        help="follow redirects (default: disabled)",
    )
    parser.add_option(
        "-i",
        "--insecure",
        action="store_true",
        default=False,
        help="allow insecure SSL connections (default: disabled)",
    )
    parser.add_option(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="show request headers (default: disabled)",
    )

    # Print help if no argument is given
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(2)

    # Parse the args
    (options, args) = parser.parse_args()

    # Some args validation
    if len(args) == 0:
        parser.error("url not provided")
    if len(args) > 2:
        parser.error("too many arguments")
    if options.timeout < 1:
        parser.error("timeout must be a positive number")
    if options.data_file is not None and options.json_data is not None:
        parser.error(
            "json data file and json data string provided, choose just one to " "use"
        )
    if options.headers_file is not None and options.json_headers is not None:
        parser.error(
            "json headers file and json headers string provided, choose just "
            "one to use"
        )
    return (options, args)


# Open and load a json file
def open_data_file(data_file):
    try:
        file_object = open(data_file)
    except Exception as ex:
        print("\n%s\n" % ex)
        sys.exit(1)
    try:
        data = json.load(file_object)
    except json.decoder.JSONDecodeError as ex:
        print("\nMalformed JSON file: %s\n" % ex)
        sys.exit(1)

    file_object.close()
    return data


# Open the json headers file and update the original headers
def open_headers_file(headers_file, headers):
    headers_data = open_data_file(headers_file)
    headers = update_headers(headers_data, headers)
    return headers


# Load json data from string
def load_json_data(json_string):
    try:
        data = json.loads(json_string)
    except json.decoder.JSONDecodeError as ex:
        print("\nMalformed JSON: %s\n" % ex)
        sys.exit(1)
    return data


# Load and update headers from json string
def load_json_headers(json_string, headers):
    headers_data = load_json_data(json_string)
    headers = update_headers(headers_data, headers)
    return headers


# Update headers
def update_headers(headers_data, headers):
    # Handle case insensitive keys, the original headers keys are lowercase
    for key, value in headers_data.items():
        headers[key.lower()] = value
    return headers


# Get response from req resource
def open_url(req, insecure):
    try:
        if insecure:
            ctx = ssl._create_unverified_context()
            resp = urllib.urlopen(req, context=ctx)
        else:
            resp = urllib.urlopen(req)
    except urllib.HTTPError as ex:
        return req, ex
    except urllib.URLError as ex:
        print("\nError connecting to %s: %s\n" % (req.full_url, ex.reason))
        sys.exit(1)
    except Exception as ex:
        print("\nError connecting to %s: %s\n" % (req.full_url, ex))
        sys.exit(1)
    return req, resp


# Handle get, head and options methods
def do_get_request(url, headers, method, insecure):
    req = urllib.Request(url, headers=headers, method=method)
    req, resp = open_url(req, insecure)
    return req, resp


# Handle post, patch, put and delete methods
def do_post_request(url, headers, data, method, insecure):
    # Add the appropriate header
    headers["content-type"] = "application/json"
    # Convert dict to json string and then convert it to bytes
    data = json.dumps(data).encode()
    req = urllib.Request(url, headers=headers, data=data, method=method)
    req, resp = open_url(req, insecure)
    return req, resp


# Colorize and print the req headers
def print_request_headers(req, color_method, color_headers):
    selector = req.selector if not req.selector == "" else "/"
    if sys.stdout.isatty():
        print(color_method + "%s %s" % (req.method, selector) + Colors.END)
    else:
        print("%s %s" % (req.method, selector))
    print_headers(req.header_items(), color_headers)
    print("\n")


# Colorize and print http status
def print_http_status(http_status, color):
    if sys.stdout.isatty():
        print(color + "HTTP %s %s" % (http_status[0], http_status[1]) + Colors.END)
    else:
        print("HTTP %s %s" % (http_status[0], http_status[1]))


# Colorize and print headers
def print_headers(headers, color):
    for item in headers:
        if sys.stdout.isatty():
            print((color + "%s" + Colors.END + ": %s") % (item[0], item[1]))
        else:
            print("%s: %s" % (item[0], item[1]))


# Read the response and decompress it if needed
def read_response(resp):
    raw_resp = resp.read()
    if resp.info().get("Content-Encoding") == "gzip":
        try:
            content = gzip.decompress(raw_resp)
        except:
            return raw_resp
        else:
            return content
    return raw_resp


# Parse, colorize and print json response
def print_json_response(json_text, color):
    print()
    # Quick and dirty parser to colorize the json
    for line in json_text.splitlines():
        # Regex split witch capture group '()' keeps the delimiter
        elem_list = re.split("(:)", line)
        if len(elem_list) == 1:
            print(line)
        else:
            if sys.stdout.isatty():
                key = color + elem_list[0] + Colors.END
            else:
                key = elem_list[0]
            # Create the value string from the list elements
            value = "".join(elem_list[1:])
            print(key + value)
    print()


# Print the response
def print_response(content):
    if len(content) == 0:
        print("\n")
        return
    try:
        resp_data = json.loads(content)
    # Print the response and exit if content is not valid json
    except json.decoder.JSONDecodeError:
        if sys.stdout.isatty():
            print(
                Colors.RED + "\n*** Decode Error! Response content is not "
                "valid JSON ***\n" + Colors.END
            )
        else:
            print("\n*** Decode Error! Response content is not valid JSON ***\n")
        print(content.decode())
        sys.exit(1)
    except UnicodeDecodeError:
        if sys.stdout.isatty():
            print(
                Colors.RED + "\n*** Decode Error! Response content is not a "
                "UTF-8 encoded text ***\n" + Colors.END
            )
        else:
            print(
                "\n*** Decode Error! Response content is not a UTF-8 encoded "
                "text ***\n"
            )
        print(content)
        sys.exit(1)
    else:
        # ensure_ascii=False is needed to correct print chars like 'é'
        json_text = json.dumps(resp_data, indent=4, sort_keys=True, ensure_ascii=False)
        print_json_response(json_text, Colors.YELLOW)


# Validate and return provided http method
def get_method(args):
    valid_methods = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
    method = ""
    if len(args) == 2:
        method = args[1].upper()
        if method not in valid_methods:
            print('\nError: Invalid HTTP method "%s"\n' % method)
            sys.exit(2)
        return method
    return method


# Validate and return provided credentials
def get_credentials(credentials):
    # It could also be done using re split with capture groups
    sep_index = credentials.find(":")
    if sep_index == -1:
        print('\nError: Could not parse credentials "%s"\n' % credentials)
        sys.exit(2)
    username = credentials[:sep_index]
    password = credentials[sep_index + 1 :]
    return username, password


# Main CLI
def cli():
    (options, args) = get_parsed_args()
    socket.setdefaulttimeout(options.timeout)
    method = get_method(args)
    post_data = None
    user_agent = "papir/" + _version
    headers = {
        "user-agent": user_agent,
        "accept-encoding": "gzip",
        "connection": "close",
    }
    if options.auth:
        username, password = get_credentials(options.auth)
        credentials = "%s:%s" % (username, password)
        base64_credentials = base64.b64encode(credentials.encode())
        headers["authorization"] = "Basic " + base64_credentials.decode()
    # Always disable redirection for HEAD method
    if not options.follow or method == "HEAD":
        noredir_opener = urllib.build_opener(NoRedirect())
        urllib.install_opener(noredir_opener)
    url = args[0]
    protocol = url.split(":")[0].lower()
    # Add protocol if not provided
    if protocol != "http" and protocol != "https":
        url = "http://" + url
    # Parse the url params and encode them
    parsed_url = list(url_parse.urlparse(url))
    parsed_url[4] = url_parse.parse_qsl(parsed_url[4])
    parsed_url[4] = url_parse.urlencode(parsed_url[4])
    url = url_parse.urlunparse(parsed_url)

    # Load headers file if needed
    if options.headers_file:
        headers = open_headers_file(options.headers_file, headers)

    # Load data file if needed
    if options.data_file:
        post_data = open_data_file(options.data_file)

    # Load json headers from string
    if options.json_headers:
        headers = load_json_headers(options.json_headers, headers)

    # Load json data from string
    if options.json_data:
        post_data = load_json_data(options.json_data)

    # Do the request based on cli args
    if not method and not post_data:
        req, resp = do_get_request(url, headers, "GET", options.insecure)
    elif not method and post_data:
        req, resp = do_post_request(url, headers, post_data, "POST", options.insecure)
    elif method == "GET" or method == "HEAD" or method == "OPTIONS":
        req, resp = do_get_request(url, headers, method, options.insecure)
    else:
        if not post_data:
            print('\nError: Missing JSON to "%s"\n' % method)
            sys.exit(1)
        req, resp = do_post_request(url, headers, post_data, method, options.insecure)

    # Print req headers if verbose enabled
    if options.verbose:
        print_request_headers(req, Colors.PURPLE, Colors.CYAN)

    # Get the response status, like: 200 OK
    http_status = (resp.status, resp.msg)
    # Print the response status and headers
    print_http_status(http_status, Colors.BLUE)
    print_headers(resp.getheaders(), Colors.GREEN)

    # Read and print the response content
    content = read_response(resp)
    print_response(content)


# Run cli function if invoked from shell
if __name__ == "__main__":
    cli()
