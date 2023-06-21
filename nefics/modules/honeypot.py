#!/usr/bin/env python3

# Standard imports
import subprocess
import os
from enum import Enum
from time import sleep
# from math import max
from datetime import datetime
from threading import Thread
from typing import Union, Callable
# NEFICS imports
from nefics.modules.devicebase import IEDBase, DeviceHandler, ProtocolListener, LOG_PRIO
from nefics.protos import http, modbus

class HoneyDevice(IEDBase):
    # Will only hold the honeyd configuration
    
    def __init__(self, guid: int, neighbors_in: list = ..., neighbors_out: list = ..., **kwargs):
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        assert 'honeyconf' in kwargs.keys()
        assert os.path.exists(kwargs['honeyconf'])
        self._honeyconf = kwargs['honeyconf']
    
    @property
    def honeyconf(self) -> str:
        return self._honeyconf

class HoneyHandler(DeviceHandler):
    
    def __init__(self, device: HoneyDevice):
        super().__init__(device)
        self._device = device
        check_honey = subprocess.call(['which', 'honeyd'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
        if check_honey != 0:
            raise FileNotFoundError(2, 'Cannot find executable', 'honeyd')
        self._process : Union[subprocess.Popen, None] = None
    
    def _respawn(self):
        if isinstance(self._process, subprocess.Popen):
            self._process.kill()
            self._process = None
        self._process = subprocess.Popen(
            ['honeyd', '-d', '-i', 'honeypot-eth0', '-f', self._device.honeyconf],
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

class PLCMemMapping(Enum):
    TANK_LVL  : int = 0x20000
    SET_POINT : int = 0x30000
    VALVE_IN  : int = 0x30002
    VALVE_OUT : int = 0x30004

class PhysMemMapping(Enum):
    # FactoryIO Modbus Mapping
    TANK_LVL  : int = 0x0001 # IR
    VALVE_IN  : int = 0x0000 # HR
    VALVE_OUT : int = 0x0001 # HR

class PLCDevice(IEDBase):

    def __init__(self, guid: int, neighbors_in: list = ..., neighbors_out: list = ..., **kwargs):
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        assert 'phys_ip' in kwargs.keys() and isinstance(kwargs['phys_ip'], str)
        assert 'set_point' in kwargs.keys() and isinstance(kwargs['set_point'], float) and kwargs['set_point'] > 0.0 and kwargs['set_point'] < 3.0
        self._html : Union[str, None] = kwargs['html'] if 'html' in kwargs.keys() and isinstance(kwargs['html'], str) else None
        self._httpsrv = kwargs['httpsrv'] if 'httpsrv' in kwargs.keys() and isinstance(kwargs['httpsrv'], str) else None
        self._protocols : Union[list[str], None] = kwargs['protos'] if 'protos' in kwargs.keys() and isinstance(kwargs['protos'], list) and all(isinstance(x, str) for x in kwargs['protos']) else None
        self._phys_ip = kwargs['phys_ip']
        set_point : int = int((1000.0 * kwargs['set_point']) / 3.0) # Set point (HR) [0-1000] <-> [0-3m]
        self._memory[PLCMemMapping.TANK_LVL.value] = 0 # Water level meter (IR) [0-1000] <-> [0-3m]
        self._memory[PLCMemMapping.TANK_LVL.value + 1] = 0
        self._memory[PLCMemMapping.SET_POINT.value] =  set_point & 0xff
        self._memory[PLCMemMapping.SET_POINT.value + 1] =  (set_point & 0xff00) >> 8
        self._memory[PLCMemMapping.VALVE_IN.value] = 0 # Valve in (HR) [0-1000] <-> [0-100%]
        self._memory[PLCMemMapping.VALVE_IN.value + 1] = 0
        self._memory[PLCMemMapping.VALVE_OUT.value] = 0 # Valve out (HR) [0-1000] <-> [0-100%]
        self._memory[PLCMemMapping.VALVE_OUT.value + 1] = 0
    
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
        ref : float = (self.read_word(PLCMemMapping.SET_POINT.value) * 3.0) / 1000.0
        lvl : float = (self.read_word(PLCMemMapping.TANK_LVL.value) * 3.0) / 1000.0
        v_in : float = self.read_word(PLCMemMapping.VALVE_IN.value) / 10.0
        v_out : float = self.read_word(PLCMemMapping.VALVE_OUT.value) / 10.0
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
            f'      # Status\r\n'
            f'        Set point:  {ref:0.2f} m\r\n'
            f'        Tank level: {lvl:0.2f} m\r\n'
            f'        Valve in:   {v_in:0.2f} %\r\n'
            f'        Valve out:  {v_out:0.2f} %\r\n'
        )
        return devicestr
    
    def sync(self):
        phys : modbus.ModbusClient = modbus.ModbusClient(self._phys_ip)
        phys.connect()
        while not self._terminate:
            lvl = phys.read_input_word(PhysMemMapping.TANK_LVL.value, unit=1)
            self._write_word(PLCMemMapping.TANK_LVL.value, lvl)
            phys.send_word(PhysMemMapping.VALVE_IN.value, self.read_word(PLCMemMapping.VALVE_IN.value), unit=1)
            phys.send_word(PhysMemMapping.VALVE_OUT.value, self.read_word(PLCMemMapping.VALVE_OUT.value), unit=1)
        phys.close()

    def simulate(self):
        sync_thread = Thread(target=self.sync)
        sync_thread.start()
        t_s : float = 0.1 # Sample time
        e_i : float = 0.0 # Error
        h_0 : float = 1.5 # Linearization point
        while not self._terminate:
            ref : float = (self.read_word(PLCMemMapping.SET_POINT.value) * 3.0) / 1000.0
            lvl = self.read_word(PLCMemMapping.TANK_LVL.value)
            lvl = (lvl * 3.0) / 1000.0
            e_i = e_i + (ref - lvl) * t_s
            e_i = max(-15, e_i) if e_i < 15 else 15
            v_in : int = int( (-0.79 * (lvl - h_0) + 0.07 * e_i + 0.5) * 1000)
            v_out : int = int( (0.79 * (lvl - h_0) -0.07 * e_i + 0.5) * 1000)
            v_in = max(0, v_in) if v_in < 1000 else 1000
            v_out = max(0, v_out) if v_out < 1000 else 1000
            self._write_word(PLCMemMapping.VALVE_IN.value, v_in)
            self._write_word(PLCMemMapping.VALVE_OUT.value, v_out)
            sleep(t_s)
        sync_thread.join()


class PLCHandler(DeviceHandler):

    def __init__(self, device: PLCDevice):
        super().__init__(device)
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
            phandlers : dict[str, Callable]= {
                'http' : self._start_http,
                'modbus' : self._start_modbus
            }
            for p in self._device.protocols:
                if p.lower() in phandlers.keys():
                    phandlers[p]()
                else:
                    self._device.log(message=f'Unknown protocol: {p}', prio=LOG_PRIO['WARNING'])
        while not self._terminate:
            # Dummy loop
            sleep(1)
        while any(thr.is_alive() for thr in self._protocols.values()):
            for thr in self._protocols.values():
                if thr.is_alive():
                    thr.terminate = True
                    thr.join(1)
        self._device.join()
        
