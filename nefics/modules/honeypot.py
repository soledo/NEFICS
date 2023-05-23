#!/usr/bin/env python3

import subprocess
import os
from time import sleep
from datetime import datetime
from nefics.modules.devicebase import IEDBase, DeviceHandler

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
        self._process = None
    
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
        self._process.terminate()
        self._process.wait(20)
