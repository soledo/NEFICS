#!/usr/bin/env python3
# Based on the Secure Water Treatment (SWaT) testbed, which is used
# by Singapore University of Technology and Design (SUTD)’s
# researcher and students in the context of Cyber-Physical systems
# security research.

from dataclasses import dataclass, astuple
from datetime import datetime
from enum import Enum
from math import ceil
from netaddr import valid_ipv4
from random import randint
from numpy import isin
from scapy.contrib.modbus import * # MODBUS TCP
from socket import AF_INET, IPPROTO_TCP, SOCK_STREAM, socket, timeout
from threading import Thread
from time import sleep
from typing import Optional, Union
# NEFICS imports
from nefics.modules.devicebase import FLOAT16_SCALE, IEDBase, DeviceHandler
import nefics.protos.simproto as simproto

# Custom simproto definitions
simproto.MESSAGE_ID['MSG_GET'] = 6                  # Get physical value
simproto.MESSAGE_ID['MSG_SET'] = 7                  # Set physical value
simproto.MESSAGE_ID['MSG_VAL'] = 8                  # Requested value
simproto.MESSAGE_ID['MSG_DND'] = 0xFFFFFFFD         # Request denied
simproto.MESSAGE_ID_MAP[0x00000006] = 'MSG_GET'
simproto.MESSAGE_ID_MAP[0x00000007] = 'MSG_SET'
simproto.MESSAGE_ID_MAP[0x00000008] = 'MSG_VAL'
simproto.MESSAGE_ID_MAP[0xFFFFFFFD] = 'MSG_DND'
# Integer arg0 -> Variable identifier
# (Integer arg1 / Float arg0) -> values (boolean / float)
# e.g.: 0300000004000000070000000300000001000000000000000000 -> [PLC3|PHYS|MSG_SET|P301|ON|-|-]

from nefics.protos.simproto import NEFICSMSG, SIM_PORT
MESSAGE_ID = simproto.MESSAGE_ID
MESSAGE_ID_MAP = simproto.MESSAGE_ID_MAP

# General device GUIDs
SWAT_IDS : dict[Union[str, int], Union[str, int]] = {
    'PLC1': 1,
    'PLC2': 2,
    'PLC3': 3,
    'PHYS': 4,
    1: 'PLC1',
    2: 'PLC2',
    3: 'PLC3',
    4: 'PHYS',
}

# Physical status variable mapping
PHYS_IDS : dict[Union[str, int], Union[str, int]] = {
    'MV101': 0,
    'P101': 1,
    'P201': 2,
    'P301': 3,
    'LIT101': 4,
    'LIT301': 5,
    'FIT101': 6,
    'FIT201': 7,
    'PH201': 8,
    0: 'MV101',
    1: 'P101',
    2: 'P201',
    3: 'P301',
    4: 'LIT101',
    5: 'LIT301',
    6: 'FIT101',
    7: 'FIT201',
    8: 'PH201',
}

# Physical process definitions
TANK_DIAMETER        : float = 1.38                                             # [m]
TANK_HEIGHT          : float = 1.600                                            # [m]
TANK_SECTION         : float = 1.5                                              # [m^2]
PUMP_FLOWRATE_IN     : float = 2.55                                             # [m^3/h] spec say between 2.2 and 2.4 ?
PUMP_FLOWRATE_OUT    : float = 2.45                                             # [m^3/h] spec say between 2.2 and 2.4 ?
PH_PUMP_FLOWRATE_IN  : float = 0.7
PH_PUMP_FLOWRATE_OUT : float = 0.7
RESCALING_HOURS      : float = 100
PROCESS_TIMEOUT_S    : float = 0.20                                             # physical process update rate in seconds
PROCESS_TIMEOUT_H    : float = (PROCESS_TIMEOUT_S / 3600.0) * RESCALING_HOURS
PH_PERIOD_SEC        : float = 0.05
PH_PERIOD_HOURS      : float = (PH_PERIOD_SEC / 3600.0) * RESCALING_HOURS

# Control logic thresholds
LIT_101_MM = {      # raw water tank [mm]
    'LL': 250.0,
    'L': 500.0,
    'H': 800.0,
    'HH': 1200.0,
}
LIT_101_M = {       # raw water tank [m]
    'LL': 0.250,
    'L': 0.500,
    'H': 0.800,
    'HH': 1.200,
}
LIT_301_MM = {      # ultrafiltration tank [mm]
    'LL': 250.0,
    'L': 800.0,
    'H': 1000.0,
    'HH': 1200.0,
}
LIT_301_M = {       # ultrafiltration tank [m]
    'LL': 0.250,
    'L': 0.800,
    'H': 1.000,
    'HH': 1.200,
}
PH_201_M = {
	'LL': 0.50,
	'L': 0.700,
	'H': 0.800,
	'HH': 1.000
}

MB_MAX_LEN = 260
'''
MODBUS PDU Size

RS232 / RS485 ADU = 253 bytes + Server address (1 byte) + CRC (2 bytes) = 256 bytes

TCP MODBUS ADU = 253 bytes + MBAP (7 bytes) = 260 bytes
'''

MB_WR_COIL_VAL = {
    0x0000: False,
    0xff00: True
}

@dataclass
class PhysicalStatus(object):
    '''
    Dataclass containing the physical information of the system
    '''

    mv101:  bool  = False  # Motorized valve 101 status (ON/OFF)
    p101:   bool  = False  # Pump 101 status (ON/OFF)
    p201:   bool  = False  # Pump 201 [Chemical dispenser] (ON/OFF)
    p301:   bool  = False  # Pump 301 status (ON/OFF)
    lit101: float = 0.0    # Level indicator 101 [m]
    lit301: float = 0.0    # Level indicator 301 [m]
    fit101: float = 0.0    # Flow level indicator 101 [m^3/h]
    fit201: float = 0.0    # Flow level indicator 201 [m^3/h]
    ph201:  float = 0.0    # pH level indicator

    def __str__(self):
        output = (
            f'{"=" * 15}\r\n'
            f' MV101: {"   [ON]" if self.mv101  else "  [OFF]"}\r\n'
            f'  P101: {"   [ON]" if self.p101   else "  [OFF]"}\r\n'
            f'  P201: {"   [ON]" if self.p201   else "  [OFF]"}\r\n'
            f'  P301: {"   [ON]" if self.p301   else "  [OFF]"}\r\n'
            f'LIT101: {self.lit101:2.7f}\r\n'
            f'LIT301: {self.lit301:2.7f}\r\n'
            f'FIT101: {self.fit101:2.7f}\r\n'
            f'FIT201: {self.fit201:2.7f}\r\n'
            f' PH201: {self.ph201:2.7f}\r\n'
            f'{"=" * 15}\r\n'
        )
        return output

class SWaTProcessDevice(IEDBase):

    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        assert SWAT_IDS[guid] == 'PHYS' # This is the physical process simulation
        assert 'plc' in kwargs.keys()
        assert isinstance(kwargs['plc'], dict)
        assert all(isinstance(x, str) for x in kwargs['plc'].keys())
        assert all(isinstance(x, str) for x in kwargs['plc'].values())
        assert all(valid_ipv4(x) for x in kwargs['plc'].values())
        # A dictionary containing the IP addresses of the PLCs indexed by the GUID of the device. See SWAT_IDS ^^^
        self._plc_ip = dict[int, str]()
        pplc:dict[str, str] = kwargs['plc']
        for k in pplc.keys():
            self._plc_ip[int(k)] = pplc[k]
        # Initial simulation values
        self._status = PhysicalStatus(
            mv101 = False,                  # OFF
            p101 = True,                    # ON
            p201 = False,                   # OFF
            p301 = False,                   # OFF
            lit101 = 0.500,                 # [m]
            lit301 = 0.500,                 # [m]
            fit101 = 0.0,                   # [m^3/h]
            fit201 = PUMP_FLOWRATE_OUT,     # [m^3/h]
            ph201 = 0.7                     # pH
        )
    
    def __str__(self) -> str:
        return str(self._status)

    def simulate(self):
        # Tank T101 (PLC1)
        t101 = self._status.lit101 # Current tank level [m]
        water_volume = t101 * TANK_SECTION
        water_volume += (PUMP_FLOWRATE_IN * PROCESS_TIMEOUT_H) if self._status.mv101 else 0.0
        self._status.fit101 = PUMP_FLOWRATE_IN if self._status.mv101 else 0.0
        water_volume -= (PUMP_FLOWRATE_OUT * PROCESS_TIMEOUT_H) if self._status.p101 else 0.0
        self._status.fit201 = PUMP_FLOWRATE_OUT if self._status.p101 else 0.0
        t101 = water_volume / TANK_SECTION
        t101 = 0.0 if t101 <= 0.0 else t101
        self._status.lit101 = t101 # Updated level [m]

        # pH changes (PLC2)
        self._status.ph201 += PH_PUMP_FLOWRATE_IN * PH_PERIOD_HOURS if self._status.p201 else (-1.0 * (PH_PUMP_FLOWRATE_OUT * PH_PERIOD_HOURS))
        
        # Tank T301 (PLC3)
        t301 = self._status.lit301 # Current tank level [m]
        water_volume = t301 * TANK_SECTION
        water_volume += (PUMP_FLOWRATE_OUT * PROCESS_TIMEOUT_H) if self._status.p101 else 0.0
        water_volume -= (PUMP_FLOWRATE_OUT * PROCESS_TIMEOUT_H) if self._status.p301 else 0.0
        t301 = water_volume / TANK_SECTION
        t301 = 0.0 if t301 <= 0.0 else t301
        self._status.lit301 = t301 # Updated level [mm]

        sleep(PROCESS_TIMEOUT_S)

    def handle_specific(self, message: NEFICSMSG):
        if message.SenderID in self._plc_ip.keys() and message.SenderID in SWAT_IDS.keys() and message.ReceiverID == self.guid and message.IntegerArg0 in PHYS_IDS.keys():
            addr = self._plc_ip[message.SenderID]
            mid = message.MessageID
            sender = SWAT_IDS[message.SenderID]
            request = PHYS_IDS[message.IntegerArg0]
            pkt : Optional[NEFICSMSG]
            pkt = NEFICSMSG(SenderID=self.guid, ReceiverID=message.SenderID)
            assert isinstance(addr, str)
            assert isinstance(mid, int)
            assert isinstance(request, str)
            assert isinstance(sender, str)
            allowed_get : list[str] = list()
            allowed_set : list[str] = list()
            # Check privileges
            if sender == 'PLC1':
                # PLC1 is allowed to control: MV101, P101
                # PLC1 is allowed to request: MV101, P101, LIT101, FIT101
                allowed_get += ['MV101', 'P101', 'LIT101', 'FIT101']
                allowed_set += ['MV101', 'P101']
            elif sender == 'PLC2':
                # PLC2 is allowed to control: P201
                # PLC2 is allowed to request: P201, FIT201, PH201
                allowed_get += ['PH201', 'FIT201', 'P201']
                allowed_set += ['P201']
            elif sender == 'PLC3':
                # PLC3 is allowed to control: P301
                # PLC3 is allowed to request: P301, LIT301
                allowed_get += ['P301', 'LIT301']
                allowed_set += ['P301']
            # Check operation
            if mid == MESSAGE_ID['MSG_GET'] and request in allowed_get:
                status_idx = PHYS_IDS[request]
                assert isinstance(status_idx, int)
                pkt.IntegerArg0 = status_idx
                pkt.MessageID = MESSAGE_ID['MSG_VAL']
                value = astuple(self._status)[status_idx]
                value = value if isinstance(value, float) else int(value)
                if isinstance(value, int):
                    pkt.IntegerArg1 = value
                else:
                    pkt.FloatArg0 = value
            elif mid == MESSAGE_ID['MSG_SET'] and request in allowed_set:
                if request == 'MV101':
                    self._status.mv101 = bool(message.IntegerArg1)
                elif request == 'P101':
                    self._status.p101 = bool(message.IntegerArg1)
                elif request == 'P201':
                    self._status.p201 = bool(message.IntegerArg1)
                elif request == 'P301':
                    self._status.p301 = bool(message.IntegerArg1)
                pkt = None
            else:
                self.log(f'Access denied for {sender}: {request}')
                pkt.MessageID = MESSAGE_ID['MSG_DND']
            # If necessary, send response packet
            if pkt is not None:
                self._sock.sendto(pkt.build(), (addr, SIM_PORT))

class SWaTProcessHandler(DeviceHandler):

    def __init__(self, device: SWaTProcessDevice):
        super().__init__(device)

    def status(self):
        stat = (
            f'### SWaT Physical Process Handler\r\n'
            f' ## Class: {self._device.__class__.__name__}\r\n'
            f'  # Status at: {datetime.now().ctime()}\r\n\r\n'
            f'{str(self._device)}'
        )
        print(stat)
    
class ModbusDatamap(Enum):
    
    DI=1
    CO=2
    IR=3
    HR=4

    def __str__(self):
        STR_MAP = {1: 'Discrete Input', 2: 'Coil', 3: 'Input Register', 4: 'Holding Register'}
        return STR_MAP[self._value_]

PDU_REQ_MAPPING = {
    ModbusDatamap.CO: ModbusPDU01ReadCoilsRequest,
    ModbusDatamap.DI: ModbusPDU02ReadDiscreteInputsRequest,
    ModbusDatamap.HR: ModbusPDU03ReadHoldingRegistersRequest,
    ModbusDatamap.IR: ModbusPDU04ReadInputRegistersRequest
}

# Memory mappings for MODBUS
PHYS_MODBUS = {
    'MV101' : (ModbusDatamap.CO, 0x0101),
    'P101'  : (ModbusDatamap.CO, 0x1101),
    'P201'  : (ModbusDatamap.CO, 0x1201),
    'P301'  : (ModbusDatamap.CO, 0x1301),
    'LIT101': (ModbusDatamap.IR, 0x0101),
    'LIT301': (ModbusDatamap.IR, 0x0301),
    'FIT101': (ModbusDatamap.IR, 0x1101),
    'FIT201': (ModbusDatamap.IR, 0x1201),
    'PH201' : (ModbusDatamap.IR, 0x2201),
}

class PLCDevice(IEDBase):
    
    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        assert 'paddr' in kwargs.keys()
        assert isinstance(kwargs['paddr'], str)
        assert valid_ipv4(kwargs['paddr'])
        # Physical process pseudo-device IP address
        self._phys_addr = (kwargs['paddr'], SIM_PORT)
        # MODBUS Device Identification
        self._mb_vname = kwargs['vendor_name'] if 'vendor_name' in kwargs.keys() and isinstance(kwargs['vendor_name'], str) else 'NEFICS'
        self._mb_pcode = kwargs['product_code'] if 'product_code' in kwargs.keys() and isinstance(kwargs['product_code'], str) else 'SWaT PLC'
        self._mb_mmrev = kwargs['mm_revision'] if 'mm_revision' in kwargs.keys() and isinstance(kwargs['mm_revision'], str) else 'v1.0'
        # MODBUS data model
        self._di_map = dict[int, bool]()
        self._co_map = dict[int, bool]()
        self._ir_map = dict[int, int]()
        self._hr_map = dict[int, int]()

    def __str__(self):
        output = '=' * 40 + '\r\n'
        for k in PHYS_MODBUS.keys():
            dmap, addr = PHYS_MODBUS[k]
            if self.check_addr(dmap, addr, 1):
                value = self._get_memory_value(k)
                output += f'{k:6s}: [{str(dmap):16s}@0x{addr:04x}] = {value}\r\n'
        output += '=' * 40 + '\r\n'
        return output

    # Physical process I/O
    def _request_value(self, id: int):
        assert id in PHYS_IDS.keys()
        request = NEFICSMSG(SenderID=self.guid, ReceiverID=SWAT_IDS['PHYS'], MessageID=MESSAGE_ID['MSG_GET'], IntegerArg0=id)
        self._sock.sendto(request.build(), self._phys_addr)
    
    def _set_value(self, id: int, value: int):
        assert id in PHYS_IDS.keys()
        idstr = PHYS_IDS[id]
        assert idstr in ['MV101', 'P101', 'P201', 'P301']
        request = NEFICSMSG(SenderID=self.guid, ReceiverID=SWAT_IDS['PHYS'], MessageID=MESSAGE_ID['MSG_SET'], IntegerArg0=id, IntegerArg1=value)
        self._sock.sendto(request.build(), self._phys_addr)

    # MODBUS I/O
    def read_bool(self, dmap: ModbusDatamap, address: int) -> bool:
        assert dmap in [ModbusDatamap.DI, ModbusDatamap.CO]
        data_map = self._di_map if dmap == ModbusDatamap.DI else self._co_map
        assert address in range(65536)
        assert address in data_map.keys()
        return data_map[address]
    
    def read_word(self, dmap: ModbusDatamap, address: int) -> int:
        assert dmap in [ModbusDatamap.HR, ModbusDatamap.IR]
        data_map = self._hr_map if dmap == ModbusDatamap.HR else self._ir_map
        assert address in range(65536)
        assert address in data_map.keys()
        return data_map[address]
    
    def write_coil(self, address: int, value: bool):
        assert address in range(65536)
        assert address in self._co_map.keys()
        self._co_map[address] = value

    def write_holding_register(self, address: int, value: int):
        assert address in range(65536)
        assert address in self._hr_map.keys()
        assert value in range(65536)
        self._hr_map[address] = value

    def check_addr(self, datamap: ModbusDatamap, address: int, quantity: int) -> bool:
        try:
            assert address in range(65535)
            if datamap == ModbusDatamap.CO:
                map = self._co_map
            elif datamap == ModbusDatamap.DI:
                map = self._di_map
            elif datamap == ModbusDatamap.HR:
                map = self._hr_map
            else:
                map = self._ir_map
            assert all(a in map.keys() for a in range(address, address + quantity))
            return True
        except AssertionError:
            return False

    def _set_memory_value(self, tag:str, value: Union[int, bool]):
        # Internal method for setting values in the memory map
        assert tag in PHYS_MODBUS.keys()
        datamap, address = PHYS_MODBUS[tag]
        assert address in range(65536)
        if datamap == ModbusDatamap.CO:
            assert isinstance(value, bool)
            self._co_map[address] = value
        elif datamap == ModbusDatamap.DI:
            assert isinstance(value, bool)
            self._di_map[address] = value
        elif datamap == ModbusDatamap.HR:
            assert isinstance(value, int)
            assert value in range(65536)
            self._hr_map[address] = value
        else:
            assert isinstance(value, int)
            assert value in range(65536)
            self._ir_map[address] = value

    def _get_memory_value(self, tag:str) -> Union[int, bool]:
        # Internal method for getting values from the memory map
        assert tag in PHYS_MODBUS.keys()
        datamap, address = PHYS_MODBUS[tag]
        assert address in range(65536)
        if datamap == ModbusDatamap.CO:
            return self._co_map[address]
        elif datamap == ModbusDatamap.DI:
            return self._di_map[address]
        elif datamap == ModbusDatamap.HR:
            return self._hr_map[address]
        else:
            return self._ir_map[address]

    def _build_mb_request_single(self, tag:str) -> ModbusADURequest:
        request = ModbusADURequest(transId=randint(1,65535))
        dmap, address = PHYS_MODBUS[tag]
        request /= PDU_REQ_MAPPING[dmap](startAddr=address, quantity=1)
        return request

class PLCHandler(DeviceHandler):

    def __init__(self, device: PLCDevice):
        super().__init__(device)
        self._device = device
        self._connections = list[Thread]()

    def status(self):
        stat = (
            f'### SWaT PLC Handler\r\n'
            f' ## Class: {self._device.__class__.__name__}\r\n'
            f'  # Status at: {datetime.now().ctime()}\r\n\r\n'
            f'{str(self._device)}'
        )
        print(stat)

    def _modbus_loop(self, sock: socket):
        connection_alive = True
        while connection_alive and not self._terminate:
            # MODBUS server transaction loop
            # Based on the definitions presented in "MODBUS Messaging on TCP/IP Implementation Guide V1.0b"
            # https://modbus.org/docs/Modbus_Messaging_Implementation_Guide_V1_0b.pdf
            try:
                # Wait for a MB indication
                data = sock.recv(MB_MAX_LEN)
                request = ModbusADURequest(data)
                reqpdu = request.payload
                try:
                    # Check MBAP Header
                    assert all(x in request.fields for x in ['transId', 'protoId', 'len', 'unitId'])
                    assert request.protoId == 0x0000    # MODBUS
                    assert request.unitId == 0xff       # MODBUS TCP ignores unit ID, must be 0xFF
                except AssertionError:
                    # Error on MBAP => MB Indication discarded
                    continue
                transaction_id = request.transId
                try:
                    # Validate the function code
                    assert not isinstance(reqpdu, ModbusPDUUserDefinedFunctionCodeRequest)
                except AssertionError:
                    # Illegal function code
                    rawpdu = bytes(reqpdu)
                    function_code = (int(rawpdu[0]) + 0x80) & 0xff if rawpdu[0] < 0x80 else rawpdu[0] # The response function code = the request function code + 0x80
                    # Exception Response with code 0x01
                    response = ModbusADUResponse(transId=transaction_id)/bytes([function_code, 0x01])
                    sock.send(response.build())
                    continue
                function_code = reqpdu.funcCode
                response = ModbusADUResponse(transId=transaction_id)
                values : list[Union[int, str]]
                # MODBUS Indication processing
                if function_code in [0x01, 0x02]:
                    # Read coils request / Read Discrtete Input Request
                    address:int = reqpdu.startAddr
                    quantity:int = reqpdu.quantity
                    datamap:ModbusDatamap = ModbusDatamap.CO if function_code == 0x01 else ModbusDatamap.DI
                    if not (0x0001 <= quantity and quantity <= 0x07d0): # Validate quantity. Up to 2000 according to protocol specs
                        # Exception Response with code 0x03
                        response /= ModbusPDU01ReadCoilsError(exceptCode=0x03) if function_code == 0x01 else ModbusPDU02ReadDiscreteInputsError(exceptCode=0x03)
                    elif not self._device.check_addr(datamap, address, quantity): # Validate addresses. All addresses must be mapped in the device
                        # Exception Response with code 0x02
                        response /= ModbusPDU01ReadCoilsError(exceptCode=0x02) if function_code == 0x01 else ModbusPDU02ReadDiscreteInputsError(exceptCode=0x02)
                    else:
                        # Read coil/discrete input values
                        try:
                            coils = 0
                            for a in range(address + quantity - 1, address - 1, -1):
                                coils += 1 if self._device.read_bool(datamap, a) else 0
                                coils <<= 1
                            status = []
                            while coils > 0:
                                status.append(coils & 0xff)
                                coils >>= 8
                            response /= ModbusPDU01ReadCoilsResponse(coilStatus=status) if function_code == 0x01 else ModbusPDU02ReadDiscreteInputsResponse(inputStatus=status)
                        except AssertionError:
                            # Exception Response with code 0x04
                            response /= ModbusPDU01ReadCoilsError(exceptCode=0x04) if function_code == 0x01 else ModbusPDU02ReadDiscreteInputsError(exceptCode=0x04)
                elif function_code in [0x03, 0x04]:
                    # Read Holding Registers / Input Registers
                    address:int = reqpdu.startAddr
                    quantity:int = reqpdu.quantity
                    datamap:ModbusDatamap = ModbusDatamap.HR if function_code == 0x03 else ModbusDatamap.IR
                    if not (0x0001 <= quantity and quantity <= 0x7d): # Validate quantity. Up to 125 according to protocol specs
                        # Exception Response with code 0x03
                        response /= ModbusPDU03ReadHoldingRegistersError(exceptCode=0x03) if function_code == 0x03 else ModbusPDU04ReadInputRegistersError(exceptCode=0x03)
                    elif not self._device.check_addr(datamap, address, quantity): # Validate addresses. All addresses must be mapped in the device
                        # Exception Response with code 0x02
                        response /= ModbusPDU03ReadHoldingRegistersError(exceptCode=0x02) if function_code == 0x03 else ModbusPDU04ReadInputRegistersError(exceptCode=0x02)
                    else:
                        try:
                            # Read register values
                            values = [self._device.read_word(datamap, a) for a in range(address, address + quantity, 1)]
                            response /= ModbusPDU03ReadHoldingRegistersResponse(registerVal=values) if function_code == 0x03 else ModbusPDU04ReadInputRegistersResponse(registerVal=values)
                        except AssertionError:
                            # Exception Response with code 0x04
                            response /= ModbusPDU03ReadHoldingRegistersError(exceptCode=0x04) if function_code == 0x03 else ModbusPDU04ReadInputRegistersError(exceptCode=0x04)
                elif function_code == 0x05:
                    # Write Single Coil Request
                    address:int = reqpdu.outputAddr
                    value:int = reqpdu.outputValue
                    if value not in MB_WR_COIL_VAL.keys(): # Value is not 'ON' (0xFF00) or 'OFF' (0x0000)
                        # Exception Response with code 0x03
                        response /= ModbusPDU05WriteSingleCoilError(exceptCode=0x03)
                    elif not self._device.check_addr(ModbusDatamap.CO, address, 1): # Validate address
                        # Exception Response with code 0x02
                        response /= ModbusPDU05WriteSingleCoilError(exceptCode=0x02)
                    else:
                        try:
                            self._device.write_coil(address, MB_WR_COIL_VAL[value])
                            response /= ModbusPDU05WriteSingleCoilResponse(outputAddr=address, outputValue=value)
                        except AssertionError:
                            # Exception Response with code 0x04
                            response /= ModbusPDU05WriteSingleCoilError(exceptCode=0x04)
                elif function_code == 0x06:
                    # Write Single Register
                    address:int = reqpdu.registerAddr
                    value:int = reqpdu.registerValue
                    if not self._device.check_addr(ModbusDatamap.HR, address, 1): # Validate address
                        # Exception Response with code 0x02
                        response /= ModbusPDU06WriteSingleRegisterError(exceptCode=0x02)
                    else:
                        try:
                            self._device.write_holding_register(address, value)
                            response /= ModbusPDU06WriteSingleRegisterResponse(registerAddr=address, registerValue=value)
                        except AssertionError:
                            # Exception Response with code 0x04
                            response /= ModbusPDU06WriteSingleRegisterError(exceptCode=0x04)
                elif function_code in [0x07, 0x08, 0x0b, 0x0c, 0x11]:
                    # Serial line only - No MODBUS TCP
                    # Exception Response with code 0x01
                    if function_code == 0x07:
                        response /= ModbusPDU07ReadExceptionStatusError(exceptCode=0x01)
                    elif function_code == 0x08:
                        response /= ModbusPDU08DiagnosticsError(exceptCode=0x01)
                    elif function_code == 0x0b:
                        response /= ModbusPDU0BGetCommEventCounterError(exceptCode=0x01)
                    elif function_code == 0x0c:
                        response /= ModbusPDU0CGetCommEventLogError(exceptCode=0x01)
                    else:
                        response /= ModbusPDU11ReportSlaveIdError(exceptCode=0x01)
                elif function_code == 0x0f:
                    # Write Multiple Coils Request
                    address:int = reqpdu.startAddr
                    quantity:int = reqpdu.quantityOutput
                    count:int = reqpdu.byteCount
                    values = reqpdu.outputsValue
                    if not ((0x0001 <= quantity and quantity <= 0x07b0) and count == ceil(float(quantity) / 8.0)): # Validate quantity
                        # Exception Response with code 0x03
                        response /= ModbusPDU0FWriteMultipleCoilsError(exceptCode=0x03)
                    elif not self._device.check_addr(ModbusDatamap.CO, address, quantity): # Validate addresses. All addresses must be mapped in the device
                        # Exception Response with code 0x02
                        response /= ModbusPDU0FWriteMultipleCoilsError(exceptCode=0x02)
                    else:
                        try:
                            coilvals = 0
                            assert isinstance(values, list)
                            assert all(x.__class__ == int for x in values)
                            while len(values):
                                coilvals <<= 8
                                coilvals += int(values.pop())
                            for offset in range(quantity):
                                self._device.write_coil(address + offset, bool(coilvals & 0b1))
                                coilvals >>= 1
                            response /= ModbusPDU0FWriteMultipleCoilsResponse(startAddr=address, quantityOutput=quantity)
                        except AssertionError:
                            # Exception Response with code 0x04
                            response /= ModbusPDU0FWriteMultipleCoilsError(exceptCode=0x04)
                elif function_code == 0x10:
                    # Write Multiple Registers Request
                    address:int = reqpdu.startAddr
                    quantity:int = reqpdu.quantityRegisters
                    count:int = reqpdu.byteCount
                    values = reqpdu.outputsValue
                    if not ((0x0001 <= quantity and quantity <= 0x007b) and count == (quantity * 2) and count == len(values)): # Validate quantity
                        # Exception Response with code 0x03
                        response /= ModbusPDU10WriteMultipleRegistersError(exceptCode=0x03)
                    elif not self._device.check_addr(ModbusDatamap.HR, address, quantity): # Validate addresses. All addresses must be mapped in the device
                        # Exception Response with code 0x02
                        response /= ModbusPDU10WriteMultipleRegistersError(exceptCode=0x02)
                    else:
                        try:
                            assert isinstance(values, list)
                            assert all(isinstance(x, int) for x in values)
                            for offset in range(quantity):
                                self._device.write_holding_register(address + offset, int(values[offset]))
                            response /= ModbusPDU10WriteMultipleRegistersResponse(startAddr=address, quantityRegisters=quantity)
                        except AssertionError:
                            # Exception Response with code 0x04
                            response /= ModbusPDU10WriteMultipleRegistersError(exceptCode=0x04)
                elif function_code in [0x014, 0x015]:
                    # We are not supporting File Records R/W. Respond with "Busy" Exception
                    response /= ModbusPDU14ReadFileRecordError(exceptCode=0x06) if function_code == 0x15 else ModbusPDU15WriteFileRecordError(exceptCode=0x06)
                elif function_code == 0x16:
                    # Mask Write Register Request
                    address:int = reqpdu.refAddr
                    andmask:int = reqpdu.andMask
                    ormask:int = reqpdu.orMask
                    if not self._device.check_addr(ModbusDatamap.HR, address, 1): # Validate Address
                        # Exception Response with code 0x02
                        response /= ModbusPDU16MaskWriteRegisterError(exceptCode=0x02)
                    try:
                        current = self._device.read_word(ModbusDatamap.HR, address)
                        self._device.write_holding_register(address, ((current & andmask) | (ormask and (andmask ^ 0xffff))) & 0xffff)
                        response /= ModbusPDU16MaskWriteRegisterResponse(refAddr=address, andMask=andmask, orMask=ormask)
                    except AssertionError:
                        # Exception Response with code 0x04
                        response /= ModbusPDU16MaskWriteRegisterError(exceptCode=0x04)
                elif function_code == 0x17:
                    # Read/Write Multiple registers Request
                    rd_address:int = reqpdu.readStartingAddr
                    rd_quantity:int = reqpdu.readQuantityRegisters
                    wr_address:int = reqpdu.writeStartingAddress
                    wr_quantity:int = reqpdu.writeQuantityRegisters
                    count:int = reqpdu.byteCount
                    wr_values:list[int] = reqpdu.writeRegistersValue
                    if not (0x0001 <= rd_quantity and rd_quantity <= 0x7d and 0x0001 <= wr_quantity and wr_quantity <= 0x0079 and count == (wr_quantity * 2)): # Validate quantities
                        # Exception Response with code 0x03
                        response /= ModbusPDU17ReadWriteMultipleRegistersError(exceptCode=0x03)
                    elif not (self._device.check_addr(ModbusDatamap.HR, rd_address, rd_quantity) and self._device.check_addr(ModbusDatamap.HR, wr_address, wr_quantity)): # Validate addresses. All addresses must be mapped in the device
                        # Exception Response with code 0x02
                        response /= ModbusPDU17ReadWriteMultipleRegistersError(exceptCode=0x02)
                    else:
                        try:
                            # Read register values
                            values = [self._device.read_word(ModbusDatamap.HR, a) for a in range(rd_address, rd_address + rd_quantity, 1)]
                            # Write register values
                            for offset in range(wr_quantity):
                                self._device.write_holding_register(wr_address + offset, wr_values[offset])
                            response /= ModbusPDU17ReadWriteMultipleRegistersResponse(registerVal=values)
                        except AssertionError:
                            # Exception Response with code 0x04
                            response /= ModbusPDU17ReadWriteMultipleRegistersError(exceptCode=0x04)
                elif function_code == 0x18:
                    # Read FIFO Queue Request
                    fifo:int = reqpdu.FIFOPointerAddr
                    if not self._device.check_addr(ModbusDatamap.HR, fifo, 1): # Validate FIFO pointer address
                        # Exception Response with code 0x02
                        response /= ModbusPDU18ReadFIFOQueueError(exceptCode=0x02)
                    try:
                        count = self._device.read_word(ModbusDatamap.HR, fifo)
                        if count > 31:
                            # Exception Response with code 0x03
                            response /= ModbusPDU18ReadFIFOQueueError(exceptCode=0x03)
                        elif not self._device.check_addr(ModbusDatamap.HR, fifo + 1, count): # Validate queue addresses
                            # Exception Response with code 0x02
                            response /= ModbusPDU18ReadFIFOQueueError(exceptCode=0x02)
                        else:
                            # Read queue
                            values = [self._device.read_word(ModbusDatamap.HR, fifo + offset) for offset in range(1, count + 1)]
                            response /= ModbusPDU18ReadFIFOQueueResponse(FIFOCount=count, FIFOVal=values)
                    except AssertionError:
                        # Exception Response with code 0x04
                        response /= ModbusPDU18ReadFIFOQueueError(exceptCode=0x04)
                else:
                    # Read Device Identification Request
                    readcode:int = reqpdu.readCode
                    objectid:int = reqpdu.objectId
                    if not (0x01 <= readcode and readcode <= 0x04):
                        # Exception Response with code 0x03
                        response /= ModbusPDU2B0EReadDeviceIdentificationError(exceptCode=0x03)
                    elif readcode < 0x04:
                        respdu = ModbusPDU2B0EReadDeviceIdentificationResponse(readCode=readcode, conformityLevel=0x83, objCount=3)
                        respdu/= ModbusObjectId(id=0x00, value=self._device._mb_vname)
                        respdu/= ModbusObjectId(id=0x01, value=self._device._mb_pcode)
                        respdu/= ModbusObjectId(id=0x02, value=self._device._mb_mmrev)
                        response /= respdu
                    elif objectid not in [0, 1, 2]:
                        # Object not supported
                        # Exception Response with code 0x02
                        response /= ModbusPDU2B0EReadDeviceIdentificationError(exceptCode=0x02)
                    else:
                        respdu = ModbusPDU2B0EReadDeviceIdentificationResponse(readCode=readcode, conformityLevel=0x83, objCount=1)
                        values = [self._device._mb_vname, self._device._mb_pcode, self._device._mb_mmrev]
                        respdu/= ModbusObjectId(id=objectid, value=values[objectid])
                        response /= respdu
                sock.send(response.build())
            except (timeout, BrokenPipeError) as ex:
                # Socket timeout or disconnection
                connection_alive = False
        sock.close()

    def run(self):
        listening_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        listening_sock.bind(('', 502)) # Modbus TCP
        listening_sock.settimeout(2) 
        listening_sock.listen()
        self._device.start()
        while not self._terminate:
            try:
                incoming, iaddr = listening_sock.accept()
                incoming.settimeout(60) # There is no standard timeout for Modbus, we'll allow a minute
                new_conn = Thread(target=self._modbus_loop, args=[incoming])
                self._connections.append(new_conn)
                new_conn.start()
            except timeout:
                continue
        while any(thr.is_alive() for thr in self._connections):
            for thr in self._connections:
                thr.join(1)
        self._device.join()
        listening_sock.close()

class PLC1(PLCDevice):

    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        assert guid == SWAT_IDS['PLC1']
        assert 'p3addr' in kwargs.keys()
        assert isinstance(kwargs['p3addr'], str)
        assert valid_ipv4(kwargs['p3addr'])
        self._plc3_ip = kwargs['p3addr']
        # Memory mappings
        self._set_memory_value('MV101', False)
        self._set_memory_value('P101', True)
        self._set_memory_value('LIT101', 5000) # 0.5 * 10000. The register holds 2 bytes as a short int (0-65535)
        self._set_memory_value('FIT101', 0)
        # PLC3 socket
        self._p3 = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        self._p3.connect((self._plc3_ip, 502)) # MODBUS
        self._p3.settimeout(1)
    
    def _query_values(self):
        # From physical process
        request = simproto.NEFICSMSG(SenderID=self.guid, ReceiverID=SWAT_IDS['PHYS'], MessageID=simproto.MESSAGE_ID['MSG_GET'])
        request.IntegerArg0 = PHYS_IDS['LIT101']
        self._sock.sendto(request.build(), self._phys_addr)
        sleep(0.1)
        request.IntegerArg0 = PHYS_IDS['FIT101']
        self._sock.sendto(request.build(), self._phys_addr)
        sleep(0.1)
    
    def _update_values(self):
        # To physical process
        request = simproto.NEFICSMSG(SenderID=self.guid, ReceiverID=SWAT_IDS['PHYS'], MessageID=simproto.MESSAGE_ID['MSG_SET'])
        request.IntegerArg0 = PHYS_IDS['MV101']
        request.IntegerArg1 = int(self._get_memory_value('MV101'))
        self._sock.sendto(request.build(), self._phys_addr)
        sleep(0.1)
        request.IntegerArg0 = PHYS_IDS['P101']
        request.IntegerArg1 = int(self._get_memory_value('P101'))
        self._sock.sendto(request.build(), self._phys_addr)
    
    def handle_specific(self, message: simproto.NEFICSMSG):
        if message.SenderID == SWAT_IDS['PHYS'] and message.ReceiverID == self.guid and message.MessageID == simproto.MESSAGE_ID['MSG_VAL']:
            # PLC1 should only receive values from 'LIT101' and 'FIT101'
            phys_id = message.IntegerArg0
            value = message.FloatArg0
            tag = PHYS_IDS[phys_id]
            assert isinstance(phys_id, int)
            assert isinstance(tag, str)
            assert isinstance(value, float)
            if phys_id in [PHYS_IDS['LIT101'], PHYS_IDS['FIT101']]:
                self._set_memory_value(tag, int(value * FLOAT16_SCALE)) # Float to short int
    
    def simulate(self):
        # Request FIT101 and LIT101 from the physical process
        self._query_values()
        # Request LIT301 value from PLC3
        request = self._build_mb_request_single('LIT301')
        self._p3.send(request.build())
        data = self._p3.recv(1024)
        if len(data):
            response = ModbusADUResponse(data)
        # Control logic
        lit101 = float(self._get_memory_value('LIT101')) / FLOAT16_SCALE # Value from short int to float
        if lit101 >= LIT_101_M['HH'] or lit101 >= LIT_101_M['H']:
            self._set_memory_value('MV101', False)
        if lit101 <= LIT_101_M['L'] or lit101 <= LIT_101_M['LL']:
            self._set_memory_value('MV101', True)
        if len(data) and 'registerVal' in response.payload.fields: # Modbus PDU response with register value (holding/input)
            lit301 = float(response.payload.registerVal[0]) / FLOAT16_SCALE  # Value from short int to float
            if lit301 >= LIT_301_M['HH'] or lit301 >= LIT_301_M['H']:
                self._set_memory_value('P101', False)
            if lit301 <= LIT_301_M['L'] or lit301 <= LIT_301_M['LL']:
                self._set_memory_value('P101', True)
        elif 'exceptCode' in response.payload.fields: # Modbus Exception
            self.log('MODBUS Exception while requesing LIT301 value')
        # Commit changes to physical process
        self._update_values()
        sleep(PROCESS_TIMEOUT_S)

class PLC2(PLCDevice):

    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        assert guid == SWAT_IDS['PLC2']
        # Memory mappings
        self._set_memory_value('FIT201', int(PUMP_FLOWRATE_OUT * FLOAT16_SCALE))  # Float to short int
        self._set_memory_value('PH201', 7000)                               # Float to short int
        self._set_memory_value('P201', False)
    
    def _query_values(self):
        # From physical process
        request = simproto.NEFICSMSG(SenderID=self.guid, ReceiverID=SWAT_IDS['PHYS'], MessageID=simproto.MESSAGE_ID['MSG_GET'])
        request.IntegerArg0 = PHYS_IDS['FIT201']
        self._sock.sendto(request.build(), self._phys_addr)
        sleep(0.1)
        request.IntegerArg0 = PHYS_IDS['PH201']
        self._sock.sendto(request.build(), self._phys_addr)
        sleep(0.1)
    
    def _update_values(self):
        # To physical process
        request = simproto.NEFICSMSG(SenderID=self.guid, ReceiverID=SWAT_IDS['PHYS'], MessageID=simproto.MESSAGE_ID['MSG_SET'])
        request.IntegerArg0 = PHYS_IDS['P201']
        request.IntegerArg1 = int(self._get_memory_value('P201'))
        self._sock.sendto(request.build(), self._phys_addr)
        sleep(0.1)
    
    def handle_specific(self, message: simproto.NEFICSMSG):
        if message.SenderID == SWAT_IDS['PHYS'] and message.ReceiverID == self.guid and message.MessageID == simproto.MESSAGE_ID['MSG_VAL']:
            # PLC2 should only receive values from 'FIT201' and 'PH201'
            phys_id = message.IntegerArg0
            value = message.FloatArg0
            tag = PHYS_IDS[phys_id]
            assert isinstance(phys_id, int)
            assert isinstance(value, float)
            assert isinstance(tag, str)
            if phys_id in [PHYS_IDS['FIT201'], PHYS_IDS['PH201']]:
                self._set_memory_value(tag, int(value * FLOAT16_SCALE)) # Float to short int
    
    def simulate(self):
        # Request FIT201 and PH201 from the physical process
        self._query_values()
        # Control logic
        ph201 = float(self._get_memory_value('PH201')) / FLOAT16_SCALE # Value from short int to float
        if ph201 >= PH_201_M['HH'] or ph201 >= PH_201_M['H']:
            self._set_memory_value('P201', False)
        if ph201 <= PH_201_M['LL'] or ph201 <= PH_201_M['L']:
            self._set_memory_value('P201', True)
        # Commit changes to physical process
        self._update_values()
        sleep(PROCESS_TIMEOUT_S)

class PLC3(PLCDevice):

    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        assert guid == SWAT_IDS['PLC3']
        # Memory mappings
        self._set_memory_value('LIT301', 5000)
        self._set_memory_value('P301', False)
    
    def _query_values(self):
        # From physical process
        request = simproto.NEFICSMSG(SenderID=self.guid, ReceiverID=SWAT_IDS['PHYS'], MessageID=simproto.MESSAGE_ID['MSG_GET'])
        request.IntegerArg0 = PHYS_IDS['LIT301']
        self._sock.sendto(request.build(), self._phys_addr)
        sleep(0.1)
    
    def _update_values(self):
        # To physical process
        request = simproto.NEFICSMSG(SenderID=self.guid, ReceiverID=SWAT_IDS['PHYS'], MessageID=simproto.MESSAGE_ID['MSG_SET'])
        request.IntegerArg0 = PHYS_IDS['P301']
        request.IntegerArg1 = int(self._get_memory_value('P301'))
        self._sock.sendto(request.build(), self._phys_addr)
        sleep(0.1)
    
    def handle_specific(self, message: simproto.NEFICSMSG):
        if message.SenderID == SWAT_IDS['PHYS'] and message.ReceiverID == self.guid and message.MessageID == simproto.MESSAGE_ID['MSG_VAL']:
            # PLC3 should only receive values from 'LIT301'
            phys_id = message.IntegerArg0
            if phys_id == PHYS_IDS['LIT301']:
                value = message.FloatArg0
                self._set_memory_value('LIT301', int(value * FLOAT16_SCALE)) # Float to short int
    
    def simulate(self):
        # Request LIT301
        self._query_values()
        # Control logic
        lit301 = float(self._get_memory_value('LIT301')) / FLOAT16_SCALE # Value from short int to float
        if lit301 >= LIT_301_M['HH'] or lit301 >= LIT_301_M['H']:
            self._set_memory_value('P301', True)
        if lit301 <= LIT_301_M['LL'] or lit301 <= LIT_301_M['L']:
            self._set_memory_value('P301', False)
        # Commit changes to physical process
        self._update_values()
        sleep(PROCESS_TIMEOUT_S)
