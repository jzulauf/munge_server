#! /usr/bin/env python3


from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import io
import sys
from io import TextIOWrapper


def process_url(url):
    url= url.rstrip()
    munged = []
    digits = set(list("0123456789"))
    with urllib.request.urlopen(url) as f:
        last = ""
        text = TextIOWrapper(f, encoding="utf-8")
        for c in iter(lambda: text.read(1), '') :
            if c in digits or c == last:
                continue
            last = c
            munged.append(c)
      
    return "".join(munged)

debug_level = 2
class PostHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        global debug_level
        if debug_level:
            print("bgn:do_POST:", self.requestline)
            sys.stdout.flush()

        in_length = int(self.headers.get("Content-Length"))
        in_data = self.rfile.read(in_length)
        in_str  = in_data.decode('utf-8')
        if debug_level > 1:
            for u in in_str.split(","):
                print("RECD:", u)
                sys.stdout.flush()


        # Compute the response... with a chunk response capable
        # server this should be done chunkwise, but http.server isn't, apparently
        # Would also be a place to parallelize on chunks (or urls, but I'm not
        # clear on the thread safety of pool dispatch from within threads, and this
        # isn't the time to test it)
        url_list = [ u.strip().rstrip() for u in in_str.split(",")]
        if url_list:
            response = [ process_url(u) for u in url_list ]
            
            length = len(response[0])
            for i in range(1, len(response)):
                length += len(response[i])
                if response[i] and response[i-1].endswith(response[i][0]) :
                    response[i-1] = response[i-1][:-1]
                    length -= 1

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        self.wfile.write("".join(response).encode("utf-8"))

        if debug_level > 1:
            print("end:do_POST:", self.requestline)
            sys.stdout.flush()

class ThreadedServer(ThreadingMixIn, HTTPServer):
    """Using the SocketServer mixin to make the HTTPServer multithreaded"""
    pass




def main():
    # Not sure if the pool object is thread safe... disable for now
    # Needs to be parameterized, especially vs. ThreadedServer below
    #CreateGlobalPool(2) # Allow each concurrent handler up to two workers.
    server =  ThreadedServer(('localhost', 8675), PostHandler)
    server.serve_forever()

main()
