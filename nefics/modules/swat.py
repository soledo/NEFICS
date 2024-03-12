#!/usr/bin/env python3
# Based on the Secure Water Treatment (SWaT) testbed, which is used
# by Singapore University of Technology and Design (SUTD)’s
# researcher and students in the context of Cyber-Physical systems
# security research.

from dataclasses import dataclass, astuple
from datetime import datetime
from enum import Enum
from netaddr import valid_ipv4
from threading import Thread
from time import sleep
from typing import Optional, Union
# NEFICS imports
from nefics.modules.devicebase import FLOAT16_SCALE, DeviceBase, DeviceHandler
from nefics.protos.modbus import ModbusListener, ModbusClient
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

class SWaTProcessDevice(DeviceBase):

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

    def __init__(self, *args, device: SWaTProcessDevice, **kwargs):
        super().__init__(*args, device, **kwargs)

    def status(self):
        stat = (
            f'### SWaT Physical Process Handler\r\n'
            f' ## Class: {self._device.__class__.__name__}\r\n'
            f'  # Status at: {datetime.now().ctime()}\r\n\r\n'
            f'{str(self._device)}'
        )
        print(stat)

class SWaTMemMappings(Enum):
    # Coils
    MV101  = 0x10101
    P101   = 0x11101
    P201   = 0x11201
    P301   = 0x11301
    # Input Registers
    LIT101 = 0x20101
    LIT301 = 0x20301
    FIT101 = 0x21101
    FIT201 = 0x21201
    PH201  = 0x22201

class PLCDevice(DeviceBase):
    
    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        assert 'paddr' in kwargs.keys()
        assert isinstance(kwargs['paddr'], str)
        assert valid_ipv4(kwargs['paddr'])
        # Physical process pseudo-device IP address
        self._phys_addr = (kwargs['paddr'], SIM_PORT)

    def __str__(self):
        output = '=' * 10 + '\r\n'
        for k in self._memory.keys():
            value = self.read_bool(k) if k in range(0x20000) else self.read_word(k)
            output += f'[@0x{k:05x}] = {value}\r\n'
        output += '=' * 10 + '\r\n'
        return super().__str__() + output

    # Physical process I/O - NEFICS
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

    
class PLCHandler(DeviceHandler):

    def __init__(self, *args, device: PLCDevice, **kwargs):
        super().__init__(*args, device, **kwargs)
        self._device : PLCDevice = device
        self._connections = list[Thread]()

    def status(self):
        stat = (
            f'### SWaT PLC Handler\r\n'
            f' ## Class: {self._device.__class__.__name__}\r\n'
            f'  # Status at: {datetime.now().ctime()}\r\n\r\n'
            f'{str(self._device)}'
        )
        print(stat)

    def run(self):
        self._device.start()
        modbus_listener : ModbusListener = ModbusListener(device=self._device)
        modbus_listener.start()
        modbus_listener.join()
        self._device.join()

class PLC1(PLCDevice):

    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        assert guid == SWAT_IDS['PLC1']
        assert 'p3addr' in kwargs.keys()
        assert isinstance(kwargs['p3addr'], str)
        assert valid_ipv4(kwargs['p3addr'])
        assert isinstance(SWAT_IDS['PLC3'], int)
        self._plc3_ip = kwargs['p3addr']
        # Memory mappings
        self._memory[SWaTMemMappings.MV101.value] = int(False)
        self._memory[SWaTMemMappings.P101.value] = int(True)
        self._memory[SWaTMemMappings.LIT101.value] = 5000 # 0.5 * 10000. The register holds 2 bytes as a short int (0-65535)
        self._memory[SWaTMemMappings.FIT101.value] = 0
        # PLC3 communications channel
        self._p3_id : int = SWAT_IDS['PLC3']
        self._p3 : ModbusClient = ModbusClient(ipaddr=self._plc3_ip)
        self._p3.connect()
    
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
        request.IntegerArg1 = int(self.read_bool(SWaTMemMappings.MV101.value))
        self._sock.sendto(request.build(), self._phys_addr)
        sleep(0.1)
        request.IntegerArg0 = PHYS_IDS['P101']
        request.IntegerArg1 = int(self.read_bool(SWaTMemMappings.P101.value))
        self._sock.sendto(request.build(), self._phys_addr)
    
    def handle_specific(self, message: simproto.NEFICSMSG):
        if message.SenderID == SWAT_IDS['PHYS'] and message.ReceiverID == self.guid and message.MessageID == simproto.MESSAGE_ID['MSG_VAL']:
            # PLC1 should only receive values from 'LIT101' and 'FIT101'
            phys_id = message.IntegerArg0
            value = message.FloatArg0
            assert isinstance(phys_id, int) and phys_id in PHYS_IDS.keys()
            assert isinstance(value, float)
            if phys_id in [PHYS_IDS['LIT101'], PHYS_IDS['FIT101']]:
                address = SWaTMemMappings.LIT101.value if phys_id == PHYS_IDS['LIT101'] else SWaTMemMappings.FIT101.value
                self.write_word(address, int(value * FLOAT16_SCALE)) # Float to short int
    
    def simulate(self):
        # Request FIT101 and LIT101 from the physical process
        self._query_values()
        # Request LIT301 value from PLC3
        lit301 = float(self._p3.read_input_word(SWaTMemMappings.LIT301.value, unit=self._p3_id)) / FLOAT16_SCALE
        # Control logic
        lit101 = float(self.read_word(SWaTMemMappings.LIT101.value)) / FLOAT16_SCALE # Value from short int to float
        if lit101 >= LIT_101_M['HH'] or lit101 >= LIT_101_M['H']:
            self.write_bool(SWaTMemMappings.MV101.value, False)
        elif lit101 <= LIT_101_M['L'] or lit101 <= LIT_101_M['LL']:
            self.write_bool(SWaTMemMappings.MV101.value, True)
        if lit301 >= LIT_301_M['HH'] or lit301 >= LIT_301_M['H']:
            self.write_bool(SWaTMemMappings.P101.value, False)
        elif lit301 <= LIT_301_M['L'] or lit301 <= LIT_301_M['LL']:
            self.write_bool(SWaTMemMappings.P101.value, True)
        # Commit changes to physical process
        self._update_values()
        sleep(PROCESS_TIMEOUT_S)

class PLC2(PLCDevice):

    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        assert guid == SWAT_IDS['PLC2']
        # Memory mappings
        self._memory[SWaTMemMappings.FIT201.value] = int(PUMP_FLOWRATE_OUT * FLOAT16_SCALE) # Float to short int
        self._memory[SWaTMemMappings.PH201.value] = 7000 # Float to short int
        self._memory[SWaTMemMappings.P201.value] = int(False)
    
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
        request.IntegerArg1 = self.read_word(SWaTMemMappings.P201.value)
        self._sock.sendto(request.build(), self._phys_addr)
        sleep(0.1)
    
    def handle_specific(self, message: simproto.NEFICSMSG):
        if message.SenderID == SWAT_IDS['PHYS'] and message.ReceiverID == self.guid and message.MessageID == simproto.MESSAGE_ID['MSG_VAL']:
            # PLC2 should only receive values from 'FIT201' and 'PH201'
            phys_id = message.IntegerArg0
            value = message.FloatArg0
            assert isinstance(phys_id, int)
            assert isinstance(value, float)
            if phys_id in [PHYS_IDS['FIT201'], PHYS_IDS['PH201']]:
                address = SWaTMemMappings.FIT201.value if phys_id == PHYS_IDS['FIT201'] else SWaTMemMappings.PH201.value
                self.write_word(address, int(value * FLOAT16_SCALE)) # Float to short int
    
    def simulate(self):
        # Request FIT201 and PH201 from the physical process
        self._query_values()
        # Control logic
        ph201 = float(self.read_word(SWaTMemMappings.PH201.value)) / FLOAT16_SCALE # Value from short int to float
        if ph201 >= PH_201_M['HH'] or ph201 >= PH_201_M['H']:
            self.write_bool(SWaTMemMappings.P201.value, False)
        if ph201 <= PH_201_M['LL'] or ph201 <= PH_201_M['L']:
            self.write_bool(SWaTMemMappings.P201.value, True)
        # Commit changes to physical process
        self._update_values()
        sleep(PROCESS_TIMEOUT_S)

class PLC3(PLCDevice):

    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        assert guid == SWAT_IDS['PLC3']
        # Memory mappings
        self._memory[SWaTMemMappings.LIT301.value] = 5000
        self._memory[SWaTMemMappings.P301.value] = int(False)
    
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
        request.IntegerArg1 = int(self.read_bool(SWaTMemMappings.P301.value))
        self._sock.sendto(request.build(), self._phys_addr)
        sleep(0.1)
    
    def handle_specific(self, message: simproto.NEFICSMSG):
        if message.SenderID == SWAT_IDS['PHYS'] and message.ReceiverID == self.guid and message.MessageID == simproto.MESSAGE_ID['MSG_VAL']:
            # PLC3 should only receive values from 'LIT301'
            phys_id = message.IntegerArg0
            if phys_id == PHYS_IDS['LIT301']:
                value = message.FloatArg0
                self.write_word(SWaTMemMappings.LIT301.value, int(value * FLOAT16_SCALE)) # Float to short int
    
    def simulate(self):
        # Request LIT301
        self._query_values()
        # Control logic
        lit301 = float(self.read_word(SWaTMemMappings.LIT301.value)) / FLOAT16_SCALE # Value from short int to float
        if lit301 >= LIT_301_M['HH'] or lit301 >= LIT_301_M['H']:
            self.write_bool(SWaTMemMappings.P301.value, True)
        if lit301 <= LIT_301_M['LL'] or lit301 <= LIT_301_M['L']:
            self.write_bool(SWaTMemMappings.P301.value, False)
        # Commit changes to physical process
        self._update_values()
        sleep(PROCESS_TIMEOUT_S)
