#!/usr/bin/env python3

import nmap3
import argparse
import sys

def main():
    aparser = argparse.ArgumentParser()
    aparser.add_argument('ip')
    args = aparser.parse_args()
    ip_addr = str(args.ip)
    nm = nmap3.Nmap()
    results = []
    scans = 10
    for i in range(scans):
        sys.stdout.write(f'\rScan {i+1}/{scans}')
        sys.stdout.flush()
        r = nm.nmap_os_detection(ip_addr)
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
