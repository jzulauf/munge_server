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
        
def group_urls(url_file):
    random.seed(42,2) # For consistant results
    groups = []
    current_group = []
    for url in url_file:
        url = url.rstrip()
        print("Url:", url)
        if random.randint(0,2) :
            current_group.append(url)
        else:
            groups.append(", ".join(current_group))
            current_group = [ url ]
    if current_group:
        groups.append(", ".join(current_group))

    print("Groups", groups)
    return groups
        

def main(post_url, url_file, num_threads):
    urls = open(url_file,"r")
    groups = group_urls(urls)
    pool = CreatePool(num_threads)
    # Lambda really should work here....
    #poster = Poster(post_url)
    #post = lambda g: poster.post(g)
    results = pool.map(Poster(post_url), groups)
    print("\n".join(results))


import getopt
host = "http://localhost:8675"
width = 4
opts, args = getopt.getopt(sys.argv[1:], "h:w:")
url_file = args[0]
if len(args) != 1 :
    raise Exception('missing url file arg, or too many')
for o, a in opts:
    if o == "-h":
        host = a
    elif o == "-w":
        width = int(a)
    else:
        raise Exception('unknown flag')

main(host, url_file, width)
