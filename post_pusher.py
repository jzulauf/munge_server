#! /usr/bin/env python3
"""
post_pusher.py

test and exerciser for the http app server munge_server.py

Given the name of a server containing files to fetch and munge
randomly group the files together in munge requests POST'd to
the munge_server, and optionally testing that the file munging
meets the munge criteria -- which is super secret, so like
don't read the code to figure it out, okay, really.

Note the the validation is incomplete in that it only tests
if the munge criteria is met, but does not independently verify
that the munging wasn't carried our in excess of the criteria.

For completeness this should be added.
"""



from multiprocessing import Pool
from io import TextIOWrapper

import urllib.request
import random
import sys

# Globals
debug_level = 0

def CreatePool(num_threads=0) :
    """The pool allows for multiple post to be sent simulataneously"""
    if num_threads > 0:
        pool = Pool(num_threads)
    else:
        pool = Pool(num_threads)

    return pool

def test_response(response) : 
    """Read the response and verify that the content meets the munging criteria"""
    last = ""
    offset = 1
    digits = set(list("0123456789"))
    out = []
    for c in iter(lambda: response.read(1), '') :
        out.append(c)
        if c in digits:
            if debug_level > 1:
                print(":".join(out))
            return "FAIL: digit at {}:".format(offset)
        elif c == last:
            if debug_level > 1:
                print(":".join(out))
            return "FAIL: dupl. at {}:".format(offset)
        offset += 1
        last = c
    return "PASS"
      
class Poster:
    def __init__(self, post_url, validation_level):
        self.post_url = post_url
        self.do_test = validation_level > 0

    def __call__(self, message):
        call_result =  "FAIL:urlopen"
        try:
            if debug_level > 2:
                print("Sending", message)
                sys.stdout.flush()
            payload = message.encode("utf-8")
            with urllib.request.urlopen(self.post_url, payload) as f:
                if f.status == 200 :
                    t = TextIOWrapper(f, encoding="utf-8")
                    if self.do_test:
                        call_result = test_response(t)
                    else:
                        call_result = "PASS:trivial"
                else:
                    call_result = "FAIL:server_err"
        except urllib.error.URLError as e:
            call_result = "FAIL:HTTPError:{}:{}".format(e.reason, e.code)
        except:
            call_result = "FAIL:unknown:" + sys.exc_info()[0]

        result =  "{}: {}".format(call_result, message)
        return result
        
def create_grouped_urls(file_server, files):
    random.seed(42,2) # For consistant results
    groups = []
    current_group = []
    for f in files:
        url = file_server + "/" + f.rstrip().strip()
        if debug_level > 1:
            print("Url:", url)
        if random.randint(0,2) :
            # Two thirds of the time we'll add a url to the current group
            # to get a pseudo random variation in the number of urls
            current_group.append(url)
        else:
            groups.append(", ".join(current_group))
            if debug_level > 0:
                print("Group:", groups[-1])
            current_group = [ url ]
    if current_group:
        groups.append(", ".join(current_group))
        if debug_level > 0:
            print("Group:", groups[-1])

    return groups
        

def main(post_url, file_server, file_list, num_threads, one_group, validation_level):
    if not one_group:
        files = open(file_list,"r")
        groups = create_grouped_urls(file_server, files)
    else:
        groups = [ one_group ]
    if debug_level > 3:
        print("Groups:", groups)
    pool = CreatePool(num_threads)
    # Lambda really should work here.... but map wants to pickle the proc
    # and you can't pickle lambda's apparently
    #poster = Poster(post_url)
    #post = lambda g: poster.post(g)
    results = pool.map(Poster(post_url,validation_level), groups)
    print("\n".join(results))


def usage():
    print("Usage:")
    print("    {} <opts> file_list".format(sys.argv[0]))
    print("    {} -u url_list".format(sys.argv[0]))
    print("\nOptions")
    print("    -f file_server    the URL of the root of the file_list")
    print("    -h app_server     the URL file munging app server")
    print("    -w num_threads    the paralell width for post creation")
    print("    -u url_list       post one request with the csv url_list given")
    print("    -v validation_lvl control the level of testing > 0 for munge testing (default 1)")

import getopt
app_host = "http://localhost:8675"
file_server = "http://localhost"
width = 4

try:
    opts, args = getopt.getopt(sys.argv[1:], "f:h:w:u:v:")
except:
    usage()
    sys.exit(1)

one_group = ""
ok_args = 1
validation_level = 1
file_list = ""

for o, a in opts:
    if o == "-h":
        app_host = a
    elif o == "-w":
        width = int(a)
    elif o == "-f":
        file_server = a
    elif o == "-v":
        validation_level = int(a)
    elif o == "-u":
        # Debug flag to force the pusher to send this exact group of URLS
        one_group = a
        width = 1
        ok_args = 0
    else:
        usage()
        print('unknown flag', o)
        sys.exit(1)

if len(args) != ok_args :
    usage()
    print("saw {} args, expected {}".format(len(args), ok_args))
    sys.exit(1)

if ok_args == 1:
    file_list = args[0]

main(app_host, file_server, file_list, width, one_group, validation_level)
