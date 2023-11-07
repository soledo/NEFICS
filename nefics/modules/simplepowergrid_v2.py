#!/usr/bin/env python3

from socket import _Address
from time import sleep
from typing import Optional
# NEFICS imports
from nefics.modules.devicebase import IEDBase, LOG_PRIO
from nefics.protos.iec10x.iec104 import IEC104Handler
from nefics.simproto import NEFICSMSG, MESSAGE_ID

class SimpleRTU(IEDBase):
    'Generic RTU'

# Source (Generator)
VOLTAGE_IOA = 0x28000 # Float read-only

class Source(SimpleRTU):

    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        assert all(x is not None for x in [guid, neighbors_out])
        assert len(neighbors_out) >= 1
        assert 'voltage' in kwargs.keys()
        assert isinstance(kwargs['voltage'], float)
        super().__init__(guid, [], neighbors_out[:1], **kwargs)
        self._voltage : float = kwargs['voltage']
        self._memory[VOLTAGE_IOA] = 0 # Reserve memory location
        self.write_ieee_float(VOLTAGE_IOA, kwargs['voltage']) # write initial value
    
    def __str__(self) -> str:
        return f'Vout: {self._voltage:6.3f} V\r\n'
    
    def handle_specific(self, message: NEFICSMSG):
        if message.SenderID in self._n_out_addr.keys():
            addr = self._n_out_addr[message.SenderID]
            if addr is not None:
                if message.MessageID == MESSAGE_ID['MSG_GETV']:
                    pkt = NEFICSMSG(
                        SenderID=self.guid,
                        ReceiverID=message.SenderID,
                        MessageID=MESSAGE_ID['MSG_VOLT'],
                        FloatArg0=self._voltage
                    )
                else:
                    self._log(f'Received a NEFICS message not supported by simplepowergrid.Source from {addr}: {repr(message)}')
                    pkt = NEFICSMSG(
                        SenderID=self.guid,
                        ReceiverID=message.SenderID,
                        MessageID=MESSAGE_ID['MSG_UKWN']
                    )
                self._sock.sendto(pkt.build(), addr)

# Transmission
BREAKER_IOA_BASE = 0x10000 # Boolean RW [0x10000-0x1FFFF]

class Transmission(SimpleRTU):

    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        assert all(x is not None for x in [guid, neighbors_in, neighbors_out])
        assert len(neighbors_in) >= 1
        assert len(neighbors_out) >= 1
        assert all(x not in neighbors_out for x in neighbors_in)
        assert all(x in kwargs.keys() for x in ['loads', 'state'])
        assert isinstance(kwargs['loads'], list)
        assert len(kwargs['loads']) in range(1,0x10000)
        assert all(isinstance(x, float) for x in kwargs['loads'])
        assert isinstance(kwargs['state'], int)
        assert kwargs['state'] in range(2 ** len(kwargs['loads']))
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        self._loads : list[float] = kwargs['loads']
        self._state : int = kwargs['state']
        self._laststate : Optional[int] = None
        self._load : Optional[float] = None
        self._vin : Optional[float] = None
        self._vout : Optional[float] = None
        self._amp : Optional[float] = None
        self._rload : Optional[float] = None
        self._wait_exec : Optional[int] = None
    
    def __str__(self) -> str:
        if all(x is not None for x in [self._vin, self._vout, self._amp, self._load, self._rload]):
            return f'Vin:  {self._vin:6.3f} V\r\nVout: {self._vout:6.3f} V\r\nI:    {self._amp:6.3f} A\r\nBreakers: {self._state:b}\r\nR:    {self._load:6.3f} Ohm\r\nLoad: {self._rload:6.3f} Ohm\r\n'
        return 'Awaiting data from configured neighbors ...\r\n'
    
    def handle_specific(self, message: NEFICSMSG):
        if message.SenderID in list(self._n_in_addr.keys()) + list(self._n_out_addr.keys()):
            addr = self._n_in_addr[message.SenderID] if message.SenderID in self._n_in_addr.keys() else self._n_out_addr[message.SenderID]
            isinput = bool(message.SenderID in self._n_in_addr.keys())
            if addr is not None:
                pkt = NEFICSMSG(
                    SenderID=self.guid,
                    ReceiverID=message.SenderID,
                )
                if message.MessageID == MESSAGE_ID['MSG_GETV'] and not isinput:
                    if self._vout is not None:
                        pkt.MessageID = MESSAGE_ID['MSG_VOLT']
                        pkt.FloatArg0 = self._vout
                    else:
                        pkt.MessageID = MESSAGE_ID['MSG_NRDY']
                elif message.MessageID == MESSAGE_ID['MSG_VOLT'] and isinput:
                    self._vin = message.FloatArg0
                    pkt = None
                elif message.MessageID == MESSAGE_ID['MSG_GREQ'] and isinput:
                    if all(x is not None for x in [self._load, self._rload]):
                        pkt.MessageID = MESSAGE_ID['MSG_TREQ']
                        pkt.FloatArg0 = self._load + self._rload
                    else:
                        pkt.MessageID = MESSAGE_ID['MSG_NRDY']
                elif message.MessageID == MESSAGE_ID['MSG_TREQ'] and not isinput:
                    self._rload = message.FloatArg0
                    self._log(f'Received REQ {self._rload:f} from {addr[0]:s}')
                    return
                else:
                    self._log(f'Received a NEFICS message not supported by simplepowergrid. Transmission from {addr[0]}: {repr(message)}')
                    pkt.MessageID = MESSAGE_ID['MSG_UKWN']
                if pkt is not None:
                    self._sock.sendto(pkt.build(), addr)
    
    def simulate(self):
        # Request updated values
        if all(x is not None for x in list(self._n_in_addr.values()) + list(self._n_out_addr.values())):
            addrs : list[_Address] = list()
            pkts : list[NEFICSMSG] = list()
            # Request output load
            dstid : int = list(self._n_out_addr.keys())[0]
            addrs.append(self._n_out_addr[dstid])
            pkts.append(NEFICSMSG(
                SenderID=self.guid,
                ReceiverID=dstid,
                MessageID=MESSAGE_ID['MSG_GREQ']
            ))
            # Request input voltage
            dstid : int = list(self._n_in_addr.keys())[0]
            addrs.append(self._n_in_addr[dstid])
            pkts.append(NEFICSMSG(
                SenderID=self.guid,
                ReceiverID=dstid,
                MessageID=MESSAGE_ID['MSG_GETV']
            ))
            # Send requests
            for pkt, addr in zip(pkts, addrs):
                self._sock.sendto(pkt.build(), addr)
            sleep(0.5)
        # Check for any state changes in the substation
        if self._state != self._laststate:
            self._laststate = self._state
            if self._state == 0:
                self._log('All breakers are OPEN', LOG_PRIO['WARNING'])
                self._load = float('inf')
            else:
                self._load = None
                for i in range(len(self._loads)):       # Iterate over substation breakers
                    if (self._state & (2 ** i)) > 0:    # If the current breaker is 'OFF/CLOSED' ==> Corresponding load is connected
                        if self._loads[i] == 0:         # Failure condition ==> Simulate a broken breaker
                            #TODO: Failure condition
                            self._log(f'Failure condition: short circuit detected on breaker {(BASE_IOA // 10) + 1 +i}', devicebase.LOG_PRIO['CRITICAL'])
                            self._load = 0
                            break
                        else:
                            self._load = self._loads[i] if self._load is None else (self._load * self._loads[i]) / (self._load + self._loads[i])
        # Determine new local values
        if self._load == float('inf'):                  # Failure condition ==> No output, no current
            self._vout = 0
            self._amp = 0
        elif all(x is not None for x in [self._vin, self._load, self._rload]):
            if self._rload == float('inf'):             # Failure in another substation
                self._log('Breakers OPEN somewhere on the grid', devicebase.LOG_PRIO['WARNING'])
                self._vout = self._vin
            else:
                self._vout = self._vin * self._rload / (self._rload + self._load)
            try:
                self._amp = (self._vin - self._vout) / self._load
            except ZeroDivisionError:
                self._log('Short circuit somewhere on the grid', devicebase.LOG_PRIO['CRITICAL'])
                self._amp = float('inf')                # Failure condition - Short circuit in the system ==> Current increases toward infinity
        sleep(0.333)
