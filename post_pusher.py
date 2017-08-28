#! /usr/bin/env python3


from multiprocessing import Pool

import urllib.request

def CreatePool(num_threads=0) :
    if num_threads > 0:
        pool = Pool(num_threads)
    else:
        pool = Pool(num_threads)

    return pool

def count(url):
    url= url.rstrip()
    count = -1
    with urllib.request.urlopen(url) as f:
        count = 0
        for l in f:
            count += 1
    return "{}: {}".format(url, count)
        

def main(url_file, num_threads):
    urls = open(url_file,"r")
    pool = CreatePool(num_threads)
    for r in pool.map(count, urls):
        print(r)


main("medium_url",4)
