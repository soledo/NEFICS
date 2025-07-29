#!/usr/bin/env python3

# Standard imports
import subprocess
import os
from enum import Enum
from time import sleep
from datetime import datetime
from threading import Thread
from typing import Union, Callable

# NEFICS imports
from nefics.modules.devicebase import DeviceBase, DeviceHandler, ProtocolListener, LOG_PRIO
from nefics.protos import http, modbus

# Globals

SYNC_TIMER : float = 0.05
LOOP_TIMER : float = SYNC_TIMER * 2.0

# Honeypot base classes

class HoneyDevice(DeviceBase):
    # Will only hold the honeyd configuration
    
    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        assert 'honeyconf' in kwargs.keys()
        assert os.path.exists(kwargs['honeyconf'])
        self._honeyconf = kwargs.pop('honeyconf')
        super().__init__(guid=guid, neighbors_in=neighbors_in, neighbors_out=neighbors_out, **kwargs)
    
    @property
    def honeyconf(self) -> str:
        return self._honeyconf

class HoneyHandler(DeviceHandler):
    
    def __init__(self, *args, device: HoneyDevice, **kwargs):
        super().__init__(*args, device=device, **kwargs)
        self._device = device
        check_honey = subprocess.call(['which', 'honeyd'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
        if check_honey != 0:
            raise FileNotFoundError(2, 'Cannot find executable', 'honeyd')
        self._process : Union[subprocess.Popen, None] = None
    
    def _respawn(self):
        if isinstance(self._process, subprocess.Popen):
            self._process.kill()
            self._process = None
        fingerprint_file = 'conf/honeypot_fingerprints.txt'
        cmd = ['honeyd', '-d', '-i', 'honeypot-eth0', '-f', self._device.honeyconf]
        if os.path.exists(fingerprint_file):
            cmd.extend(['-p', fingerprint_file])
        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    
    def status(self):
        status = (
            f'### Honeyd process handler\r\n'
            f' ## Configuration: {self._device.honeyconf}\r\n'
            f'  # Status at: {datetime.now().ctime()}\r\n\r\n'
            f'{"Running..." if isinstance(self._process, subprocess.Popen) and self._process.poll() is None else "Terminated... trying to respawn"}\r\n'
        )
        print(status)
    
    def run(self):
        while not self._terminate:
            retcode = self._process.poll() if isinstance(self._process, subprocess.Popen) else 0
            if retcode is not None:
                # Process terminated, respawning
                self._respawn()
            sleep(5)
        if isinstance(self._process, subprocess.Popen):
            self._process.terminate()
            self._process.wait(20)

# Scenario-agnostic PLC device and handler

class PLCDevice(DeviceBase):

    def __init__(self, *args, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        # Extract PLC-specific parameters before calling super().__init__
        assert 'phys_ip' in kwargs.keys() and isinstance(kwargs['phys_ip'], str), f'Physical process simulation IP address is missing ([phys_ip] directive not found).'
        self._html : Union[str, None] = kwargs.pop('html', None) if 'html' in kwargs else None
        self._httpsrv = kwargs.pop('httpsrv', None) if 'httpsrv' in kwargs else None
        self._protocols : Union[list[str], None] = kwargs.pop('protos', None) if 'protos' in kwargs else None
        self._phys_ip = kwargs.pop('phys_ip')
        # Remove other PLC-specific parameters that shouldn't go to DeviceBase
        for key in ['info']:
            kwargs.pop(key, None)
        super().__init__(guid=guid, neighbors_in=neighbors_in, neighbors_out=neighbors_out, **kwargs)
    
    @property
    def httpsrv_header(self) -> str:
        return self._httpsrv if self._httpsrv is not None else 'NEFICS/1.0'
    
    @property
    def html_path(self) -> str:
        return self._html if self._html is not None else ''
    
    @property
    def protocols(self) -> Union[list[str], None]:
        return self._protocols
    
    def __str__(self) -> str:
        devicestr : str = (
            f'    ### Emulated PLC Device\r\n'
            f'     ## Module: {self.__class__.__module__}\r\n'
            f'     ## Class:  {self.__class__.__name__}\r\n'
            f'      # Configured device information:\r\n\r\n'
            f'        Vendor name:  {self._vendor_name}\r\n'
            f'        Product code: {self._product_code}\r\n'
            f'        Revision:     {self._revision}\r\n'
            f'        Device name:  {self._device_name}\r\n'
            f'        Device model: {self._device_model}\r\n\r\n'
        )
        return devicestr

class PLCHandler(DeviceHandler):

    def __init__(self, *args, device: PLCDevice, **kwargs):
        super().__init__(device=device, **kwargs)
        self._device : PLCDevice = device
        self._protocols : dict[str, ProtocolListener] = dict()

    def status(self):
        stat = (
            f'### Honeypot PLC Handler\r\n'
            f' ## Class: {self._device.__class__.__name__}\r\n'
            f'  # Status at: {datetime.now().ctime()}\r\n\r\n'
            f'{str(self._device)}\r\n\r\n'
            f'  # Protocol listeners:\r\n'
        )
        for p in self._protocols.keys():
            stat += f'    {p.upper()}: {"LISTENING" if self._protocols[p].is_alive() else "DOWN"}\r\n'
        print(stat)

    def _start_http(self):
        try:
            hpath = self._device.html_path
            assert len(hpath)
            assert os.path.exists(hpath)
            assert os.path.isdir(hpath)
            listener : ProtocolListener = http.HTTPListener(server_header=self._device.httpsrv_header, static_dir=hpath)
            self._protocols['http'] = listener
            listener.start()
        except AssertionError:
            self._device.log(message='Could not instantiate HTTP server.', prio=LOG_PRIO['WARNING'])

    def _start_modbus(self):
        listener : ProtocolListener = modbus.ModbusListener(device=self._device)
        self._protocols['modbus'] = listener
        listener.start()

    def run(self):
        self._device.start()
        if self._device.protocols is not None:
            protocol_handlers : dict[str, Callable]= {
                'http' : self._start_http,
                'modbus' : self._start_modbus
            }
            for protocol in self._device.protocols:
                if protocol.lower() in protocol_handlers.keys():
                    protocol_handlers[protocol]()
                else:
                    self._device.log(message=f'Unknown protocol: {protocol}', prio=LOG_PRIO['WARNING'])
        while not self._terminate:
            # Dummy loop
            sleep(1)
        while any(thr.is_alive() for thr in self._protocols.values()):
            for thr in self._protocols.values():
                if thr.is_alive():
                    thr.terminate = True
                    thr.join(1)
        self._device.join()

# Scenario #1 - Water tank

class WaterTankPLCMemMapping(Enum):
    TANK_LVL  = 0x20000
    SET_POINT = 0x30000
    VALVE_IN  = 0x30001
    VALVE_OUT = 0x30002

class WaterTankPhysMemMapping(Enum):
    # FactoryIO Modbus Mapping
    # -- Input Registers --
    TANK_LVL  = 0x0001
    # -- Holding Registers --
    VALVE_IN  = 0x0000
    VALVE_OUT = 0x0001

class WaterTankPLC(PLCDevice):

    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        # Extract WaterTank-specific parameters
        assert 'set_point' in kwargs.keys() and isinstance(kwargs['set_point'], float), f'Missing set point ([set_point] directive not found)'
        assert kwargs['set_point'] > 0.0 and kwargs['set_point'] < 3.0, f'Set point out of range'
        set_point_value = kwargs.pop('set_point')
        # Extract slave_id (default to 1 for backward compatibility)
        self._slave_id = kwargs.pop('slave_id', 1)
        super().__init__(guid=guid, neighbors_in=neighbors_in, neighbors_out=neighbors_out, **kwargs)
        set_point : int = int((1000.0 * set_point_value) / 3.0) # Set point (HR) [0-1000] <-> [0-3m]
        self._memory[WaterTankPLCMemMapping.TANK_LVL.value] = 0 # Water level meter (IR) [0-1000] <-> [0-3m]
        self._memory[WaterTankPLCMemMapping.SET_POINT.value] = set_point  # Remove & 0xff to store full value
        self._memory[WaterTankPLCMemMapping.VALVE_IN.value] = 0 # Valve in (HR) [0-1000] <-> [0-100%]
        self._memory[WaterTankPLCMemMapping.VALVE_OUT.value] = 0 # Valve out (HR) [0-1000] <-> [0-100%]
        
    def __str__(self) -> str:
        ref : float = (self.read_word(WaterTankPLCMemMapping.SET_POINT.value) * 3.0) / 1000.0
        lvl : float = (self.read_word(WaterTankPLCMemMapping.TANK_LVL.value) * 3.0) / 1000.0
        v_in : float = self.read_word(WaterTankPLCMemMapping.VALVE_IN.value) / 10.0
        v_out : float = self.read_word(WaterTankPLCMemMapping.VALVE_OUT.value) / 10.0
        status : str = (
            f'      # PLC Status\r\n'
            f'        Set point:  {ref:0.2f} m\r\n'
            f'        Tank level: {lvl:0.2f} m\r\n'
            f'        Valve in:   {v_in:0.2f} %\r\n'
            f'        Valve out:  {v_out:0.2f} %\r\n'
        )
        return super().__str__() + status

    def sync(self):
        phys : modbus.ModbusClient = modbus.ModbusClient(self._phys_ip)
        phys.connect()
        while not self._terminate:
            try:
                lvl = phys.read_input_word(WaterTankPhysMemMapping.TANK_LVL.value, unit=self._slave_id)
                self._write_word(WaterTankPLCMemMapping.TANK_LVL.value, lvl)
                phys.send_word(WaterTankPhysMemMapping.VALVE_IN.value, self.read_word(WaterTankPLCMemMapping.VALVE_IN.value), unit=self._slave_id)
                phys.send_word(WaterTankPhysMemMapping.VALVE_OUT.value, self.read_word(WaterTankPLCMemMapping.VALVE_OUT.value), unit=self._slave_id)
            except BrokenPipeError:
                phys.reconnect()
            sleep(SYNC_TIMER)
        phys.close()

    def simulate(self):
        sync_thread = Thread(target=self.sync)
        sync_thread.start()
        t_s : float = 0.1 # Sample time
        e_i : float = 0.0 # Error
        h_0 : float = 1.5 # Linearization point
        while not self._terminate:
            # Simple LQI controller using a set point
            ref : float = (self.read_word(WaterTankPLCMemMapping.SET_POINT.value) * 3.0) / 1000.0
            lvl = self.read_word(WaterTankPLCMemMapping.TANK_LVL.value)
            lvl = (lvl * 3.0) / 1000.0
            e_i = e_i + (ref - lvl) * t_s
            e_i = max(-15, e_i) if e_i < 15 else 15
            v_in : int = int( (-0.79 * (lvl - h_0) + 0.07 * e_i + 0.5) * 1000)
            v_out : int = int( (0.79 * (lvl - h_0) -0.07 * e_i + 0.5) * 1000)
            v_in = max(0, v_in) if v_in < 1000 else 1000
            v_out = max(0, v_out) if v_out < 1000 else 1000
            self._write_word(WaterTankPLCMemMapping.VALVE_IN.value, v_in)
            self._write_word(WaterTankPLCMemMapping.VALVE_OUT.value, v_out)
            sleep(t_s)
        sync_thread.join()

# Scenario #2 - Automated warehouse

# Warehouse key positions
IDLE_POSITION : int = 55
RETRIEVE_NONE : int = 0
MAX_STORAGE : int = 54
MIN_STORAGE : int = 1
FORKLIFT_TIMER : float = LOOP_TIMER * 15.0

class WarehousePhysMemMapping(Enum):
    # FactoryIO Modbus Mapping
    # -- Coils --
    ENTRY_CONVEYOR  = 0x0000
    LOAD_CONVEYOR   = 0x0001
    FORKS_LEFT      = 0x0002
    FORKS_RIGHT     = 0x0003
    LIFT            = 0x0004
    UNLOAD_CONVEYOR = 0x0005
    EXIT_CONVEYOR   = 0x0006
    # -- Direct Input --
    AT_ENTRY  = 0x0000
    AT_LOAD   = 0x0001
    AT_LEFT   = 0x0002
    AT_MIDDLE = 0x0003
    AT_RIGHT  = 0x0004
    AT_UNLOAD = 0x0005
    AT_EXIT   = 0x0006
    MOVING_X  = 0x0007
    MOVING_Z  = 0x0008
    # -- Holding Registers --
    TARGET_POSITION = 0x0000

class ConveyorPLCMemMapping(Enum):
    AT_ENTRY        = 0x00000
    AT_LOAD         = 0x00001
    AT_UNLOAD       = 0x00002
    AT_EXIT         = 0x00003
    ENTRY_CONVEYOR  = 0x10000
    LOAD_CONVEYOR   = 0x10001
    UNLOAD_CONVEYOR = 0x10002
    EXIT_CONVEYOR   = 0x10003
    FORKLIFT_BUSY   = 0x10004

class ConveyorPLC(PLCDevice):

    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        self._memory[ConveyorPLCMemMapping.AT_ENTRY.value       ] = 0
        self._memory[ConveyorPLCMemMapping.AT_LOAD.value        ] = 0
        self._memory[ConveyorPLCMemMapping.AT_UNLOAD.value      ] = 0
        self._memory[ConveyorPLCMemMapping.AT_EXIT.value        ] = 0
        self._memory[ConveyorPLCMemMapping.ENTRY_CONVEYOR.value ] = 0
        self._memory[ConveyorPLCMemMapping.LOAD_CONVEYOR.value  ] = 0
        self._memory[ConveyorPLCMemMapping.UNLOAD_CONVEYOR.value] = 0
        self._memory[ConveyorPLCMemMapping.EXIT_CONVEYOR.value  ] = 0
        self._memory[ConveyorPLCMemMapping.FORKLIFT_BUSY.value  ] = 0
    
    def __str__(self) -> str:
        at_entry : str = "X" if self.read_bool(ConveyorPLCMemMapping.AT_ENTRY.value) else " "
        at_load : str = "X" if self.read_bool(ConveyorPLCMemMapping.AT_LOAD.value) else " "
        at_unload : str = "X" if self.read_bool(ConveyorPLCMemMapping.AT_UNLOAD.value) else " "
        at_exit : str = "X" if self.read_bool(ConveyorPLCMemMapping.AT_EXIT.value) else " "
        entry_cnv : str = "X" if self.read_bool(ConveyorPLCMemMapping.ENTRY_CONVEYOR.value) else " "
        load_cnv : str = "X" if self.read_bool(ConveyorPLCMemMapping.LOAD_CONVEYOR.value) else " "
        unload_cnv : str = "X" if self.read_bool(ConveyorPLCMemMapping.UNLOAD_CONVEYOR.value) else " "
        exit_cnv : str = "X" if self.read_bool(ConveyorPLCMemMapping.EXIT_CONVEYOR.value) else " "
        forklift : str = "X" if self.read_bool(ConveyorPLCMemMapping.FORKLIFT_BUSY.value) else " "
        status = (
            f'      # PLC Status:\r\n\r\n'
            f'        Sensors:\r\n'
            f'        [{at_entry}] Entry\t[{at_load}] Load\t[{at_unload}] Unload\t[{at_exit}] Exit\r\n'
            f'        Conveyors:\r\n'
            f'        [{entry_cnv}] Entry\t[{load_cnv}] Load\t[{unload_cnv}] Unload\t[{exit_cnv}] Exit \r\n'
            f'        Process:\r\n'
            f'        [{forklift}] Forklift Busy\r\n'
        )
        return super().__str__() + status

    def sync(self):
        phys : modbus.ModbusClient = modbus.ModbusClient(self._phys_ip)
        phys.connect()
        while not self._terminate:
            try:
                # Sensors
                self.write_bool(ConveyorPLCMemMapping.AT_ENTRY.value, phys.read_discrete_input(WarehousePhysMemMapping.AT_ENTRY.value))
                self.write_bool(ConveyorPLCMemMapping.AT_LOAD.value, phys.read_discrete_input(WarehousePhysMemMapping.AT_LOAD.value))
                self.write_bool(ConveyorPLCMemMapping.AT_UNLOAD.value, phys.read_discrete_input(WarehousePhysMemMapping.AT_UNLOAD.value))
                self.write_bool(ConveyorPLCMemMapping.AT_EXIT.value, phys.read_discrete_input(WarehousePhysMemMapping.AT_EXIT.value))
                # Actuators
                phys.send_bool(WarehousePhysMemMapping.ENTRY_CONVEYOR.value, self.read_bool(ConveyorPLCMemMapping.ENTRY_CONVEYOR.value))
                phys.send_bool(WarehousePhysMemMapping.LOAD_CONVEYOR.value, self.read_bool(ConveyorPLCMemMapping.LOAD_CONVEYOR.value))
                phys.send_bool(WarehousePhysMemMapping.UNLOAD_CONVEYOR.value, self.read_bool(ConveyorPLCMemMapping.UNLOAD_CONVEYOR.value))
                phys.send_bool(WarehousePhysMemMapping.EXIT_CONVEYOR.value, self.read_bool(ConveyorPLCMemMapping.EXIT_CONVEYOR.value))
            except BrokenPipeError:
                phys.reconnect()
            sleep(SYNC_TIMER)
        phys.close()
    
    def simulate(self):
        sync_thread = Thread(target=self.sync)
        sync_thread.start()
        while not self._terminate:
            at_entry = not self.read_bool(ConveyorPLCMemMapping.AT_ENTRY.value)     # FactoryIO uses negative logic sensors for this purpose (True -> Empty, False -> Box)
            at_load = not self.read_bool(ConveyorPLCMemMapping.AT_LOAD.value)       # FactoryIO uses negative logic sensors for this purpose (True -> Empty, False -> Box)
            at_exit = not self.read_bool(ConveyorPLCMemMapping.AT_EXIT.value)       # FactoryIO uses negative logic sensors for this purpose (True -> Empty, False -> Box)
            forklift = self.read_bool(ConveyorPLCMemMapping.FORKLIFT_BUSY.value)
            self.write_bool(ConveyorPLCMemMapping.ENTRY_CONVEYOR.value, not (at_load or forklift))
            self.write_bool(ConveyorPLCMemMapping.LOAD_CONVEYOR.value, not (at_load or forklift))
            self.write_bool(ConveyorPLCMemMapping.UNLOAD_CONVEYOR.value, not (at_exit or forklift))
            self.write_bool(ConveyorPLCMemMapping.EXIT_CONVEYOR.value, not at_exit)
            sleep(LOOP_TIMER)
        sync_thread.join()

class ForkliftPLCMemMapping(Enum):
    AT_LEFT           = 0x00000
    AT_MIDDLE         = 0x00001
    AT_RIGHT          = 0x00002
    MOVING_X          = 0x00003
    MOVING_Z          = 0x00004
    FORKS_LEFT        = 0x10000
    FORKS_RIGHT       = 0x10001
    LIFT              = 0x10002
    TARGET_POSITION   = 0x30000
    RETRIEVE_POSITION = 0x30001

class ForkliftStatus(Enum):
    IDLE = 0
    RECEIVING = 1
    STORING = 2
    RETRIEVING = 3
    DELIVERING = 4

class ForkliftPLC(PLCDevice):

    def __init__(self, guid: int, neighbors_in: list[int] = list(), neighbors_out: list[int] = list(), **kwargs):
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        assert 'cnv_ip' in kwargs.keys() and isinstance(kwargs['cnv_ip'], str), f'Missing conveyors PLC IP address ([cnv_ip] directive not found)'
        self._conveyor_ip : str = kwargs['cnv_ip']
        self._status : ForkliftStatus                                   = ForkliftStatus.IDLE
        self._storage : int                                             = 0                     # An integer representing the available shelfs. Each bit represents a shelf (0 -> available, 1 -> occupied), enumerated from the LSB to the MSB
        self._memory[ForkliftPLCMemMapping.AT_LEFT.value]               = 0
        self._memory[ForkliftPLCMemMapping.AT_MIDDLE.value]             = 0
        self._memory[ForkliftPLCMemMapping.AT_RIGHT.value]              = 0
        self._memory[ForkliftPLCMemMapping.MOVING_X.value]              = 0
        self._memory[ForkliftPLCMemMapping.MOVING_Z.value]              = 0
        self._memory[ForkliftPLCMemMapping.FORKS_LEFT.value]            = 0
        self._memory[ForkliftPLCMemMapping.FORKS_RIGHT.value]           = 0
        self._memory[ForkliftPLCMemMapping.LIFT.value]                  = 0
        self._memory[ForkliftPLCMemMapping.TARGET_POSITION.value]       = IDLE_POSITION         # FactoryIO Starting position. The valid range of this holding registar is [0-55]
        self._memory[ForkliftPLCMemMapping.RETRIEVE_POSITION.value]     = 0                     # Since '0' is 'current position' in FactoryIO, we'll use it to indicate 'retrieve nothing'. The valid range for this holding register will be [0-54]
    
    def __str__(self) -> str:
        at_left = 'X' if self.read_bool(ForkliftPLCMemMapping.AT_LEFT.value) else ' '
        at_middle = 'X' if self.read_bool(ForkliftPLCMemMapping.AT_MIDDLE.value) else ' '
        at_right = 'X' if self.read_bool(ForkliftPLCMemMapping.AT_RIGHT.value) else ' '
        moving_x = 'X' if self.read_bool(ForkliftPLCMemMapping.MOVING_X.value) else ' '
        moving_z = 'X' if self.read_bool(ForkliftPLCMemMapping.MOVING_Z.value) else ' '
        forks_left = 'X' if self.read_bool(ForkliftPLCMemMapping.FORKS_LEFT.value) else ' '
        forks_right = 'X' if self.read_bool(ForkliftPLCMemMapping.FORKS_RIGHT.value) else ' '
        lift = 'X' if self.read_bool(ForkliftPLCMemMapping.LIFT.value) else ' '
        target = self.read_word(ForkliftPLCMemMapping.TARGET_POSITION.value)
        retrieve = self.read_word(ForkliftPLCMemMapping.RETRIEVE_POSITION.value)
        storage = f'{self._storage:054b}'.replace('0','_').replace('1', 'X')
        status : str = (
            f'      # PLC Status:\t{str(self._status)}\r\n\r\n'
            f'        Sensors:\r\n'
            f'        [{at_left}] At Left\t[{at_middle}] At Middle\t[{at_right}] At Right\r\n'
            f'        [{moving_x}] Moving X\t[{moving_z}] Moving Z\r\n'
            f'        Forklift:\r\n'
            f'        [{lift}] Lift\t[{forks_left}] Forks Left\t[{forks_right}] Forks Right\r\n'
            f'        Positioning:\r\n'
            f'        Store [{target:2d}]\tRetrieve [{retrieve:2d}]\r\n'
            f'        Storage status:\r\n'
            f'        [{storage}]'
        )
        return super().__str__() + status
    
    def _next_available(self) -> int:
        index : int = 0
        while bool((self._storage >> index) & 0b1):
            index += 1
        return index + 1
    
    def sync(self):
        phys : modbus.ModbusClient = modbus.ModbusClient(self._phys_ip)
        phys.connect()
        while not self._terminate:
            try:
                # Sensors
                self.write_bool(ForkliftPLCMemMapping.AT_LEFT.value, phys.read_discrete_input(WarehousePhysMemMapping.AT_LEFT.value))
                self.write_bool(ForkliftPLCMemMapping.AT_MIDDLE.value, phys.read_discrete_input(WarehousePhysMemMapping.AT_MIDDLE.value))
                self.write_bool(ForkliftPLCMemMapping.AT_RIGHT.value, phys.read_discrete_input(WarehousePhysMemMapping.AT_RIGHT.value))
                self.write_bool(ForkliftPLCMemMapping.MOVING_X.value, phys.read_discrete_input(WarehousePhysMemMapping.MOVING_X.value))
                self.write_bool(ForkliftPLCMemMapping.MOVING_Z.value, phys.read_discrete_input(WarehousePhysMemMapping.MOVING_Z.value))
                # Forklift
                phys.send_bool(WarehousePhysMemMapping.LIFT.value, self.read_bool(ForkliftPLCMemMapping.LIFT.value))
                phys.send_bool(WarehousePhysMemMapping.FORKS_LEFT.value, self.read_bool(ForkliftPLCMemMapping.FORKS_LEFT.value))
                phys.send_bool(WarehousePhysMemMapping.FORKS_RIGHT.value, self.read_bool(ForkliftPLCMemMapping.FORKS_RIGHT.value))
                # Positioning
                phys.send_word(WarehousePhysMemMapping.TARGET_POSITION.value, self.read_word(ForkliftPLCMemMapping.TARGET_POSITION.value))
            except BrokenPipeError:
                phys.reconnect()
            sleep(SYNC_TIMER)
        phys.close()
    
    def simulate(self):
        sync_thread = Thread(target=self.sync)
        sync_thread.start()
        conveyor_plc : modbus.ModbusClient = modbus.ModbusClient(self._conveyor_ip)
        conveyor_plc.connect()
        while not self._terminate:
            try:
                status : ForkliftStatus = self._status
                next_shelf : int = self._next_available() & 0x3F
                if status == ForkliftStatus.IDLE:
                    at_load : bool = not conveyor_plc.read_discrete_input(ConveyorPLCMemMapping.AT_LOAD.value) # FactoryIO uses negative logic sensors for this purpose (True -> Empty, False -> Box)
                    retrieve : int = self.read_word(ForkliftPLCMemMapping.RETRIEVE_POSITION.value)
                    target : int = self.read_word(ForkliftPLCMemMapping.TARGET_POSITION.value)
                    next_shelf : int = self._next_available() & 0xFF
                    if retrieve >= MIN_STORAGE and retrieve <= MAX_STORAGE and target == IDLE_POSITION:
                        conveyor_plc.send_bool(ConveyorPLCMemMapping.FORKLIFT_BUSY.value & 0xFFFF, True)
                        self._status = ForkliftStatus.RETRIEVING
                    elif at_load and next_shelf <= MAX_STORAGE:
                        conveyor_plc.send_bool(ConveyorPLCMemMapping.FORKLIFT_BUSY.value & 0xFFFF, True)
                        self._status = ForkliftStatus.RECEIVING
                elif status == ForkliftStatus.RECEIVING:
                    lift = self.read_bool(ForkliftPLCMemMapping.LIFT.value)
                    at_middle = self.read_bool(ForkliftPLCMemMapping.AT_MIDDLE.value)
                    if at_middle:
                        if lift:
                            self._status = ForkliftStatus.STORING
                        else:
                            self.write_bool(ForkliftPLCMemMapping.FORKS_LEFT.value, True)
                    else:
                        if lift:
                            self.write_bool(ForkliftPLCMemMapping.FORKS_LEFT.value, False)
                        else:
                            self.write_bool(ForkliftPLCMemMapping.LIFT.value, True)
                elif status == ForkliftStatus.STORING:
                    target = self.read_word(ForkliftPLCMemMapping.TARGET_POSITION.value)
                    moving = self.read_bool(ForkliftPLCMemMapping.MOVING_X.value) or self.read_bool(ForkliftPLCMemMapping.MOVING_Z.value)
                    at_middle = self.read_bool(ForkliftPLCMemMapping.AT_MIDDLE.value)
                    lift = self.read_bool(ForkliftPLCMemMapping.LIFT.value)
                    if target == IDLE_POSITION:
                        if not moving:
                            if lift:
                                self._storage |= 2 ** (next_shelf - 1)
                                self.write_word(ForkliftPLCMemMapping.TARGET_POSITION.value, next_shelf)
                            else:
                                conveyor_plc.send_bool(ConveyorPLCMemMapping.FORKLIFT_BUSY.value & 0xFFFF, False)
                                self._status = ForkliftStatus.IDLE
                    else:
                        if not moving:
                            if at_middle:
                                if lift:
                                    self.write_bool(ForkliftPLCMemMapping.FORKS_RIGHT.value, True)
                                else:
                                    self.write_word(ForkliftPLCMemMapping.TARGET_POSITION.value, IDLE_POSITION)
                            else:
                                if lift:
                                    self.write_bool(ForkliftPLCMemMapping.LIFT.value, False)
                                else:
                                    self.write_bool(ForkliftPLCMemMapping.FORKS_RIGHT.value, False)

                elif status == ForkliftStatus.RETRIEVING:
                    target = self.read_word(ForkliftPLCMemMapping.TARGET_POSITION.value)
                    retrieve = self.read_word(ForkliftPLCMemMapping.RETRIEVE_POSITION.value)
                    moving = self.read_bool(ForkliftPLCMemMapping.MOVING_X.value) or self.read_bool(ForkliftPLCMemMapping.MOVING_Z.value)
                    at_middle = self.read_bool(ForkliftPLCMemMapping.AT_MIDDLE.value)
                    lift = self.read_bool(ForkliftPLCMemMapping.LIFT.value)
                    if target == IDLE_POSITION:
                        if not moving:
                            if lift:
                                self.write_word(ForkliftPLCMemMapping.RETRIEVE_POSITION.value, RETRIEVE_NONE)
                                self._status = ForkliftStatus.DELIVERING
                            else:
                                self.write_word(ForkliftPLCMemMapping.TARGET_POSITION.value, retrieve)
                                self._storage &= ((2 ** (retrieve - 1)) ^ 0xFFFFFFFFFFFFFF) if retrieve in range(MIN_STORAGE,IDLE_POSITION) else self._storage
                    else:
                        if not moving:
                            if at_middle:
                                if lift:
                                    self.write_word(ForkliftPLCMemMapping.TARGET_POSITION.value, IDLE_POSITION)
                                else:
                                    self.write_bool(ForkliftPLCMemMapping.FORKS_RIGHT.value, True)
                            else:
                                if lift:
                                    self.write_word(ForkliftPLCMemMapping.FORKS_RIGHT.value, False)
                                else:
                                    self.write_word(ForkliftPLCMemMapping.LIFT.value, True)
                else:
                    at_middle = self.read_bool(ForkliftPLCMemMapping.AT_MIDDLE.value)
                    lift = self.read_bool(ForkliftPLCMemMapping.LIFT.value)
                    if at_middle:
                        if lift:
                            self.write_bool(ForkliftPLCMemMapping.FORKS_RIGHT.value, True)
                        else:
                            conveyor_plc.send_bool(ConveyorPLCMemMapping.FORKLIFT_BUSY.value & 0xFFFF, False)
                            self._status = ForkliftStatus.IDLE
                    else:
                        if lift:
                            self.write_bool(ForkliftPLCMemMapping.LIFT.value, False)
                        else:
                            self.write_bool(ForkliftPLCMemMapping.FORKS_RIGHT.value, False)
                sleep(FORKLIFT_TIMER)
            except BrokenPipeError:
                conveyor_plc.reconnect()
        conveyor_plc.close()
        sync_thread.join()
