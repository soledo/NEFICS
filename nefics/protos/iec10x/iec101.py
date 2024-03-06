#!/usr/bin/env python3

from enum import Enum
from serial import Serial
from time import sleep
from typing import Callable, Optional, Union

from nefics.modules.devicebase import DeviceBase, DeviceHandler, ProtocolListener
from nefics.protos.iec10x.packets import ASDU, FT12Fixed, FT12Frame, FT12Single, FT12Variable
from nefics.protos.iec10x.enums import CONTROL_FLAGS
from nefics.protos.iec10x.util import time56

BAUD_RATES = [50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
UART_TIMEOUT = 1
BUFFER_SIZE = 263 # Max length of frame: ASDU_MAX = 255 + 

class ControlledState(Enum):
    # Balanced transmission. Figure 9 from IEC 60870-5-101 IEC:2003 pp.23
    LINKLAYER_NOT_RESET = 0
    LINKLAYER_AVAILABLE = 1
    LINKLAYER_BUSY = 2
    EVAL_SEND_CONFIRM = 3
    EVAL_SEND_NOREPLY = 4

class IEC101Handler(DeviceHandler):

    def __init__(self, *args, device: DeviceBase, uart: Serial, **kwargs):
        super().__init__(*args, device=device, **kwargs)
        self._uart : Serial = uart
        self._state : ControlledState = ControlledState.LINKLAYER_NOT_RESET
        self._selected_for_operation : Optional[int] = None # IOA for SBO scheme
        self._frame_handlers : dict[tuple[int, int], Callable[[ASDU], None]] = {
            (45, 6) : self._handle_IO45_IO58, # Single command (Act)
            (46 ,6) : self._handle_IO46_IO59, # Double command (Act)
            (49, 6) : self._handle_IO49_IO62, # Set-point command, scaled value (Act)
            (50, 6) : self._handle_IO50_IO63, # Set-point command, short floating point number (Act)
            (58, 6) : self._handle_IO45_IO58, # Single command with time tag CP56Time2a (Act)
            (59, 6) : self._handle_IO46_IO59, # Double command with time tag CP56Time2a (Act)
            (62, 6) : self._handle_IO49_IO62, # Set-point command, scaled value with time tag CP56Time2a (Act)
            (63, 6) : self._handle_IO50_IO63, # Set-point command with time tag CP56Time2a, short floating point number (Act)
            # (100, 6) : self._handle_IO100,    # Interrogation command (Act)
            # (102, 5) : self._handle_IO102,    # Read command (req)
        }
    
    def _reset_link(self):
        self._uart.reset_input_buffer()
        self._uart.reset_output_buffer()
    
    @staticmethod
    def check_flag(value : int, flag : str) -> bool:
        assert flag in ['FCV', 'FCB', 'PRM']
        assert value in range(256)
        key = 0x00
        for k, v in CONTROL_FLAGS.items():
            if v == flag:
                key = k
                break
        return bool(value & key > 0)

    def _handle_IO45_IO58(self, asdu : ASDU):
        'Handle C_SC_NA_1 (Single command) and C_SC_TA_1 (Single command with time tag CP56Time2a)'
        select : bool = asdu.IO.SE == 0b1
        scs : bool = asdu.IO.SCS == 0b1
        ioa : int = ((asdu.IO.IOA & 0xffff) << 2) # Adjust IOA to match 3-byte memory mapping
        if select and self._selected_for_operation is None and ioa in range(0x10000,0x20000):
            self._selected_for_operation = int(ioa)
        else: # EXECUTE
            if self._selected_for_operation == int(ioa):
                # Correct IOA for operation
                self._device.write_bool(ioa, scs)
            self._selected_for_operation = None

    def _handle_IO46_IO59(self, asdu : ASDU):
        'Handle C_DC_NA_1 (Double command) and C_DC_TA_1 (Double command with time tag CP56Time2a)'
        select : bool = asdu.IO.SE == 0b1
        dcs : int = asdu.IO.DCS & 0b11
        ioa : int = ((asdu.IO.IOA & 0xffff) << 2) # Adjust IOA to match 3-byte memory mapping
        if dcs not in [0, 3] and select and self._selected_for_operation is None and ioa in range(0x10000, 0x20000):
            self._selected_for_operation = int(ioa)
        else:
            if dcs not in [0, 3] and self._selected_for_operation == int(ioa):
                # Correct IOA for operation
                self._device.write_bool(ioa, dcs == 2)
            self._selected_for_operation = None

    def _handle_IO49_IO62(self, asdu : ASDU):
        'Handle C_SE_NB_1 (Set-point command, scaled value) and C_SE_TB_1 (Set point command, scaled value with time tag CP56Time2a)'
        select : bool = asdu.IO.SE == 0b1
        value : int = asdu.IO.SVA & 0xFFFF
        ioa : int = ((asdu.IO.IOA & 0xffff) << 2) # Adjust IOA to match 3-byte memory mapping
        if select and self._selected_for_operation is None and ioa in range(0x30000, 0x38000):
            self._selected_for_operation = int(ioa)
        else: # EXECUTE
            if self._selected_for_operation == int(ioa):
                # Correct IOA for operation
                self._device.write_word(ioa, value)
            self._selected_for_operation = None

    def _handle_IO50_IO63(self, asdu : ASDU):
        'Handle C_SE_NC_1 (set point command, short floating point number) and C_SE_TC_1 (Set-point command with time tag CP56Time2a, short floating point number)'
        select : bool = asdu.IO.SE == 0b1
        value : float = asdu.IO.value
        ioa : int = ((asdu.IO.IOA & 0xffff) << 2) # Adjust IOA to match 3-byte memory mapping
        if select and self._selected_for_operation is None and ioa in range(0x38000, 0x40000):
            self._selected_for_operation = int(ioa)
        else: # EXECUTE
            if self._selected_for_operation == int(ioa):
                # Correct IOA for operation
                self._device.write_ieee_float(ioa, value)
            self._selected_for_operation = None

    def _eval_user_data(self, asdu : ASDU) -> FT12Frame:    
        handler_key = (asdu.type, asdu.COT)
        if handler_key in self._frame_handlers.keys():
            self._frame_handlers[handler_key](asdu)
            return FT12Frame()/FT12Single(acknowledge=0xe5) # ACK
        return FT12Frame()/FT12Single(acknowledge=0xa2)     # NACK

    def run(self):
        while not self.terminate:
            try:
                buffer : bytes = self._uart.read(BUFFER_SIZE)
                if len(buffer) > 0:
                    ftframe : FT12Frame = FT12Frame(buffer)
                    assert ftframe.haslayer(FT12Fixed) or ftframe.haslayer(FT12Variable)
                    frame : Union[FT12Fixed, FT12Variable] = ftframe[FT12Fixed] if ftframe.haslayer(FT12Fixed) else ftframe[FT12Variable]
                    assert self.check_flag(frame.Control_Flags, 'PRM')
                    assert frame.address == self._device.guid
                    if self._state == ControlledState.LINKLAYER_NOT_RESET:
                        assert frame.fcode in [0x00, 0x09]
                        if frame.fcode == 0x09:
                            ftframe = FT12Frame()/FT12Fixed(fcode=0x0b, address=self._device.guid)
                            self._uart.write(ftframe.build())
                        else:
                            ftframe = FT12Frame()/FT12Fixed(fcode=0x00, address=self._device.guid)
                            self._uart.write(ftframe.build())
                            self._reset_link()
                            self._state = ControlledState.LINKLAYER_AVAILABLE
                    elif self._state == ControlledState.LINKLAYER_AVAILABLE:
                        if frame.fcode == 0x00:
                            ftframe = FT12Frame()/FT12Fixed(fcode=0x00, address=self._device.guid)
                            self._uart.write(ftframe.build())
                            self._reset_link()
                        elif frame.fcode in [0x01, 0x02]:
                            ftframe = FT12Frame()/FT12Single(acknowledge=0xe5) # ACK
                            self._uart.write(ftframe.build())
                        elif frame.fcode in [0x03, 0x04]:
                            # EVAL SEND/CONFIRM (0x03) -- SEND/NO_REPLY (0x04)
                            # Must include User data => Variable length
                            assert isinstance(frame, FT12Variable)
                            asdu : ASDU = frame['LinkUserData']
                            ftframe = self._eval_user_data(asdu)
                            if frame.fcode == 0x03:
                                self._uart.write(ftframe.build())
                        elif frame.fcode == 0x09:
                            ftframe = FT12Frame()/FT12Fixed(fcode=0x0b, address=self._device.guid)
                            self._uart.write(ftframe.build())
                        else:
                            ftframe = FT12Frame()/FT12Single(acknowledge=0xa2) # NACK
                            self._uart.write(ftframe.build())
            except AssertionError:
                continue


class IEC101Listener(ProtocolListener):

    def __init__(self, *args, device: DeviceBase, serial_device: str = '/dev/ttyS0', baud_rate : int = 9600, **kwargs):
        super().__init__(*args, device=device, **kwargs)
        assert baud_rate in BAUD_RATES
        self._serial_dev : str = serial_device
        self._baud_rate : int = baud_rate
    
    def run(self):
        with Serial(port=self._serial_dev, baudrate=self._baud_rate, timeout=UART_TIMEOUT) as serial_port:
            handler : IEC101Handler = IEC101Handler(device=self._device, uart=serial_port)
            handler.start()
            while not self.terminate:
                sleep(1)
            handler.join()
