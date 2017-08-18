import sys
import os

from time import gmtime, strftime

last_message = u""
head_message = u""

output_log, time_format = "/dev/null", "%Y-%m-%d %H:%M:%S"
last_line_ended = True


def log_file():
    return open(output_log, "a")


def start_message(s):
    global last_message, head_message, last_line_ended
    head_message = s
    last_message = s
    if sys.stderr.isatty():
        if not last_line_ended:
            sys.stderr.write("\n")
        sys.stderr.write(s)
        sys.stderr.flush()
    last_line_ended = False


def append_message(s):
    global last_message, head_message, log_file, last_line_ended

    if sys.stderr.isatty():
        sys.stderr.write("\r" + (" " * len(last_message)))
    last_message = head_message + s
    if sys.stderr.isatty():
        sys.stderr.write("\r" + last_message)
        sys.stderr.flush()
    with log_file() as log:
        log.write("%s: %s\n" % (strftime(time_format, gmtime()), last_message))
        log.flush()
        if not sys.stderr.isatty():
            sys.stderr.write("%s: %s\n" % (strftime(time_format, gmtime()), last_message))
    last_line_ended = False


def print_message(s):
    global last_line_ended
    if not last_line_ended:
        if sys.stderr.isatty():
            sys.stderr.write("\n")
    if sys.stderr.isatty():
        sys.stderr.write(s + "\n")
        sys.stderr.flush()
    with log_file() as log:
        log.write("%s: %s\n" % (strftime(time_format, gmtime()), s))
        log.flush()
        if not sys.stderr.isatty():
            sys.stderr.write("%s: %s\n" % (strftime(time_format, gmtime()), s))
    last_line_ended = True
