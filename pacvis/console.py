import json
import sys
import os

from time import gmtime, strftime

last_message = u""
head_message = u""

output_log, time_format = "/tmp/pacvis.log", "%Y-%m-%d %H:%M:%S"


def log_file():
    return open(output_log, "a")


def start_message(s):
    global last_message, head_message
    head_message = s
    last_message = s
    sys.stderr.write("\n" + s)
    sys.stderr.flush()


def append_message(s):
    global last_message, head_message, log_file

    sys.stderr.write("\r" + (" " * len(last_message)))
    last_message = head_message + s
    sys.stderr.write("\r" + last_message)
    sys.stderr.flush()
    with log_file() as log:
        log.write("%s: %s\n" % (strftime(time_format, gmtime()), last_message))
        log.flush()


def print_message(s):
    sys.stderr.write("\n")
    sys.stderr.write(s + "\n")
    sys.stderr.flush()
    with log_file() as log:
        log.write("%s: %s\n" % (strftime(time_format, gmtime()), s))
        log.flush()


def dumpjson(j, f=None):
    if f is None:
        print_message(json.dumps(j, sort_keys=True, indent=4))
    else:
        json.dump(j, f, sort_keys=True, indent=4)
        f.flush()


def dumplog(filename, data):
    if filename == "":
        return
    with open(filename, "w") as f:
        dumpjson(data, f)


def loadjson(path, default_value):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default_value
