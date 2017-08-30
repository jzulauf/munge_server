#! /usr/bin/env python3

from multiprocessing import Pool
from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import io
import sys
from io import TextIOWrapper
from functools import reduce
import time

base_time = 0
pool = None
#  NOTE: This feature was added late, need a better place than a global for this state...
dedup_set = None

def millitime():
    return int(round(time.time() * 1000))

def init_timer():
    global base_time
    base_time = millitime()

def timestamp():
    global base_time
    return millitime() - base_time

def create_pool(num_threads) :
    """The pool allows for multiple post to be sent simulataneously"""
    global pool
    if num_threads > 0:
        pool = Pool(num_threads)
    else:
        pool = None

def process_url(url, dedup_set):
    munged = []
    mset = set()
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
        if dedup_set:
            for c in iter(lambda: text.read(1), '') :
                if not c in digits:
                    mset.add(c)
            munged = list(mset)
            #print("ZZZ DBG mset:", munged)
        else:
            for c in iter(lambda: text.read(1), '') :
                if c in digits or c == last:
                    continue
                last = c
                munged.append(c)
      
    return "".join(munged)

debug_level = 0

class MungedUrl:
    def __init__(self, url):
        global dedup_set
        self.success = False
        self.result = ""
        try:
            self.source = url.strip().rstrip()
            self.result = process_url(self.source, dedup_set)
        except UnicodeDecodeError as e:
            self.success = False
            self.result = ""
            self.message = "FAILED:{}:{}, {}, at".format(self.source, e.encoding, e.reason, e.start)

        except ValueError as e:
            self.message = "FAILED:{}:{}".format(self.source, "likely bad URL")
        except Exception as e:
            self.message = "FAILED:{}:{}".format(self.source, "unexpected exception")
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

def merge_set_results(munged):
    s = set()
    for m in munged:
        s = s | set(list(m.result))

    #print("ZZZ DBG", "".join(list(s)))
    return "".join(list(s))

class PostHandler(BaseHTTPRequestHandler):

    def send_success_POST(self, munged):
        global dedup_set
        # Filter out empty results
        munged = [ m for m in munged if m.response() ]
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        # clean up any duplicates across result boundaries
        charset = "utf-8"
        if ( len(munged) ):
            # tidy up inter URL deduplication
            if dedup_set:
                # The "set" style deduplication is much smaller than the mangle style
                response = merge_set_results(munged)
            else:
                [ munged[i].tidy(munged[i+1]) for i in range(len(munged)-1) ]
                # Doesn't seem to be anyway to avoid storing the whole encoded response
                # as we need it for length... and it can be big in this dedup style
                response = "".join([m.response() for m in munged])
        else:
            response = ""
        response = response.encode(charset)
        length = len(response)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if length:
            self.wfile.write(response)

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

        # Get the payload
        in_length = int(self.headers.get("Content-Length"))
        in_data = self.rfile.read(in_length)
        in_str  = in_data.decode('utf-8')
        if debug_level > 1:
            for u in in_str.split(","):
                print("{}:URL  :{}".format(stamp, u))
            sys.stdout.flush()


        # Compute the response... with a chunk response capable
        # server this should be done chunkwise, but http.server isn't, apparently
        url_list = in_str.split(",")
        if url_list:
            # munge the given urls, using the pool if present
            if pool:
                munged = pool.map( MungedUrl, url_list )
            else:
                munged = [ MungedUrl(u) for u in url_list ]

            # All of the url's must succeed for the post to succeed... not clear
            # how to report partial failure
            if all([m.status() for m in munged ]) :
                code = self.send_success_POST(munged)
            else:
                code = self.send_failed_POST(munged)
            
        else:
            # We can successfully do nothing
            send_success_POST([])
            code = "NOOP"

        if debug_level > 1:
            print("{}:{: >5}:do_POST:".format(stamp, code))
            sys.stdout.flush()

class ThreadedServer(ThreadingMixIn, HTTPServer):
    """Using the SocketServer mixin to make the HTTPServer multithreaded"""
    pass



import getopt
def usage():
    print("Usage:")
    print("    {} <opts>".format(sys.argv[0]))
    print("\nOptions:")
    print("    -p port    the port to open for incoming requests")
    print("    -w workers the number of workers in the pool")
    print("    -M         use the alternate munge")

def get_options():
    options = { 'port': 8675 , 'workers': 0, 'dedup': 'set' }
    try:
        opts, args = getopt.getopt(sys.argv[1:], "p:w:M")
    except:
        usage()
        sys.exit(1)

    ok_args = 0
    for o, a in opts:
        if o == "-p":
           options['port'] = int(a)
        elif o == "-w":
            options['workers'] = int(a)
        elif o == "-M":
            options['dedup'] = 'mangle'
        else:
            usage()
            raise Exception('unknown flag')
    if len(args) != ok_args :
        usage()
        print("saw {} args, expected {}".format(len(args), ok_args))
        sys.exit(1)
    return options

def main():
    options = get_options()
    global dedup_set 
    dedup_set = options['dedup'] == 'set'
    server =  ThreadedServer(('localhost', options['port']), PostHandler)
    # Millisecond timer is used to 'tag' debug output
    init_timer()
    # Creates a pool as a global, used by the PortHandlers
    create_pool(options['workers'])
    server.serve_forever()

main()
