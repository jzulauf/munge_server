#! /usr/bin/env python3


from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import io
import sys

class PostHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        print("bgn:do_POST:", self.requestline)
        sys.stdout.flush()

        in_length = int(self.headers.get("Content-Length"))
        in_data = self.rfile.read(in_length)
        in_str  = in_data.decode('utf-8')
        for u in in_str.split(","):
            print("RECD:", u)
            sys.stdout.flush()
        self.send_response(200)
        response = "quack"
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode("utf-8"))

        print("end:do_POST:", self.requestline)
        sys.stdout.flush()

class ThreadedServer(ThreadingMixIn, HTTPServer):
    """Using the SocketServer mixin to make the HTTPServer multithreaded"""
    pass



def process_url(url):
    url= url.rstrip()
    count = -1
    with urllib.request.urlopen(url) as f:
        count = 0
        for l in f:
            count += 1
    return "{}: {}".format(url, count)
        

def main():
    server =  ThreadedServer(('localhost', 8675), PostHandler)
    server.serve_forever()

main()
