#!/usr/bin/env python3

from sys import stderr
from enum import Enum
from threading import Thread
from socket import socket
from queue import Queue, Full
from time import sleep

from nefics.modules.devicebase import IEDBase
from nefics.protos.iec10x.packets import *
from nefics.protos.iec10x.enums import ALLOWED_COT
from nefics.protos.iec10x.util import time56

MAX_LENGTH : int           = 260   # APCI -> 5, MAX ASDU -> 255
MAX_QUEUE : int            = 256
DATATR_WAIT : float        = 0.40
ICMD_WAIT : float          = 0.10
SUPPORTED_ASDU : list[int] = [45, 46, 49, 58, 59, 62, 100, 102, 105]

# Definition of timeouts (IEC60870-5-104 section 9.6)
TIMEOUT_T0 = 30
TIMEOUT_T1 = 15
TIMEOUT_T2 = 10
TIMEOUT_T3 = 20

class ControlledState(Enum):
    STOPPED : int = 0
    STARTED : int = 1
    PENDING : int = 2

class IEC104Handler(Thread):
    
    def __init__(self, *args, device : IEDBase, connection : socket, **kwargs):
        super().__init__(*args, **kwargs)
        self._device : IEDBase = device
        self._sock : socket = connection
        self._terminate : bool = False
        self._state : ControlledState = ControlledState.STOPPED
        self._tx : int = 0
        self._rx : int = 0
        self._mem_map : list[int] = list()
        self._recv_queue : Queue[APDU] = Queue(maxsize=MAX_QUEUE)
        self._send_queue : Queue[APDU] = Queue(maxsize=MAX_QUEUE)
        self._validate_memory()
        self._sock.settimeout(TIMEOUT_T1)
    
    @property
    def terminate(self) -> bool:
        return self._terminate
    
    @terminate.setter
    def terminate(self, value : bool = False):
        self._terminate = value
    
    @property
    def rx(self) -> int:
        return self._rx

    @rx.setter
    def rx(self, value : int):
        if value < 0 or value > 0x7fff:
            self._rx = 0
        else:
            self._rx = value

    @property
    def tx(self) -> int:
        return self._tx

    @tx.setter
    def tx(self, value : int):
        if value < 0 or value > 0x7fff:
            self._tx = 0
        else:
            self._tx = value

    def _validate_memory(self):
        device : IEDBase = self._device
        for addr in range(0, 0x3FFFF):
            if (
                addr < 0x20000
                and device.check_addr(addr & 0x30000, addr & 0xFFFF, 1)
            ) or (
                addr == 0x20000
                and device.check_addr(0x20000, 0, 1)
                and device.check_addr(0x20000, 1, 1)
            ) or (
                addr > 0x20000
                and (addr - 1) not in self._mem_map
                and device.check_addr(addr & 0x30000, addr & 0xFFFF, 1)
                and device.check_addr((addr + 1) & 0x30000, (addr + 1) & 0xFFFF, 1)
            ):
                self._mem_map.append(addr)

    def _data_transfer(self):
        device = self._device
        alive : bool = True
        while self._state == ControlledState.STARTED and alive and not self.terminate:
            try:
                sleep(TIMEOUT_T2)
                for addr in self._mem_map:
                    apdu : APDU = APDU()
                    apdu /= APCI(type=0x00, Rx=self.rx, Tx=self.tx)
                    asdu_type : int
                    if addr < 0x20000: # Boolean value
                        value = 0x01 if device.read_bool(addr) else 0x00 # Determine SPI
                        asdu_type = 0x1e # single-point information with time tag CP56Time2a
                        io = IO30(_sq=0, _number=1, _balanced=False, IOA=addr, SIQ=value, time=time56())
                    else: # Measured value
                        value = device.read_word(addr)
                        asdu_type = 0x23 # Measured value, scaled value with time tag CP56Time2a
                        io = IO35(_sq=0, _number=1, _balanced=False, IOA=addr, SVA=value, time=time56())
                    apdu /= ASDU(
                        type=asdu_type, 
                        VSQ=VSQ(SQ=0, number=1),
                        COT=0x03, # Spontaneous
                        CommonAddress=device.guid & 0xFF,
                        IO=[io]
                    )
                    self._send_queue.put(APDU(apdu.build()))
                    sleep(min(DATATR_WAIT, TIMEOUT_T2/len(self._mem_map)))
            except BrokenPipeError:
                alive = False

    def _frame_receiver(self):
        buffer : bytes = b''
        alive : bool = True
        sock = self._sock
        while alive and not self._terminate:
            try:
                buffer = sock.recv(MAX_LENGTH)
                apdu : APDU = APDU(buffer)
                assert apdu.haslayer('APCI'), f'Malformed frame: {bytes(buffer)}'
                self._recv_queue.put(APDU(buffer), block=True, timeout=TIMEOUT_T2)
                if apdu['APCI'].type == 0x00: # I-frame
                    self.rx += 1
                if apdu['APCI'].type == 0x01: # S-frame
                    if apdu['APCI'].Rx != self.tx:
                        stderr.write(f'Sequence error ({apdu["APCI"].Rx} != {self.tx}) -- Synchronizing\r\n')
                        stderr.flush()
                        self.tx = apdu['APCI'].Rx
            except Full:
                stderr.write(f'ERROR :: Receive queue full\r\n')
                stderr.flush()
            except (TimeoutError, BrokenPipeError):
                alive = False
            except AssertionError as e:
                stderr.write(f'ERROR :: {str(e)}\r\n')
                stderr.flush()

    def _frame_sender(self):
        alive : bool = True
        sock = self._sock
        state = self._state
        while alive and not self.terminate:
            try:
                if not self._send_queue.empty():
                    next_apdu : APDU = self._send_queue.get(block=False)
                    sock.send(next_apdu.build())
                    self.tx += 1
                elif self._send_queue.empty() and state == ControlledState.PENDING:
                    state = ControlledState.STOPPED
                else:
                    sleep(DATATR_WAIT)
            except (BrokenPipeError, TimeoutError):
                alive = False

    def _unknown_parameter(self, apdu : APDU, cot : int):
        # Respond with specific CoT
        asdu : ASDU = apdu['ASDU']
        rasdu : ASDU = ASDU(type=asdu.type, VSQ=asdu.VSQ, COT_flags=0b01, COT=cot, CommonAddress=asdu.CommonAddress, IO=asdu.IO)
        self._send_queue.put(APDU()/APCI(type=0x00, Rx=self.rx, Tx=self.tx)/rasdu, block=True, timeout=TIMEOUT_T2)

    def _handle_iframe(self, apdu : APDU):
        asdu : ASDU = apdu['ASDU']
        atype : int = asdu.type
        cot : int = asdu.COT
        device = self._device
        oio = asdu.IO
        if atype == 100 and cot == 6 : # Interrogation command (act)
            # Add IC (actcon) to the message queue
            rasdu = ASDU(type=100, VSQ=VSQ(SQ=0, number=1), COT_flags=0b00, COT=7, CommonAddress=self.guid & 0xFF, IO=IO100(_sq=0, _number=1, _balanced=False, IOA=0, QOI=oio.QOI))
            self._send_queue.put(APDU()/APCI(type=0x00, Rx=self.rx, Tx=self.tx)/rasdu, block=True, timeout=TIMEOUT_T2)
            sleep(ICMD_WAIT)
            # Add process information
            for addr in self._mem_map:
                asdu_type : int
                if addr < 0x20000: # Boolean value
                    value = 0x01 if device.read_bool(addr) else 0x00 # Determine SPI
                    asdu_type = 0x1e # single-point information with time tag CP56Time2a
                    io = IO1(_sq=0, _number=1, _balanced=False, IOA=addr, SIQ=value)
                else: # Measured value
                    value = device.read_word(addr)
                    asdu_type = 0x0b # Measured value, scaled value with time tag CP56Time2a
                    io = IO11(_sq=0, _number=1, _balanced=False, IOA=addr, value=ScaledValue(SVA=value), time=time56())
                rasdu = ASDU(type=asdu_type, VSQ=VSQ(SQ=0, number=1), COT=0x14, CommonAddress=device.guid & 0xFF, IO=[io])
                self._send_queue.put(APDU()/APCI(type=0x00, Rx=self.rx, Tx=self.tx)/rasdu, block=True, timeout=TIMEOUT_T2)
                sleep(min(ICMD_WAIT, TIMEOUT_T2/len(self._mem_map)))
            # Add IC (actterm) to the message queue
            rasdu = ASDU(type=100, VSQ=VSQ(SQ=0, number=1), COT_flags=0b00, COT=10, CommonAddress=self.guid & 0xFF, IO=IO100(_sq=0, _number=1, _balanced=False, IOA=0, QOI=oio.QOI))
            self._send_queue.put(APDU()/APCI(type=0x00, Rx=self.rx, Tx=self.tx)/rasdu, block=True, timeout=TIMEOUT_T2)

    def run(self):
        state = self._state
        buffer : APDU = APDU()
        datatr : Thread = None
        receiver : Thread = Thread(target=self._frame_receiver)
        sender : Thread = Thread(target=self._frame_sender)
        sender.start()
        receiver.start()
        while not self.terminate:
            try:
                if self._recv_queue.empty():
                    sleep(DATATR_WAIT)
                else:
                    buffer = self._recv_queue.get(block=False)
                    apci = buffer['APCI']
                    if state == ControlledState.STOPPED:
                        if apci.type == 0x03: # Received a U-frame
                            utype = apci.UType
                            self._send_queue.put(APDU()/APCI(type=0x03, UType=(utype << 1)))
                            if utype == 0x01: # STARTDT
                                state = ControlledState.STARTED
                                datatr = Thread(target=self._data_transfer)
                                datatr.start()
                        else:
                            self.terminate = True
                    elif state == ControlledState.STARTED:
                        if apci.type == 0x00: # I-frame
                            asdu : ASDU = apci['ASDU']
                            io = asdu.IO
                            if asdu.CommonAddress != self._device.guid: # Common address mismatch
                                # Respond with CoT 46 (unknown common address of ASDU)
                                self._unknown_parameter(buffer, 46)
                            elif asdu.type not in TYPEID_ASDU.keys() or asdu.type not in SUPPORTED_ASDU: # Unknown ASDU type
                                # Respond with CoT 44 (unknown type identification)
                                self._unknown_parameter(buffer, 44)
                            elif ALLOWED_COT[asdu.type] & (2 ** (asdu.COT - 1)) == 0: # COT not allowed for that ASDU type
                                # Respond with CoT 45 (unknown type cause of transmission)
                                self._unknown_parameter(buffer, 45)
                            elif (asdu.type == 100 and io.IOA != 0) or (asdu.type != 100 and ((isinstance(io, IO) and io.IOA not in self._mem_map) or (isinstance(io, list) and any(x.IOA not in self._mem_map for x in io)))): # Chek for valid IOAs
                                # Respond with CoT 47 (unknown information object address)
                                self._unknown_parameter(buffer, 47)
                            else:
                                # Handle supported I-frame
                                self._handle_iframe(buffer)
                        elif apci.type == 0x01: # S-frame
                            continue # Synchronization handled by the receiver. Do nothing.
                        else: # U-frame
                            utype = apci.UType
                            self._send_queue.put(APDU()/APCI(type=0x03, UType=(utype << 1)))
                            if utype == 0x04: # STOPDT
                                if self._send_queue.empty() and self._recv_queue.empty():
                                    state = ControlledState.STOPPED
                                else:
                                    state = ControlledState.PENDING
                                datatr.join()
                                datatr = None
                    else:
                        sleep(DATATR_WAIT)
            except AssertionError as e:
                stderr.write(f'ERROR :: {str(e)}\r\n')
                stderr.flush()
        if datatr is not None:
            datatr.join()
        receiver.join()
        sender.join()
        self._sock.close()
        
    