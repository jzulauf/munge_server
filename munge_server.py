#! /usr/bin/env python3

from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import io
import sys
from io import TextIOWrapper
from functools import reduce
import time

base_time = 0
def millitime():
    return int(round(time.time() * 1000))

def init_timer():
    global base_time
    base_time = millitime()

def timestamp():
    global base_time
    return millitime() - base_time


def process_url(url):
    url= url.rstrip()
    munged = []
    digits = set(list("0123456789"))
    with urllib.request.urlopen(url) as f:
        last = ""
        #
        # The spec states the contents of the urls will be UTF-8.
        # Assume that all UTF-8 content has charset correctly set
        # and that unlabeled content is the default per RFC
        #
        charset = f.headers.get_content_charset("ISO-8859-1") # get the charset if passed
                                                              # or ISO-8859-1 (the official default)
        text = TextIOWrapper(f, encoding=charset)
        for c in iter(lambda: text.read(1), '') :
            if c in digits or c == last:
                continue
            last = c
            munged.append(c)
      
    return "".join(munged)

debug_level = 2

class MungedUrl:
    def __init__(self, url):
        try:
            self.source = url.strip().rstrip()
            self.result = process_url(self.source)
        except UnicodeDecodeError as e:
            self.success = False
            self.result = ""
            self.message = "FAILED:{}:{}, {}, at".format(self.source, e.encoding, e.reason, e.start)

        except Exception as e:
            self.success = False
            self.result = ""
            self.message = "FAILED:{}:{}".format(self.source, e.reason)
        else:
            self.success = True
            self.message = "PASSED:{}".format(self.source)

    def chomp(self):
        if self.success:
            self.result = self.result[:-1]
    def first(self):
        if self.success:
            return self.result[0]
        else:
            return ""
    def last(self):
        if self.success:
            return self.result[-1]
        else:
            return ""
    def tidy(self, next_result):
        last = self.last()
        if last and last == next_result.first():
            self.chomp()
    def status(self):
        return self.success
    def length(self):
        return len(self.response())
    def response(self):
        return self.result if self.status() else self.message

class PostHandler(BaseHTTPRequestHandler):

    def send_success_POST(self, munged):
        # Filter out empty results
        munged = [ m for m in munged if m.response() ]
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        # clean up any duplicates across result boundaries
        if ( len(munged) ):
            [ munged[i].tidy(munged[i+1]) for i in range(len(munged)-1) ]
            length = sum([m.length() for m in munged])
        else:
            length = 0;
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if ( len(munged) ):
            self.wfile.write("".join([m.response() for m in munged]).encode("utf-8"))

        return "OK"

    def send_failed_POST(self, munged):
        assert len(munged), "Reporting failure on empty request.  Empty is not a failure"
        self.send_response(400) # Not sure this is a perfect response, but the client can detect failur
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        response = "\n".join([m.response() for m in munged])
        length = len(response)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        self.wfile.write(response.encode("utf-8"))
        if debug_level:
            print("Failure Response:", response)

        return "FAIL"

    def do_POST(self):
        global debug_level
        if debug_level:
            stamp = timestamp()
            print("{}:BEGIN:do_POST:{}".format(stamp, self.requestline.strip().rstrip()))
            sys.stdout.flush()
        else:
            stamp = 0

        in_length = int(self.headers.get("Content-Length"))
        in_data = self.rfile.read(in_length)
        in_str  = in_data.decode('utf-8')
        if debug_level > 1:
            for u in in_str.split(","):
                print("{}:URL  :{}".format(stamp, u))
            sys.stdout.flush()


        # Compute the response... with a chunk response capable
        # server this should be done chunkwise, but http.server isn't, apparently
        # Would also be a place to parallelize on chunks (or urls), but I'm not
        # clear on the thread safety of pool dispatch from within threads, and this
        # isn't the time to test it
        url_list = in_str.split(",")
        if url_list:
            munged = [ MungedUrl(u) for u in url_list ]
            if all([m.status() for m in munged ]) :
                code = self.send_success_POST(munged)
            else:
                code = self.send_failed_POST(munged)
            
        else:
            send_failed_POST([])
            code = "NOOP"

        if debug_level > 1:
            print("{}:{: >5}:do_POST:".format(stamp, code))
            sys.stdout.flush()

class ThreadedServer(ThreadingMixIn, HTTPServer):
    """Using the SocketServer mixin to make the HTTPServer multithreaded"""
    pass




def main():
    # Not sure if the pool object is thread safe... disable for now
    # Needs to be parameterized, especially vs. ThreadedServer below
    #CreateGlobalPool(2) # Allow each concurrent handler up to two workers.
    server =  ThreadedServer(('localhost', 8675), PostHandler)
    init_timer()
    server.serve_forever()

main()
