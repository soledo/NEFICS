#!/usr/bin/env python3

# Standard imports
import subprocess
import os
from time import sleep
from datetime import datetime
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

class PLCDevice(IEDBase):

    def __init__(self, guid: int, neighbors_in: list = ..., neighbors_out: list = ..., **kwargs):
        super().__init__(guid, neighbors_in, neighbors_out, **kwargs)
        self._html : Union[str, None] = kwargs['html'] if 'html' in kwargs.keys() and isinstance(kwargs['html'], str) else None
        self._httpsrv = kwargs['httpsrv'] if 'httpsrv' in kwargs.keys() and isinstance(kwargs['httpsrv'], str) else None
        self._protocols : Union[list[str], None] = kwargs['protos'] if 'protos' in kwargs.keys() and isinstance(kwargs['protos'], list) and all(isinstance(x, str) for x in kwargs['protos']) else None
    
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
            f'        Device model: {self._device_model}\r\n'
        )
        return devicestr

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
        
