#!/usr/bin/env python3
'''Scan a target multiple times to determine the SP and ISR values.'''

from nmap3 import Nmap
from re import compile
from tqdm import tqdm

# Regular expressions
SEQ_RE = compile(r'SEQ\([^)]+\)')
SP_RE = compile(r'^SEQ\([^(]*?SP=([0-9A-Fa-f]+?)%[^)]*?\)$')
ISR_RE = compile(r'^SEQ\([^(]*?ISR=([0-9A-Fa-f]+?)%[^)]*?\)$')
SCAN_RE = compile(r'^SCAN\([^)]+?\)(.*)$')

def main(ipaddr : str, count : int):
    nmap = Nmap()
    spvals : list[int] = []
    isrvals : list[int] = []
    scanerr : list[int] = []
    command = f'nmap -oX - -vvvv -p T:1-65535,U:53,67,68,161 --max-retries 3 --max-scan-delay 5ms --min-parallelism 10 -sSU -O -n -T4 -Pn {ipaddr}'
    '''
    - (-oX -) Output in XML format to stdout
    - (-vvvv) Be verbose x4
    - (-p T:1-65535,U:53,67,68,161) Scan all TCP ports and common UDP ports
    - (--max-retries 3) probe attempts
    - (--max-scan-delay 5ms) limit the delay between probes
    - (--min-parallelism 10) use at least 10 probes at a time
    - (-sSU) Do s SYN and UDP scans
    - (-O) determine target OS
    - (-n) Don't resolve DNS names
    - (-T4) Do an aggresive scan [fast]
    - (-Pn) Don't ping
    '''
    fingerprint : str = None
    for i in tqdm(range(count), unit='scan'):
        rawxml = nmap.run_command(command)
        xmlroot = nmap.get_xml_et(rawxml)
        host = xmlroot.find('host')
        if host is not None:
            hos = host.find('os')
            if hos is not None:
                osf = hos.find('osfingerprint')
                if osf is not None:
                    fingerp = osf.attrib['fingerprint'].replace('OS:','').replace('\n','')
                    if fingerprint is None:
                        fp = SCAN_RE.match(fingerp).groups()[0]
                        fingerprint = fp.replace(')',')\n')[:-1]
                    for seq in SEQ_RE.findall(fingerp):
                        sp = SP_RE.findall(seq)
                        isr = ISR_RE.findall(seq)
                        if len(sp):
                            for s in sp:
                                s = int(s, 16)
                                if s not in spvals:
                                    spvals.append(s)
                        if len(isr):
                            for ir in isr:
                                ir = int(ir, 16)
                                if ir not in isrvals:
                                    isrvals.append(ir)
                else:
                    scanerr.append(i)
    spvals.sort()
    isrvals.sort()
    print(
        f'{fingerprint}\n\n'
        f'Scan error runs: {scanerr}\n'
        f'SP values:  {[f"{val:02X}" for val in spvals]}\n'
        f'ISR values: {[f"{val:02X}" for val in isrvals]}\n\n'
    )

        
if __name__ == '__main__':
    from argparse import ArgumentParser
    aparser = ArgumentParser()
    aparser.add_argument('ip', metavar='IP address', action='store', type=str)
    aparser.add_argument('count', metavar='Scan count', action='store', type=int)
    args = aparser.parse_args()
    main(args.ip, args.count)
