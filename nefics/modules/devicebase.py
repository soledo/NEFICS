#!/usr/bin/env python3

import sys
import io
from signal import SIGINT, SIGTERM
from types import FrameType
from netifaces import gateways, ifaddresses
from netaddr import valid_ipv4, IPNetwork
from socket import socket, AF_INET, SOCK_DGRAM, IPPROTO_UDP, SO_REUSEADDR, SO_BROADCAST, SOL_SOCKET, timeout
from threading import Thread
from collections import deque
from datetime import datetime
from time import sleep

if sys.platform not in ['win32']:
    from socket import SO_REUSEPORT

# NEFICS imports
import nefics.simproto as simproto

# Try to determine the main broadcast address
try:
    gtwys = gateways()
    ipaddresses =  ifaddresses(list(gtwys['default'].values())[0][1])
    for a in ipaddresses.values():
        if valid_ipv4(a[0]['addr']):
            ipnet = IPNetwork(f'{a[0]["addr"]}/{a[0]["netmask"]}')
            break
    SIM_BCAST = str(ipnet.broadcast)
except IndexError:
    print('ERROR: Could not determine default broadcast address')
    sys.exit(1)


BUFFER_SIZE = 512
LOG_PRIO = {
    'CRITICAL': 0,
    'ERROR': 1,
    'WARNING': 2,
    'INFO': 3,
    'DEBUG': 4,
    0: 'CRITICAL',
    1: 'ERROR',
    2: 'WARNING',
    3: 'INFO',
    4: 'DEBUG'
}

class IEDBase(Thread):
    '''
    Main device class.
    
    All additional devices must extend from this class.

    If a device requires additional arguments, use kwargs to
    extract any additional values.
    '''

    def __init__(self, guid: int, neighbors_in: list=list(), neighbors_out: list=list(), **kwargs):
        assert all(val is not None for val in [guid, neighbors_in, neighbors_out])
        assert all(isinstance(val, int) for val in neighbors_in + neighbors_out)
        assert all(val not in neighbors_in for val in neighbors_out)
        assert all(val not in neighbors_out for val in neighbors_in)
        super().__init__()
        self._guid = guid
        self._terminate = False
        self._n_in_addr = {n: None for n in neighbors_in}                       # IDs of neighbors this device depends on
        self._n_out_addr = {n: None for n in neighbors_out}                     # IDs of neighbors depending on this device
        self._sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)                   # Use UDP
        if sys.platform not in ['win32']:
            self._sock.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)                  # Enable port reusage (unix systems)
        self._sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)                      # Enable address reuse
        self._sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)                      # Enable broadcast
        self._sock.bind(('', simproto.SIM_PORT))                                # Bind to simulation port on all addresses
        self._sock.settimeout(0.333)                                            # Set socket timeout (seconds)
        self._msgqueue = deque(maxlen=simproto.QUEUE_SIZE//simproto.DATA_LEN)   # Simulation message queue (64KB)
        if 'log' in kwargs.keys() and isinstance(kwargs['log'], io.TextIOBase):
            self._logfile = kwargs['log']
        else:
            self._logfile = None
    
    @property
    def guid(self) -> int:
        return self._guid
    
    @guid.setter
    def guid(self, value: int):
        assert value is not None
        self._guid = value
    
    @property
    def terminate(self) -> bool:
        return self._terminate
    
    @terminate.setter
    def terminate(self, value: bool):
        assert value is not None
        self._terminate = value
    
    @property
    def logfile(self) -> io.TextIOBase:
        return self._logfile
    
    @logfile.setter
    def logfile(self, value: io.TextIOBase):
        self._logfile = value

    def simulate(self):
        '''
        Override this method with the physical simulation of the
        device.

        Note that any messages exchanged between devices are
        asynchronous.
        '''
        sleep(10)

    def sim_handler(self):
        '''
        This method is meant to be runned as a Thread.

        If all the neighbors have been identified, it will run the
        simulate method in a loop until the self._terminate boolean
        is set.
        '''
        while any(x is None for x in list(self._n_in_addr.values()) + list(self._n_out_addr.values())) and not self._terminate:
            sleep(1)
        while not self._terminate:
            self.simulate()

    def handle_specific(self, message: simproto.NEFICSMSG):
        '''
        Override this method to handle incomming messages from the
        queue.

        For more information on the message format, see nefics/simproto.py
        '''
        try:
            addr = self._n_in_addr[message.SenderID] if message.SenderID in self._n_in_addr else self._n_out_addr[message.SenderID]
        except KeyError:
            addr = None
        if addr is not None:
            pkt = simproto.NEFICSMSG(
                SenderID=self.guid,
                ReceiverID=message.SenderID,
                MessageID=simproto.MESSAGE_ID['MSG_UKWN']
            )
            self._sock.sendto(pkt.build(), addr)

    def msg_handler(self):
        '''
        This method is meant to be runned as a Thread.

        While the self._terminate boolean is not set, this method will
        check if there are any messages in the queue and, if those are
        meant for this device, it will handle the message.

        Since some messages are sent to the local broadcast address, some
        messages might not be meant for this device.
        '''
        while not self._terminate:
            if len(self._msgqueue) > 0:
                next_msg = self._msgqueue.popleft()
                m_addr = next_msg[0]
                next_msg = next_msg[1]
                if next_msg.ReceiverID == self.guid:
                    if next_msg.MessageID == simproto.MESSAGE_ID['MSG_WERE']:
                        pkt = simproto.NEFICSMSG(
                            SenderID=self.guid,
                            ReceiverID=next_msg.SenderID,
                            MessageID=simproto.MESSAGE_ID['MSG_ISAT']
                        )
                        self._sock.sendto(pkt.build(), m_addr)
                    elif next_msg.MessageID == simproto.MESSAGE_ID['MSG_ISAT']:
                        nid = next_msg.SenderID
                        if nid in self._n_in_addr and self._n_in_addr[nid] is None:
                            self._n_in_addr[nid] = m_addr
                        if nid in self._n_out_addr and self._n_out_addr[nid] is None:
                            self._n_out_addr[nid] = m_addr
                    elif next_msg.MessageID in [simproto.MESSAGE_ID['MSG_NRDY'], simproto.MESSAGE_ID['MSG_UKWN']]:
                        continue
                    else:
                        self.handle_specific(next_msg)
            else:
                sleep(0.333)
    
    def identify_neighbors(self):
        '''
        This method is meant to be runned as a Thread.

        It sends a 'MSG_WERE' packet for every neighbor the device
        is supposed to have until either the device knows the IP
        address of every neighbor, or the self._terminate boolean
        value is set.
        '''
        while not self._terminate and any(x is None for x in list(self._n_in_addr.values()) + list(self._n_out_addr.values())):
            for nid in [x for x in self._n_in_addr.keys() if self._n_in_addr[x] is None] + [x for x in self._n_out_addr.keys() if self._n_out_addr[x] is None]:
                pkt = simproto.NEFICSMSG(
                    SenderID=self._guid,
                    ReceiverID=nid,
                    MessageID=simproto.MESSAGE_ID['MSG_WERE']
                )
                self._sock.sendto(pkt.build(), (SIM_BCAST, simproto.SIM_PORT))
            sleep(0.333)

    def _log(self, message:str, prio:int=LOG_PRIO['INFO']):
        if self._logfile is not None and isinstance(self._logfile, io.TextIOBase):
            line = datetime.now().ctime()
            msg = message.replace("\n", "").replace("\r","")
            line += f'\t[{LOG_PRIO[prio]}] :: {msg}\r\n'
            try:
                self._logfile.write(line)
                self._logfile.flush()
            except IOError:
                sys.stderr.write(f'{line[:-2]} -- IOError\r\n')
                sys.stderr.flush()

    def run(self):
        msghandler = Thread(target=self.msg_handler)
        identify = Thread(target=self.identify_neighbors)
        simhandler = Thread(target=self.sim_handler)
        msghandler.start()
        identify.start()
        simhandler.start()
        while not self._terminate: # Receive incomming messages and add them to the message queue
            try:
                msgdata, msgfrom = self._sock.recvfrom(BUFFER_SIZE)
                msgdata = simproto.NEFICSMSG(msgdata)
                self._msgqueue.append([msgfrom, msgdata])
            except timeout:
                pass
        simhandler.join()
        identify.join()
        msghandler.join()

class DeviceHandler(Thread):

    def __init__(self, device: IEDBase):
        super.__init__()
        self._device = device
        self._terminate = False
    
    @property
    def terminate(self) -> bool:
        return self._terminate
    
    @terminate.setter
    def terminate(self, value: bool):
        self._terminate = value
    
    def status(self):
        '''Override this method!'''
        print('Override this method!')
    
    def set_terminate(self, signum: int, stack_frame: FrameType):
        if signum in [SIGINT, SIGTERM]:
            self._device.terminate = True
            self._terminate = True
            sys.stderr.write(f'Received a termination signal. Terminating threads ...\r\n')
            sys.stderr.flush()
        else:
            sys.stderr.write(f'Signal handler recevied an unsupported signal: {signum}\r\n')
            sys.stderr.flush()
    
    def run(self):
        self._device.start()
        while not self._terminate:
            # Dummy loop
            # Place here the handling of any incoming ICS protocol connection
            sleep(1)
        self._device.join()
