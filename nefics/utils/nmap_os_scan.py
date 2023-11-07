#!/usr/bin/env python3

import nmap3
import argparse
import sys
from tqdm import tqdm

NMAP_ARGS : str = '-Pn -n -sS -sV -O -p 1-10240'

def main():
    aparser = argparse.ArgumentParser()
    aparser.add_argument('ip')
    aparser.add_argument('num_scans')
    args = aparser.parse_args()
    ip_addr = str(args.ip)
    scans = int(args.num_scans)
    nm = nmap3.Nmap()
    results = []
    for i in tqdm(range(scans), unit='scans'):
        r = nm.scan_command(ip_addr, NMAP_ARGS)
        r = nm.parser.os_identifier_parser(r)
        for rr in r[ip_addr]['osmatch']:
            results.append((rr['name'], rr['accuracy']))
    print('\r\n')
    sorted_results = {}
    for r in results:
        if r in sorted_results.keys():
            sorted_results[r] += 1
        else:
            sorted_results[r] = 1
    for rr in [(r[0], r[1], sorted_results[r]) for r in sorted_results.keys()]:
        print(f'"{rr[0]}",{rr[1]},{rr[2]}')

if __name__ == '__main__':
    main()
