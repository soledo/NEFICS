#!/usr/bin/env python3

import sys
from threading import Thread
from netaddr import valid_ipv4
from socket import AF_INET, IPPROTO_TCP, SOCK_STREAM, socket, timeout
from time import sleep
from types import FrameType
from typing import Optional

# NEFICS imports
from nefics.protos.iec10x.enums import DPI_ENUM
from nefics.protos.iec10x.packets import APDU, APCI
from nefics.protos.iec10x.iec104 import IEC104_PORT, TIMEOUT_T1, TIMEOUT_T2

BUFFER_SIZE = 260

class IEC104Poller(object):

    def __init__(self, address:str):
        super().__init__()
        assert valid_ipv4(address)
        self._terminate = False
        self._sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        self._sock.settimeout(TIMEOUT_T1)
        try:
            self._sock.connect((address, IEC104_PORT))
        except timeout:
            print('[!] Socket connection timeout')
            sys.exit()
        print('[+] Connection established')
    
    def terminate(self, signum : int, stack_frame : Optional[FrameType]):
        self._terminate = True

    def _keep_alive(self):
        while not self._terminate:
            apdu : APDU = APDU()/APCI(type=0x03, UType=0x10)
            self._sock.send(apdu.build())
            sleep(TIMEOUT_T2)

    def loop(self):
        try:
            ka_thread = Thread(target=self._keep_alive)
            print('[*] Sending STARTDT U-Frame ... ', end='')
            apdu = APDU()/APCI(type=0x03, UType=0x01)
            self._sock.send(apdu.build())
            data = self._sock.recv(BUFFER_SIZE)
            apdu = APDU(data)
            if apdu['APCI'].type != 0x03 or apdu['APCI'].UType != 0x02:
                print(f'ERROR\r\n[!] Unexpected Frame: {repr(apdu)}')
            print('Confirmed')
            ka_thread.start()
            while not self._terminate:
                data = self._sock.recv(BUFFER_SIZE)
                apdu = APDU(data)
                print(f'[!] Received APDU :: {repr(apdu)}')
            ka_thread.join()
            print('[*] Sending STOPDT U-Frame ... ')
            apdu = APDU()/APCI(type=0x03, UType=0x04)
            self._sock.send(apdu.build())
            data = self._sock.recv(BUFFER_SIZE)
            apdu = APDU(data)
            while apdu['APCI'].type != 0x03 or apdu['APCI'].UType != 0x08:
                print('[!] Received pending Frame:', repr(apdu))
                data = self._sock.recv(BUFFER_SIZE)
                apdu = APDU(data)
            print('[*] STOPDT confirmed')
            print('[*] Closing connection ...')
            self._sock.close()
        except timeout:
            print('Socket timeout')
            sys.exit()


if __name__ == '__main__':
    import argparse
    import signal
    aparser = argparse.ArgumentParser(description='IEC 60870-4-104 device poller')
    aparser.add_argument('address', action='store', type=str, metavar='IPv4_ADDRESS')
    args = aparser.parse_args()
    try:
        poller = IEC104Poller(args.address)
    except AssertionError:
        print(f'Invalid IPv4 address: "{args.address}"')
        sys.exit()
    signal.signal(signal.SIGINT, poller.terminate)
    signal.signal(signal.SIGTERM, poller.terminate)
    poller.loop()
