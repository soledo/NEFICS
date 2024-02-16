#!/usr/bin/env python3
'''
IEC-60870-104 Protocol module for NEFICS.

This implementation uses a three-bytes Information Object Address, compliant with the standard.
The underlying protocol implementation defined in the 'packets' module support both the usual
two-byte and three-byte Information Object Address, as do many devices from various manufacturers.

This module provides a handler for NEFICS devices with a subset of supported ASDU types:
- C_SC_NA_1 (45)    Single Command
- C_DC_NA_1 (46)    Double Command
- C_SE_NB_1 (49)    Set-point command, scaled value
- C_SE_NC_1 (50)    Set-point command, short floating point number
- C_SC_TA_1 (58)    Single command with time tag CP56Time2a
- C_DC_TA_1 (59)    Double command with time tag CP56Time2a
- C_SE_TB_1 (62)    Set-point command with time tag CP56Time2a, scaled value
- C_SE_TC_1 (63)    Set-point command with time tag CP56Time2a, short floating point number
- C_IC_NA_1 (100)   Interrogation command
- C_RD_NA_1 (102)   Read command

In addition to the NEFICS handler, the module provides a rudimentary CLI able to communicate
with IEC-60870-104 devices.

-----------------------------------------------------
| Memory mappings for the emulated IEC-104 devices  |
-----------------------------------------------------
| Total memory              |   0x00000 - 0x3FFFF   |
| Boolean read-only         |   0x00000 - 0x0FFFF   |
| Boolean read-write        |   0x10000 - 0x1FFFF   |
| Word read-only            |   0x20000 - 0x27FFF   |
| Float read-only           |   0x28000 - 0x2FFFF   |
| Word read-write           |   0x30000 - 0x37FFF   |
| Float read-write          |   0x38000 - 0x3FFFF   |
-----------------------------------------------------   

'''

import typing
from sys import stderr
from enum import Enum
from threading import Thread
from socket import socket, AF_INET, SOCK_STREAM, IPPROTO_TCP, SHUT_RDWR
from queue import Queue, Full
from time import sleep
from cmd import Cmd
from typing import Callable, Optional, Union
from netaddr import valid_ipv4
from datetime import datetime
from inquirer import list_input, text as text_input, confirm as confirm_input

# NEFICS imports
from nefics.modules.devicebase import IEDBase
from nefics.protos.iec10x.packets import APDU, APCI, ASDU, CP56Time2a, IO, IO1, IO11, IO13, IO30, IO35, IO36, IO45, IO46, IO49, IO50, IO58, IO59, IO62, IO63, IO100, TYPEID_ASDU, ShortFloat, ScaledValue, VSQ
from nefics.protos.iec10x.enums import ALLOWED_COT
from nefics.protos.iec10x.util import time56
from numpy import isin

# Various constants
IEC104_PORT    : int       = 2404
MAX_LENGTH     : int       = 260   # APCI -> 5, MAX ASDU -> 255
MAX_QUEUE      : int       = 256
SUPPORTED_ASDU : list[int] = [45, 46, 49, 50, 58, 59, 62, 63, 100, 102]

# Definition of timeouts (IEC60870-5-104 section 9.6)
TIMEOUT_T0 : float = 30
TIMEOUT_T1 : float = 15
TIMEOUT_T2 : float = 10
TIMEOUT_T3 : float = 20

# Wait times
EMPTY_WAIT  : float = 1
STOPDT_WAIT : float = 5
DATATR_WAIT : float = 0.40
ICMD_WAIT   : float = 0.10



class ControlledState(Enum):
    STOPPED = 0
    STARTED = 1
    PENDING = 2

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
        self._selected_for_operation : Optional[int] = None # IOA for SBO scheme
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
        for addr in range(0, 0x3FFFF):
            if self._device.check_addr(addr & 0x30000, addr & 0xFFFF, 1):
                self._mem_map.append(addr)

    def _data_transfer(self):
        alive : bool = True
        while self._state == ControlledState.STARTED and alive and not self.terminate:
            try:
                sleep(TIMEOUT_T2)
                for addr in self._mem_map:
                    apdu : APDU = APDU()
                    apdu /= APCI(type=0x00)
                    asdu_type : Optional[int] = None
                    io : Optional[Union[IO30, IO35, IO36]] = None
                    if addr < 0x20000: # Boolean value
                        value = 0x01 if self._device.read_bool(addr) else 0x00 # Determine SPI
                        asdu_type = 0x1e # single-point information with time tag CP56Time2a
                        io = IO30(_sq=0, _number=1, _balanced=False, IOA=addr, SIQ=value, time=time56())
                    elif addr in range(0x20000, 0x28000) or addr in range(0x30000, 0x38000): # Measured value (int)
                        value = self._device.read_word(addr)
                        asdu_type = 0x23 # Measured value, scaled value with time tag CP56Time2a
                        io = IO35(_sq=0, _number=1, _balanced=False, IOA=addr, SVA=value, time=time56())
                    elif addr in range(0x28000, 0x30000) or addr in range(0x38000, 0x40000): # Measured value (float)
                        value = self._device.read_ieee_float(addr)
                        asdu_type = 0x24 # Measured value, short floating point number with time tag CP56Time2a
                        io = IO36(_sq=0, _number=1, _balanced=False, IOA=addr, value=value, time=time56())
                    if asdu_type is not None and io is not None:
                        apdu /= ASDU(
                            type=asdu_type, 
                            VSQ=VSQ(SQ=0, number=1),
                            COT=0x03, # Spontaneous
                            CommonAddress=self._device.guid & 0xFF,
                            IO=[io]
                        )
                        self._send_queue.put(APDU(apdu.build()))
                    sleep(min(DATATR_WAIT, TIMEOUT_T2/len(self._mem_map)))
            except BrokenPipeError:
                alive = False

    def _frame_receiver(self):
        buffer : bytes = b''
        alive : bool = True
        while alive and not self._terminate:
            try:
                buffer = self._sock.recv(MAX_LENGTH)
                if len(buffer) > 0:
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
                else:
                    sleep(EMPTY_WAIT)
            except Full:
                stderr.write(f'ERROR :: Receive queue full\r\n')
                stderr.flush()
                continue
            except (TimeoutError, BrokenPipeError):
                alive = False
                continue
            except AssertionError as e:
                stderr.write(f'ERROR :: {str(e)}\r\n')
                stderr.flush()

                continue

    def _frame_sender(self):
        alive : bool = True
        while alive and not self.terminate:
            try:
                if not self._send_queue.empty():
                    next_apdu : APDU = self._send_queue.get(block=False)
                    if next_apdu['APCI'].type < 3:
                        next_apdu['APCI'].Rx = self.rx
                    if next_apdu['APCI'].type == 0:
                        next_apdu['APCI'].Tx = self.tx
                    self._sock.send(next_apdu.build())
                    self.tx += 1
                elif self._send_queue.empty() and self._state == ControlledState.PENDING:
                    self._state = ControlledState.STOPPED
                else:
                    sleep(DATATR_WAIT)
            except (BrokenPipeError, TimeoutError):
                alive = False
                continue

    def _unknown_parameter(self, apdu : APDU, cot : int):
        # Respond with specific CoT
        asdu : ASDU = apdu['ASDU']
        rasdu : ASDU = ASDU(type=asdu.type, VSQ=asdu.VSQ, COT_flags=0b01, COT=cot, CommonAddress=asdu.CommonAddress, IO=asdu.IO)
        self._send_queue.put(APDU()/APCI(type=0x00)/rasdu, block=True, timeout=TIMEOUT_T2)

    def _handle_IO45_IO58(self, apdu : APDU):
        'Handle C_SC_NA_1 (Single command) and C_SC_TA_1 (Single command with time tag CP56Time2a)'
        select : bool = apdu['ASDU'].IO.SE == 0b1
        scs : bool = apdu['ASDU'].IO.SCS == 0b1
        ioa : int = apdu['ASDU'].IO.IOA
        cot : int
        atype : int
        vsq : VSQ = VSQ(SQ=0, number=1)
        currtime : CP56Time2a = time56()
        cot_flags : int
        if select: # SELECT
            if self._selected_for_operation is not None or ioa not in range(0x10000,0x20000):
                # Check if:
                # - there is a previously selected object for operation
                # - IOA is not in the boolean read-write memory region [0x10000-0x1FFFF]
                cot_flags = 0b01
                cot = 10 # ActTerm
            else:
                cot_flags = 0b00
                cot = 7 # ActCon
                self._selected_for_operation = int(ioa)
        else: # EXECUTE
            if self._selected_for_operation == int(ioa):
                # Correct IOA for operation
                self._device.write_bool(ioa, scs)
                cot_flags = 0b00
                cot = 7 # ActCon
            else:
                cot_flags = 0b01
                cot = 10 # ActTerm
            self._selected_for_operation = None
        if isinstance(apdu['ASDU'].IO, IO45):
            io = IO45(_sq=0, _number=1, _balanced=False, IOA=ioa, SE=int(select), SCS=int(scs))
            atype = 0x2d
        else:
            io = IO58(_sq=0, _number=1, _balanced=False, IOA=ioa, SE=int(select), SCS=int(scs), time=currtime)
            atype = 0x3a
        asdu = ASDU(type=atype, VSQ=vsq, COT_flags=cot_flags, COT=cot, CommonAddress=self._device.guid, IO=io)
        self._send_queue.put(APDU()/APCI(type=0x00)/asdu)

    def _handle_IO46_IO59(self, apdu : APDU):
        'Handle C_DC_NA_1 (Double command) and C_DC_TA_1 (Double command with time tag CP56Time2a)'
        select : bool = apdu['ASDU'].IO.SE == 0b1
        dcs : int = apdu['ASDU'].IO.DCS & 0b11
        ioa : int = apdu['ASDU'].IO.IOA
        cot : int
        atype : int
        vsq : VSQ = VSQ(SQ=0, number=1)
        currtime : CP56Time2a = time56()
        cot_flags : int
        if dcs in [0, 3]: # DCS not permitted
            cot_flags = 0b01 # Negative
            cot = 10 # ActTerm
        else:
            if select: # SELECT
                if self._selected_for_operation is not None or ioa not in range(0x10000, 0x20000):
                    # Check if:
                    # - there is a previously selected object for operation
                    # - IOA is not in the boolean read-write memory region [0x10000-0x1FFFF]
                    cot_flags = 0b01 # Negative
                    cot = 10 # ActTerm
                else:
                    cot_flags = 0b00
                    cot = 7 # ActCon
                    self._selected_for_operation = int(ioa)
            else: # EXECUTE
                if self._selected_for_operation == int(ioa):
                    # Correct IOA for operation
                    self._device.write_bool(ioa, dcs == 2)
                    cot_flags = 0b00
                    cot = 7 # ActCon
                else:
                    cot_flags = 0b01 # Negative
                    cot = 10 # ActTerm
                self._selected_for_operation = None
        if isinstance(apdu['ASDU'].IO, IO46):
            io = IO46(_sq=0, _number=1, _balanced=False, IOA=ioa, SE=int(select), DCS=dcs)
            atype = 0x2e
        else:
            io = IO59(_sq=0, _number=1, _balanced=False, IOA=ioa, SE=int(select), DCS=dcs, time=currtime)
            atype = 0x3b
        asdu = ASDU(type=atype, VSQ=vsq, COT_flags=cot_flags, COT=cot, CommonAddress=self._device.guid, IO=io)
        self._send_queue.put(APDU()/APCI(type=0x00)/asdu)

    def _handle_IO49_IO62(self, apdu : APDU):
        'Handle C_SE_NB_1 (Set-point command, scaled value) and C_SE_TB_1 (Set point command, scaled value with time tag CP56Time2a)'
        select : bool = apdu['ASDU'].IO.SE == 0b1
        value : int = apdu['ASDU'].IO.SVA & 0xFFFF
        ioa : int = apdu['ASDU'].IO.IOA
        cot : int
        atype : int
        vsq : VSQ = VSQ(SQ=0, number=1)
        currtime : CP56Time2a = time56()
        cot_flags : int
        if select: # SELECT
            if self._selected_for_operation is not None or ioa not in range(0x30000, 0x38000):
                # Check if:
                # - there is a previously selected object for operation
                # - IOA is not in the WORD read-write memory region [0x30000-0x37FFF]
                cot_flags = 0b01 # Negative
                cot = 10 # ActTerm
            else:
                cot_flags = 0b00
                cot = 7 # ActCon
                self._selected_for_operation = int(ioa)
        else: # EXECUTE
            if self._selected_for_operation == int(ioa):
                # Correct IOA for operation
                self._device.write_word(ioa, value)
                cot_flags = 0b00
                cot = 7 # ActCon
            else:
                cot_flags = 0b01
                cot = 10 # ActTerm
            self._selected_for_operation = None
        if isinstance(apdu['ASDU'].IO, IO49):
            io = IO49(_sq=0, _number=1, _balanced=False, IOA=ioa, SVA=value, SE=int(select))
            atype=0x31
        else:
            io = IO62(_sq=0, _number=1, _balanced=False, IOA=ioa, SVA=value, SE=int(select), time=currtime)
            atype=0x3e
        asdu = ASDU(type=atype, VSQ=vsq, COT_flags=cot_flags, COT=cot, CommonAddress=self._device.guid, IO=io)
        self._send_queue.put(APDU()/APCI(type=0x00)/asdu)

    def _handle_IO50_IO63(self, apdu : APDU):
        'Handle C_SE_NC_1 (set point command, short floating point number) and C_SE_TC_1 (Set-point command with time tag CP56Time2a, short floating point number)'
        select : bool = apdu['ASDU'].IO.SE == 0b1
        value : float = apdu['ASDU'].IO.value
        ioa : int = apdu['ASDU'].IO.IOA
        cot : int
        cot_flags : int
        atype : int
        vsq : VSQ = VSQ(SQ=0, number=1)
        currtime : CP56Time2a = time56()
        if select: # SELECT
            if self._selected_for_operation is not None or ioa not in range(0x38000, 0x40000):
                # Check if:
                # - there is a previously selected object for operation
                # - IOA is not in the FLOAT read-write memory region [0x38000-0x3FFFF]
                cot_flags = 0b01 # Negative
                cot = 10 # ActTerm
            else:
                cot_flags = 0b00
                cot = 7 # ActCon
                self._selected_for_operation = int(ioa)
        else: # EXECUTE
            if self._selected_for_operation == int(ioa):
                # Correct IOA for operation
                self._device.write_ieee_float(ioa, value)
                cot_flags = 0b00
                cot = 7 # ActCon
            else:
                cot_flags = 0b01
                cot = 10 # ActTerm
            self._selected_for_operation = None
        if isinstance(apdu, IO50):
            io = IO50(_sq=0, _number=1, _balanced=False, IOA=ioa, value=value, SE=int(select))
            atype=0x32
        else:
            io = IO63(_sq=0, _number=1, _balanced=False, IOA=ioa, value=value, SE=int(select), time=currtime)
            atype=0x3F
        asdu = ASDU(type=atype, VSQ=vsq, COT_flags=cot_flags, COT=cot, CommonAddress=self._device.guid, IO=io)
        self._send_queue.put(APDU()/APCI(type=0x00)/asdu)

    def _handle_IO100(self, apdu : APDU):
        'Handle C_IC_NA_1 (Interrogation Command)'
        device = self._device
        asdu : ASDU = apdu['ASDU']
        oio = asdu.IO
        # Add IC (actcon) to the message queue
        rasdu = ASDU(type=100, VSQ=VSQ(SQ=0, number=1), COT_flags=0b00, COT=7, CommonAddress=device.guid & 0xFF, IO=IO100(_sq=0, _number=1, _balanced=False, IOA=0, QOI=oio.QOI))
        self._send_queue.put(APDU()/APCI(type=0x00)/rasdu, block=True, timeout=TIMEOUT_T2)
        sleep(ICMD_WAIT)
        # Add process information
        for addr in self._mem_map:
            asdu_type : Optional[int] = None
            io : Optional[Union[IO1, IO11, IO13]] = None
            if addr < 0x20000: # Boolean value
                value = 0b1 if device.read_bool(addr) else 0b0 # Determine SPI
                asdu_type = 0x01 # Single-point information without time tag
                io = IO1(_sq=0, _number=1, _balanced=False, IOA=addr, SIQ=value)
            elif addr in range(0x20000, 0x28000) or addr in range(0x30000, 0x38000): # Measured value (int)
                value = device.read_word(addr)
                asdu_type = 0x0b # Measured value, scaled value
                io = IO11(_sq=0, _number=1, _balanced=False, IOA=addr, value=ScaledValue(SVA=value))
            elif addr in range(0x28000, 0x30000) or addr in range(0x38000, 0x40000): # Measured value (float)
                value = device.read_ieee_float(addr)
                asdu_type = 0x0d # Measured value, short floating point number
                io = IO13(_sq=0, _number=1, _balanced=False, IOA=addr, value=ShortFloat(value=value))
            if asdu_type is not None and io is not None:
                rasdu = ASDU(type=asdu_type, VSQ=VSQ(SQ=0, number=1), COT=0x14, CommonAddress=device.guid & 0xFF, IO=[io])
                self._send_queue.put(APDU()/APCI(type=0x00)/rasdu, block=True, timeout=TIMEOUT_T2)
            sleep(min(ICMD_WAIT, TIMEOUT_T2/len(self._mem_map)))
        # Add IC (actterm) to the message queue
        rasdu = ASDU(type=100, VSQ=VSQ(SQ=0, number=1), COT_flags=0b00, COT=10, CommonAddress=device.guid & 0xFF, IO=IO100(_sq=0, _number=1, _balanced=False, IOA=0, QOI=oio.QOI))
        self._send_queue.put(APDU()/APCI(type=0x00)/rasdu, block=True, timeout=TIMEOUT_T2)

    def _handle_IO102(self, apdu : APDU):
        'Handle C_RD_NA_1 (Read command)'
        req_addr = apdu['ASDU'].IO.IOA
        device = self._device
        asdu_type : Optional[int] = None
        io : Optional[Union[IO30, IO35, IO36]] = None
        if req_addr < 0x20000: # Boolean value
            value = 0x01 if device.read_bool(req_addr) else 0x00 # Determine SPI
            asdu_type = 0x1e # single-point information with time tag CP56Time2a
            io = IO30(_sq=0, _number=1, _balanced=False, IOA=req_addr, SIQ=value, time=time56())
        elif req_addr in range(0x20000, 0x28000) or req_addr in range(0x30000, 0x38000): # Measured value (int)
            value = device.read_word(req_addr)
            asdu_type = 0x23 # Measured value, scaled value with time tag CP56Time2a
            io = IO35(_sq=0, _number=1, _balanced=False, IOA=req_addr, SVA=value, time=time56())
        elif req_addr in range(0x28000, 0x30000) or req_addr in range(0x38000, 0x40000): # Measured value (float)
            value = device.read_ieee_float(req_addr)
            asdu_type = 0x24 # Measured value, short floating point number with time tag CP56Time2a
            io = IO36(_sq=0, _number=1, _balanced=False, IOA=req_addr, value=value, time=time56())
        if asdu_type is not None and io is not None:
            res_asdu = ASDU(type=asdu_type, VSQ=VSQ(SQ=0, number=1), COT_flags=0b00, COT=5, CommonAddress=device.guid & 0xFF, IO=io)
            self._send_queue.put(APDU()/APCI(type=0x00)/res_asdu, block=True, timeout=TIMEOUT_T2)

    def _handle_iframe(self, apdu : APDU):
        atype : int = apdu['ASDU'].type
        cot : int = apdu['ASDU'].COT
        iframe_handlers : dict[tuple, Callable] = {
            (45, 6) : self._handle_IO45_IO58, # Single command (Act)
            (46 ,6) : self._handle_IO46_IO59, # Double command (Act)
            (49, 6) : self._handle_IO49_IO62, # Set-point command, scaled value (Act)
            (50, 6) : self._handle_IO50_IO63, # Set-point command, short floating point number (Act)
            (58, 6) : self._handle_IO45_IO58, # Single command with time tag CP56Time2a (Act)
            (59, 6) : self._handle_IO46_IO59, # Double command with time tag CP56Time2a (Act)
            (62, 6) : self._handle_IO49_IO62, # Set-point command, scaled value with time tag CP56Time2a (Act)
            (63, 6) : self._handle_IO50_IO63, # Set-point command with time tag CP56Time2a, short floating point number (Act)
            (100, 6) : self._handle_IO100,    # Interrogation command (Act)
            (102, 5) : self._handle_IO102,    # Read command (req)
        }
        if (atype, cot) in iframe_handlers.keys(): 
            iframe_handlers[(atype, cot)](apdu)

    def run(self):
        buffer : APDU = APDU()
        datatr : Optional[Thread] = None
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
                    if self._state == ControlledState.STOPPED:
                        if apci.type == 0x03: # Received a U-frame
                            utype = apci.UType
                            self._send_queue.put(APDU()/APCI(type=0x03, UType=(utype << 1)))
                            if utype == 0x01: # STARTDT
                                self._state = ControlledState.STARTED
                                datatr = Thread(target=self._data_transfer)
                                datatr.start()
                        else:
                            self.terminate = True
                    elif self._state == ControlledState.STARTED:
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
                                    self._state = ControlledState.STOPPED
                                else:
                                    self._state = ControlledState.PENDING
                                if datatr is not None:
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
        
class IEC104CLI(Cmd):
    prompt = '[IEC-104]> '

    def __init__(self, completekey: str = 'tab', stdin: typing.IO[str] | None = None, stdout: typing.IO[str] | None = None):
        super().__init__(completekey, stdin, stdout)
        self._sock : socket
        self._device_map : dict[int, Union[int, bool]] = dict()
        self._device_ca : Optional[int] = None
        self._rth : Thread
        self._sth : Thread
        self._kth : Thread
        self._alive : bool = False
        self._end_conn : bool = True
        self._wait_sbo : bool = False
        self._req_apdu : Optional[APDU] = None
        self._tx : int
        self._rx : int
        self._tx_queue : Queue[APDU] = Queue(maxsize=MAX_QUEUE)

    def _map_io(self, io):
        addr : int = io.IOA
        value : Union[bool, int, None] = None
        if isinstance(io, IO30):
            value = bool(io.SIQ & 0b1)
        elif isinstance(io, IO35):
            value = io.SVA
        elif isinstance(io, IO36):
            value = io.value
        if value is not None:
            self._device_map[addr] = value

    def _receiver(self):
        while self._sth.is_alive():
            try:
                buffer = self._sock.recv(MAX_LENGTH)
                if len(buffer) > 0:
                    apdu : APDU = APDU(buffer)
                    assert apdu.haslayer('APCI'), f'Received unknown data: {buffer}\r\n'
                    if apdu.haslayer('ASDU'):
                        asdu = apdu['ASDU']
                        self._device_ca = asdu.CommonAddress
                        io = asdu.IO
                        if asdu.COT == 5: # Requested
                            self._req_apdu = APDU(apdu.build())
                        elif asdu.COT == 7: # ActCon
                            if isinstance(io, (IO45, IO49, IO50)): # Command confirmation
                                self._wait_sbo = False
                        else:
                            if issubclass(io.__class__, IO):
                                self._map_io(io)
                            elif isinstance(io, list) and all(issubclass(x.__class__, IO) for x in io):
                                for x in io:
                                    self._map_io(x)
                    self._rx += 1
                else:
                    sleep(EMPTY_WAIT)
            except AssertionError as e:
                stderr.write(str(e))
                stderr.flush()
            except BrokenPipeError:
                self._alive = False
            except TimeoutError:
                self._end_conn = True
    
    def _sender(self):
        while self._alive and (not self._end_conn or not self._tx_queue.empty()):
            try:
                if not self._tx_queue.empty():
                    apdu : APDU = self._tx_queue.get()
                    if apdu['APCI'].type == 0:
                        apdu['APCI'].Tx = self._tx
                        self._tx += 1
                    if apdu['APCI'].type < 3:
                        apdu['APCI'].Rx = self._rx
                    self._sock.send(apdu.build())
                else:
                    sleep(EMPTY_WAIT)
            except (BrokenPipeError, TimeoutError):
                self._alive = False
                self._end_conn = True

    def _keep_alive(self):
        while self._alive and not self._end_conn:
            self._tx_queue.put(APDU()/APCI(type=0x03, UType=0x10))
            sleep(TIMEOUT_T2)
            
    def do_disconnect(self, arg : Optional[str]):
        try:
            assert self._alive
            print(f'Stopping data transmission ...', end=' ')
            self._tx_queue.put(APDU()/APCI(type=0x03, UType=0x04), block=False)
            sleep(STOPDT_WAIT)
            print('OK')
            print(f'Closing connection ...', end=' ')
            self._end_conn = True
            if self._sth.is_alive():
                self._sth.join()
            if self._rth.is_alive():
                self._rth.join()
            if self._kth.is_alive():
                self._kth.join()
            self._sock.shutdown(SHUT_RDWR)
            self._sock.close()
            print('OK')
            self._alive = False
            self._wait_sbo = False
            self._req_apdu = None
            print(f'Clearing memory mappings ...', end=' ')
            self._device_map = dict()
            self._device_ca = None
            print('OK')
        except (AssertionError, OSError):
            stderr.write(f'Not connected.\n')
            stderr.flush()
    
    def do_connect(self, arg : str):
        try:
            assert len(arg) > 7, f'{arg} is too short to contain an IPv4 address\r\n'
            argl : list[str] = arg.split()
            addr = argl[0]
            assert valid_ipv4(addr), f'{addr} is not a valid IPv4 address\r\n'
            port = argl[1] if len(argl) > 1 else IEC104_PORT
            if self._alive:
                # The socket is already connected
                print(f'Already connected to: {str(self._sock.getpeername())}')
            else:
                # Not connected
                self._sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
                self._sock.connect((addr, port))
                self._sock.settimeout(TIMEOUT_T1)
                print(f'Connected to: {str(self._sock.getpeername())}')
                print(f'Starting sender/receiver threads ...', end=' ')
                self._rx = 0
                self._tx = 0
                self._alive = True
                self._end_conn = False
                self._sth = Thread(target=self._sender)
                self._rth = Thread(target=self._receiver)
                self._kth = Thread(target=self._keep_alive)
                self._sth.start()
                self._rth.start()
                print('OK')
                print(f'Starting data transmission ...', end=' ')
                self._tx_queue.put(APDU()/APCI(type=0x03, UType=0x01), block=False)
                sleep(STOPDT_WAIT)
                print(f'OK')
                self._kth.start()
        except AssertionError as e:
            stderr.write(str(e))
            stderr.flush()
        except TimeoutError:
            stderr.write(f'Connection timeout\n')
            stderr.flush()
    
    def do_status(self, arg : Optional[str]):
        try:
            assert self._alive
            assert isinstance(self._device_ca, int)
            print(f'Connected to: {str(self._sock.getpeername())}')
            print(f'Status at {datetime.now().ctime()}:\r\n')
            print(f'Common address: {self._device_ca:02x}')
            print(f'Rx: {self._rx:3d}\tTx: {self._tx:3d}')
            print('IOA\tValue')
            print(16*'=')
            for k, v in self._device_map.items():
                if isinstance(v, bool):
                    val = 'ON' if v else 'OFF'
                else:
                    val = v
                print(f'{k}\t{val}')
            print(16*'=')
        except (OSError, AssertionError):
            print(f'Not connected')
    
    def do_control(self, arg : Optional[str]):
        try:
            assert self._alive, f'Not connected'
            assert isinstance(self._device_ca, int), f'No device Common Address'
            ioas : list[int] = [x for x in self._device_map.keys() if x in range(0x10000,0x20000) or x in range(0x30000,0x40000)]
            ioa = list_input('Which IO would you like to control?', choices=ioas)
            val : Union[int, bool, str, float] = self._device_map[ioa]
            io : Union[IO45, IO49, IO50] # Single command (45), Set-point command: word(49) / float(50)
            if isinstance(val, bool):
                # Boolean RW -> Single command
                print(f'IO: {ioa:6d} Status: {"ON" if val else "OFF"}')
                if confirm_input('Toggle the current IO value?'):
                    print(f'Selecting IO {ioa:6d} for operation')
                    io = IO45(_sq=0, _number=1, _balanced=False,
                        IOA=ioa,                        # IO address
                        SE=1,                           # SELECT (1)
                        SCS=int(not val)                # Toggle current value
                    )
                    asdu : ASDU = ASDU(
                        type=0x2d,                      # 0x2D: C_SC_NA_1 (45)
                        VSQ=VSQ(SQ=0, number=1),        # SQ=Single, Number=1 IO
                        COT=6,                          # Act
                        CommonAddress=self._device_ca,  # Device Common Address
                        IO=io                           # IO
                    )
                    apdu : APDU = APDU()/APCI(type=0x00)/asdu # APCI Type 0x00 (I-Frame)
                    self._wait_sbo = True
                    self._tx_queue.put(apdu)
                    while self._wait_sbo:
                        print(f'\rAwaiting confirmation...', end='')
                        sleep(DATATR_WAIT)
                    print(f'SELECTED\n')
                    io = IO45(_sq=0, _number=1, _balanced=False,
                        IOA=ioa,                        # IO address
                        SE=0,                           # EXECUTE (1)
                        SCS=int(not val)                # Toggle current value
                    )
                    asdu = ASDU(
                        type=0x2d,                      # 0x2D: C_SC_NA_1 (45)
                        VSQ=VSQ(SQ=0, number=1),        # SQ=Single, Number=1 IO
                        COT=6,                          # Act
                        CommonAddress=self._device_ca,  # Device Common Address
                        IO=io                           # IO
                    )
                    apdu = APDU()/APCI(type=0x00)/asdu  # APCI Type 0x00 (I-Frame)
                    self._wait_sbo = True
                    self._tx_queue.put(apdu)
                    while self._wait_sbo:
                        print(f'\rExecuting command...', end='')
                        sleep(DATATR_WAIT)
                    print('Done')
            else:
                # Word/Float RW -> Set-point command
                print(f'IO: {ioa:6d} Value: {val}')
                val = text_input('Enter the new value')
                assert isinstance(val, str), f'Incorrect value: {val}'
                val = val.strip()
                val = float(val) if '.' in val else int(val) & 0xFFFF
                print(f'Selecting IO {ioa:6d} for operation')
                if isinstance(val, float):
                    io = IO50(_sq=0, _number=1, _balanced=False,
                        IOA=ioa,                        # IO Address
                        value=val,                      # New value
                        SE=1                            # SELECT (1)
                    )
                    asdu = ASDU(
                        type=0x32,                      # 0x32: C_SE_NC_1 (50)
                        VSQ=VSQ(SQ=0, number=1),        # SQ=Single, Number=1 IO
                        COT=6,                          # Act
                        CommonAddress=self._device_ca,  # Device Common Address
                        IO=io                           # IO
                    )
                else:
                    io = IO49(_sq=0, _number=1, _balanced=False,
                        IOA=ioa,                        # IO Address
                        SVA=val,                        # New value
                        SE=1                            # SELECT(1)
                    )
                    asdu = ASDU(
                        type=0x31,                      # 0x31: C_SE_NB_1 (49)
                        VSQ=VSQ(SQ=0, number=1),        # SQ=Single, Number=1 IO
                        COT=6,                          # Act
                        CommonAddress=self._device_ca,  # Device Common Address
                        IO=io                           # IO
                    )
                apdu = APDU()/APCI(type=0x00)/asdu      # APCI Type 0x00 (I-Frame)
                self._wait_sbo = True
                self._tx_queue.put(apdu)
                while self._wait_sbo:
                    print(f'\rAwaiting confirmation...', end='')
                    sleep(DATATR_WAIT)
                print(f'SELECTED\n')
                if isinstance(val, float):
                    io = IO50(_sq=0, _number=1, _balanced=False,
                        IOA=ioa,                        # IO Address
                        value=val,                      # New value
                        SE=0                            # EXECUTE (0)
                    )
                    asdu = ASDU(
                        type=0x32,                      # 0x32: C_SE_NC_1 (50)
                        VSQ=VSQ(SQ=0, number=1),        # SQ=Single, Number=1 IO
                        COT=6,                          # Act
                        CommonAddress=self._device_ca,  # Device Common Address
                        IO=io                           # IO
                    )
                else:
                    io = IO49(_sq=0, _number=1, _balanced=False,
                        IOA=ioa,                        # IO Address
                        SVA=val,                        # New value
                        SE=0                            # EXECUTE (0)
                    )
                    asdu = ASDU(
                        type=0x31,                      # 0x31: C_SE_NB_1 (49)
                        VSQ=VSQ(SQ=0, number=1),        # SQ=Single, Number=1 IO
                        COT=6,                          # Act
                        CommonAddress=self._device_ca,  # Device Common Address
                        IO=io                           # IO
                    )
                apdu = APDU()/APCI(type=0x00)/asdu      # APCI Type 0x00 (I-Frame)
                self._wait_sbo = True
                self._tx_queue.put(apdu)
                while self._wait_sbo:
                    print(f'\rExecuting command...', end='')
                    sleep(DATATR_WAIT)
                print('Done')
        except ValueError:
            print(f'Incorrect value: {val}')
        except (AssertionError, OSError) as e:
            print(str(e))
    
    def do_exit(self, arg : Optional[str]):
        return True
    
    def do_EOF(self, arg : Optional[str]):
        print('')
        return True

if __name__ == '__main__':
    from sys import exit
    ieccli : IEC104CLI = IEC104CLI()
    try:
        ieccli.cmdloop()
    except KeyboardInterrupt:
        ieccli.do_disconnect(None)
        exit(0)

