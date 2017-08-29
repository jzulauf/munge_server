#! /usr/bin/env python3


from multiprocessing import Pool
from io import TextIOWrapper

import urllib.request
import random
import sys

def CreatePool(num_threads=0) :
    if num_threads > 0:
        pool = Pool(num_threads)
    else:
        pool = Pool(num_threads)

    return pool

def test_response(response) : 
    last = ""
    offset = 1
    digits = set(list("0123456789"))
    out = []
    for c in iter(lambda: response.read(1), '') :
        out.append(c)
        if c in digits:
            print(":".join(out))
            return "FAIL: digit at {}:".format(offset)
        elif c == last:
            print(":".join(out))
            return "FAIL: dupl. at {}:".format(offset)
        offset += 1
        last = c
    return "PASS"
      
class Poster:
    def __init__(self, post_url):
        self.post_url = post_url

    def __call__(self, message):
        print("Sending", message)
        sys.stdout.flush()
        payload = message.encode("utf-8")
        result =  "FAIL:urlopen: {}".format(message)
        with urllib.request.urlopen(self.post_url, payload) as f:
            t = TextIOWrapper(f, encoding="utf-8")
            result =  "{}: {}".format(test_response(t), message)

        return result
        
def create_grouped_urls(file_server, files):
    random.seed(42,2) # For consistant results
    groups = []
    current_group = []
    for f in files:
        url = file_server + "/" + f.rstrip().strip()
        print("Url:", url)
        if random.randint(0,2) :
            # Two thirds of the time we'll add a url to the current group
            # to get a pseudo random variation in the number of urls
            current_group.append(url)
        else:
            groups.append(", ".join(current_group))
            current_group = [ url ]
    if current_group:
        print("Group:", groups[-1])
        groups.append(", ".join(current_group))

    #print("Groups", groups)
    return groups
        

def main(post_url, file_server, file_list, num_threads):
    files = open(file_list,"r")
    groups = create_grouped_urls(file_server, files)
    pool = CreatePool(num_threads)
    # Lambda really should work here....
    #poster = Poster(post_url)
    #post = lambda g: poster.post(g)
    results = pool.map(Poster(post_url), groups)
    print("\n".join(results))


def usage():
    print("Usage: {} <opts> file_list", sys.argv[0])
    print("\nOptions")
    print("    -f file_server    the URL of the root of the file_list")
    print("    -h app_server     the URL file munging app server")
    print("    -w num_threads    the paralell width for post creation")

import getopt
app_host = "http://localhost:8675"
file_server = "http://localhost"
width = 4
opts, args = getopt.getopt(sys.argv[1:], "f:h:w:")
file_list = args[0]
if len(args) != 1 :
    raise Exception('missing url file arg, or too many')

for o, a in opts:
    if o == "-h":
        app_host = a
    elif o == "-w":
        width = int(a)
    elif o == "-f":
        file_server = a
    else:
        raise Exception('unknown flag')

main(app_host, file_server, file_list, width)
