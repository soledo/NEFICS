#!/usr/bin/env python3

# Standard imports
import sys
import struct
from math import ceil
from enum import Enum
from threading import Thread
from socket import socket, timeout, AF_INET, SOCK_STREAM, IPPROTO_TCP, SHUT_RDWR
from typing import Callable, Optional
# Scapy imports
from scapy.packet import Packet
import scapy.contrib.modbus as smb
# NEFICS imports
from nefics.modules.devicebase import DeviceBase, DeviceHandler, ProtocolListener

MODBUS_TCP_PORT = 502
MODBUS_MAX_LENGTH = 260

MODBUS_TIMEOUT = 60 # Not defined in the specification. We chose a minute as a reasonable timeout for modbus.

MODBUS_WRITE_COIL_VALUES = {
    0x0000: False,
    0xFF00: True
}

class ModbusErrorCode(Enum):
    'Modbus Exception codes'
    ILLEGAL_FUNCTION_CODE = 0x01
    ILLEGAL_DATA_ADDRESS = 0x02
    ILLEGAL_DATA_VALUE = 0x03
    SERVER_FAILURE = 0x04
    ACKNOWLEDGE = 0x05
    SERVER_BUSY = 0x06
    GATEWAY_PATH_PROBLEM = 0x07
    GATEWAY_NO_RESPONSE = 0x08

class ModbusMemmap(Enum):
    '''Emulated memory offsets for Modbus'''
    DI = 0x00000
    CO = 0x10000
    IR = 0x20000
    HR = 0x30000

class ModbusReadCodes(Enum):
    'Modbus Device ID Read Codes'
    BASIC = 0x01
    REGULAR = 0x02
    EXTENDED = 0x03
    SPECIFIC = 0x04

class ModbusDeviceID(Enum):
    'Modbus Device ID values'
    VENDOR_NAME = 0x00
    PRODUCT_CODE = 0x01
    MAJOR_MINOR_REVISION = 0x02
    VENDOR_URL = 0x03
    PRODUCT_NAME = 0x04
    MODEL_NAME = 0x05
    USER_APP_NAME = 0x06

class ModbusHandler(DeviceHandler):

    def __init__(self, *args, device : DeviceBase, connection : socket, **kwargs):
        super().__init__(*args, device=device, **kwargs)
        self._device = device
        self._sock = connection
    
    def _mb_indication_RDCO_RDDI(self, function_code : int = 0x01, request_pdu : Optional[Packet] = None) -> Packet:
        '''Read coils request / Read Discrete Input Request'''
        try:
            assert request_pdu is not None
            address : int = request_pdu.startAddr
            quantity : int = request_pdu.quantity
            mem_offset : ModbusMemmap = ModbusMemmap.CO if function_code == 0x01 else ModbusMemmap.DI
            if not (0x0001 <= quantity and quantity <= 0x07d0): # Validate quantity. Up to 2000 according to protocol specifications
                # Exception Response with code 0x03 (Illegal data value)
                return smb.ModbusPDU01ReadCoilsError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value) if function_code == 0x01 else smb.ModbusPDU02ReadDiscreteInputsError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value)
            elif not self._device.check_addr(mem_offset.value, address, quantity): # Validate addresses. All addresses must be mapped in the device
                # Exception Response with code 0x02 (Illegal data address)
                return smb.ModbusPDU01ReadCoilsError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value) if function_code == 0x01 else smb.ModbusPDU02ReadDiscreteInputsError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
            else:
                # Attempt to read coil/discrete input values
                coils = 1
                for addr in range((mem_offset.value + address) + quantity - 1, (mem_offset.value + address) - 1, -1):
                    coils <<= 1
                    coils += 1 if self._device.read_bool(addr) else 0
                coils &= (2 ** quantity) - 1
                status = []
                if coils > 0:
                    while coils > 0:
                        status.append(coils & 0xff)
                        coils >>= 8
                else:
                    # All coils are in "False state"
                    status = [0x00] * ((quantity // 8) + (1 if quantity % 8 > 0 else 0))
                return smb.ModbusPDU01ReadCoilsResponse(coilStatus=status) if function_code == 0x01 else smb.ModbusPDU02ReadDiscreteInputsResponse(inputStatus=status)
        except AssertionError:
            # Exception Response with code 0x04 (Serve Failure)
            return smb.ModbusPDU01ReadCoilsError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value) if function_code == 0x01 else smb.ModbusPDU02ReadDiscreteInputsError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_RDHR_RDIR(self, function_code : int = 0x03, request_pdu : Optional[Packet] = None) -> Packet:
        '''Read Holding Registers / Input Registers'''
        try:
            assert request_pdu is not None
            address : int = request_pdu.startAddr
            quantity : int = request_pdu.quantity
            mem_offset : ModbusMemmap = ModbusMemmap.HR if function_code == 0x03 else ModbusMemmap.IR
            if not (0x0001 <= quantity and quantity <= 0x7d): # Validate quantity. Up to 125 according to protocol specs
                # Exception Response with code 0x03 (Illegal Data Value)
                return smb.ModbusPDU03ReadHoldingRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value) if function_code == 0x03 else smb.ModbusPDU04ReadInputRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value)
            elif not self._device.check_addr(mem_offset.value, address, quantity): # Validate addresses. All addresses must be mapped in the device.
                # Exception Response with code 0x02 (Illegal Data Address)
                return smb.ModbusPDU03ReadHoldingRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value) if function_code == 0x03 else smb.ModbusPDU04ReadInputRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
            else:
                # Read register values
                values = [self._device.read_word(mem_offset.value + a) for a in range(address, address + quantity)]
                return smb.ModbusPDU03ReadHoldingRegistersResponse(registerVal=values) if function_code == 0x03 else smb.ModbusPDU04ReadInputRegistersResponse(registerVal=values)
        except AssertionError:
            # Exception Response with code 0x04 (Server Failure)
            return smb.ModbusPDU03ReadHoldingRegistersError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value) if function_code == 0x03 else smb.ModbusPDU04ReadInputRegistersError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_WR_SCO(self, function_code : int = 0x05, request_pdu : Optional[smb.ModbusPDU05WriteSingleCoilRequest] = None) -> Packet:
        '''Write Single Coil Request'''
        try:
            assert request_pdu is not None
            address : int = request_pdu.outputAddr
            value : int = request_pdu.outputValue
            if value not in MODBUS_WRITE_COIL_VALUES.keys(): # Value is not 'ON' (0xFF00) or 'OFF' (0x0000)
                # Exception Response with code 0x03 (Illegal Data Value)
                return smb.ModbusPDU05WriteSingleCoilError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value)
            elif not self._device.check_addr(ModbusMemmap.CO.value, address, 1): # Validate address
                # Exception Response with code 0x02 (Illegal Data Address)
                return smb.ModbusPDU05WriteSingleCoilError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
            else:
                self._device.write_bool(ModbusMemmap.CO.value + address, MODBUS_WRITE_COIL_VALUES[value])
                return smb.ModbusPDU05WriteSingleCoilResponse(outputAddr=address, outputValue=value)
        except AssertionError:
            # Exception Response with code 0x04 (Server Failure)
            return smb.ModbusPDU05WriteSingleCoilError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_WR_SHR(self, function_code : int = 0x06, request_pdu : Optional[smb.ModbusPDU06WriteSingleRegisterRequest] = None) -> Packet:
        '''Write Single Register Request'''
        try:
            assert request_pdu is not None
            address : int = request_pdu.registerAddr
            value : int = request_pdu.registerValue
            if not self._device.check_addr(ModbusMemmap.HR.value, address, 1): # Validate address
                # Exception Response with code 0x02 (Illegal Data Address)
                return smb.ModbusPDU06WriteSingleRegisterError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
            else:
                self._device.write_word(ModbusMemmap.HR.value + address, value)
                return smb.ModbusPDU06WriteSingleRegisterResponse(registerAddr=address, registerValue=value)
        except AssertionError:
            # Exception Response with code 0x04 (Server Failure)
            return smb.ModbusPDU06WriteSingleRegisterError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_SerialOnly(self, function_code : int = 0x07, request_pdu : Optional[Packet] = None) -> Packet:
        'Handle request meant for serial line only (No TCP)'
        appropriate_response : dict = {
            0x07 : smb.ModbusPDU07ReadExceptionStatusError,
            0x08 : smb.ModbusPDU08DiagnosticsError,
            0x0b : smb.ModbusPDU0BGetCommEventCounterError,
            0x0c : smb.ModbusPDU0CGetCommEventLogError,
            0x11 : smb.ModbusPDU11ReportSlaveIdError
        }
        return appropriate_response[function_code](exceptCode=ModbusErrorCode.ILLEGAL_FUNCTION_CODE.value)

    def _mb_indication_WR_MCO(self, function_code : int = 0x0f, request_pdu : Optional[smb.ModbusPDU0FWriteMultipleCoilsRequest] = None) -> Packet:
        'Write Multiple Coils Request'
        try:
            assert request_pdu is not None
            address : int = request_pdu.startAddr
            quantity : int = request_pdu.quantityOutput
            count : int = request_pdu.byteCount
            values : list[int] = request_pdu.outputsValue # Coil values are a list of bytes, with each byte representing the desired state of up to eight coils, one per bit
            if not ((0x0001 <= quantity and quantity <= 0x07b0) and count == ceil(float(quantity) / 8.0)): # Validate quantity according to Modbus specification
                # Exception Response with code 0x03
                return smb.ModbusPDU0FWriteMultipleCoilsError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value)
            elif not self._device.check_addr(ModbusMemmap.CO.value, address, quantity): # Validate addresses. All addresses must be mapped in the device
                # Exception Response with code 0x02
                return smb.ModbusPDU0FWriteMultipleCoilsError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
            else:
                coilvals = 0
                while len(values):
                    coilvals <<= 8
                    coilvals += values.pop()
                for offset in range(quantity):
                    self._device.write_bool(ModbusMemmap.CO.value + address + offset, bool(coilvals & 0b1))
                    coilvals >>= 1
                return smb.ModbusPDU0FWriteMultipleCoilsResponse(startAddr=address, quantityOutput=quantity)
        except AssertionError:
            # Exception Response with code 0x04
            return smb.ModbusPDU0FWriteMultipleCoilsError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_WR_MHR(self, function_code : int = 0x10, request_pdu : Optional[smb.ModbusPDU10WriteMultipleRegistersRequest] = None) -> Packet:
        'Write Multiple Registers Request'
        try:
            assert request_pdu is not None
            address : int = request_pdu.startAddr
            quantity : int = request_pdu.quantityRegisters
            count : int = request_pdu.byteCount
            values : list[int] = request_pdu.outputsValue
            if not ((0x0001 <= quantity and quantity <= 0x007b) and count == (quantity * 2) and quantity == len(values)): # Validate quantity
                # Exception Response with code 0x03
                return smb.ModbusPDU10WriteMultipleRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value)
            elif not self._device.check_addr(ModbusMemmap.HR.value, address, quantity): # Validate addresses. All addresses must be mapped in the device.
                # Exception Response with code 0x02
                return smb.ModbusPDU10WriteMultipleRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
            else:
                for offset in range(quantity):
                    self._device.write_word(ModbusMemmap.HR.value + address + offset, values[offset])
                return smb.ModbusPDU10WriteMultipleRegistersResponse(startAddr=address, quantityRegisters=quantity)
        except AssertionError:
            # Exception Response with code 0x04
            return smb.ModbusPDU10WriteMultipleRegistersError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_FileRecords(self, function_code : int = 0x14, request_pdu : Optional[Packet] = None) -> Packet:
        'On File records requests, respond with "Server Busy", as we are ont going to support file records'
        return smb.ModbusPDU14ReadFileRecordError(exceptCode=ModbusErrorCode.SERVER_BUSY.value) if function_code == 0x14 else smb.ModbusPDU15WriteFileRecordError(exceptCode=ModbusErrorCode.SERVER_BUSY.value)

    def _mb_indication_WR_MASKHR(self, function_code : int = 0x16, request_pdu : Optional[smb.ModbusPDU16MaskWriteRegisterRequest] = None) -> Packet:
        'Mask Write Register Request'
        try:
            assert request_pdu is not None
            address : int = request_pdu.refAddr
            andmask : int = request_pdu.andMask
            ormask : int = request_pdu.orMask
            if not self._device.check_addr(ModbusMemmap.HR.value, address, 1): # Validate Address
                # Exception Response with code 0x02
                return smb.ModbusPDU16MaskWriteRegisterError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
            current = self._device.read_word(ModbusMemmap.HR.value + address)
            self._device.write_word(ModbusMemmap.HR.value + address, ((current & andmask) | (ormask and (andmask ^ 0xffff))) & 0xffff)
            return smb.ModbusPDU16MaskWriteRegisterResponse(refAddr=address, andMask=andmask, orMask=ormask)
        except AssertionError:
            # Exception Response with code 0x04
            return smb.ModbusPDU16MaskWriteRegisterError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_RW_MHR(self, function_code : int = 0x17, request_pdu : Optional[smb.ModbusPDU17ReadWriteMultipleRegistersRequest] = None) -> Packet:
        'Read/Write Multiple registers Request'
        try:
            assert request_pdu is not None
            rd_address : int = request_pdu.readStartingAddr
            rd_quantity : int = request_pdu.readQuantityRegisters
            wr_address : int = request_pdu.writeStartingAddress
            wr_quantity : int = request_pdu.writeQuantityRegisters
            count : int = request_pdu.byteCount
            wr_values : list[int] = request_pdu.writeRegistersValue
            if not (0x0001 <= rd_quantity and rd_quantity <= 0x7d and 0x0001 <= wr_quantity and wr_quantity <= 0x0079 and count == (wr_quantity * 2)): # Validate quantities
                # Exception Response with code 0x03
                return smb.ModbusPDU17ReadWriteMultipleRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value)
            elif not (self._device.check_addr(ModbusMemmap.HR.value, rd_address, rd_quantity) and self._device.check_addr(ModbusMemmap.HR.value, wr_address, wr_quantity)): # Validate addresses. All addresses must be mapped in the device, 2 bytes per requested 16-bit value
                # Exception Response with code 0x02
                return smb.ModbusPDU17ReadWriteMultipleRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
            else:
                # Read register values
                values = [self._device.read_word(ModbusMemmap.HR.value + a) for a in range(rd_address, rd_address + rd_quantity)]
                # Write register values
                for offset in range(wr_quantity):
                    self._device.write_word(ModbusMemmap.HR.value + wr_address + offset, wr_values[offset])
                return smb.ModbusPDU17ReadWriteMultipleRegistersResponse(registerVal=values)
        except AssertionError:
            # Exception Response with code 0x04
            return smb.ModbusPDU17ReadWriteMultipleRegistersError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_FIFO_QR(self, function_code : int = 0x18, request_pdu : Optional[smb.ModbusPDU18ReadFIFOQueueRequest] = None) -> Packet:
        'Read FIFO Queue Request'
        try:
            assert request_pdu is not None
            fifo : int = request_pdu.FIFOPointerAddr
            if not self._device.check_addr(ModbusMemmap.HR.value, fifo, 1): # Validate FIFO pointer address
                # Exception Response with code 0x02
                return smb.ModbusPDU18ReadFIFOQueueError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
            count = self._device.read_word(ModbusMemmap.HR.value + fifo)
            if count > 31:
                # Exception Response with code 0x03
                return smb.ModbusPDU18ReadFIFOQueueError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value)
            elif not self._device.check_addr(ModbusMemmap.HR.value, fifo + 1, count): # Validate queue addresses (2 bytes per value)
                # Exception Response with code 0x02
                return smb.ModbusPDU18ReadFIFOQueueError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
            else:
                # Read queue
                values : list[int] = [self._device.read_word(ModbusMemmap.HR.value + fifo + offset) for offset in range(1, count + 1)]
                return smb.ModbusPDU18ReadFIFOQueueResponse(FIFOCount=count, FIFOVal=values)
        except AssertionError:
            # Exception Response with code 0x04
            return smb.ModbusPDU18ReadFIFOQueueError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_EIT(self, function_code : int = 0x2b, request_pdu : Optional[smb.ModbusPDU2B0EReadDeviceIdentificationRequest] = None) -> Packet:
        'Encapsulated Interface Transport (0x2B / 0x0E) Read Device Identification'
        try:
            assert request_pdu is not None
            readcode : int = request_pdu.readCode
            ModbusReadCodes(readcode)
            device_id : dict[int, str] = self._device.device_id
            if readcode < ModbusReadCodes.SPECIFIC.value:
                # Stream access available device information (codes 0x01 - 0x03)
                respdu = smb.ModbusPDU2B0EReadDeviceIdentificationResponse(readCode=readcode, conformityLevel=0x80 + readcode, objCount=3 + (2 if readcode > ModbusReadCodes.BASIC.value else 0), nextObjId=ModbusDeviceID.VENDOR_NAME.value)
                # BASIC values
                respdu/= smb.ModbusObjectId(id=ModbusDeviceID.VENDOR_NAME.value, value=device_id[ModbusDeviceID.VENDOR_NAME.value])
                respdu/= smb.ModbusObjectId(id=ModbusDeviceID.PRODUCT_CODE.value, value=device_id[ModbusDeviceID.PRODUCT_CODE.value])
                respdu/= smb.ModbusObjectId(id=ModbusDeviceID.MAJOR_MINOR_REVISION.value, value=device_id[ModbusDeviceID.MAJOR_MINOR_REVISION.value])
                if readcode > ModbusReadCodes.BASIC.value:
                    # REGULAR values
                    respdu/= smb.ModbusObjectId(id=ModbusDeviceID.PRODUCT_NAME.value, value=device_id[ModbusDeviceID.PRODUCT_NAME.value])
                    respdu/= smb.ModbusObjectId(id=ModbusDeviceID.MODEL_NAME.value, value=device_id[ModbusDeviceID.MODEL_NAME.value])
                return respdu
            else:
                objectid : int = request_pdu.objectId
                if objectid not in device_id.keys():
                    # Object not supported
                    # Exception Response with code 0x02
                    return smb.ModbusPDU2B0EReadDeviceIdentificationError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
                # Individual access to one specific identification object
                respdu = smb.ModbusPDU2B0EReadDeviceIdentificationResponse(readCode=readcode, conformityLevel=0x80 + readcode - 1, objCount=1, nextObjId=objectid)
                respdu/= smb.ModbusObjectId(id=objectid, value=device_id[objectid])
                return respdu
        except ValueError:
            return smb.ModbusPDU2B0EReadDeviceIdentificationError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value)
        except AssertionError:
            return smb.ModbusPDU2B0EReadDeviceIdentificationError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def run(self) -> None:
        isalive = True
        sock = self._sock
        indication_handlers : dict[int, Callable[[int, Optional[Packet]], Packet]] = {
            0x01 : self._mb_indication_RDCO_RDDI,
            0x02 : self._mb_indication_RDCO_RDDI,
            0x03 : self._mb_indication_RDHR_RDIR,
            0x04 : self._mb_indication_RDHR_RDIR,
            0x05 : self._mb_indication_WR_SCO,
            0x06 : self._mb_indication_WR_SHR,
            0x0f : self._mb_indication_WR_MCO,
            0x10 : self._mb_indication_WR_MHR,
            0x14 : self._mb_indication_FileRecords,
            0x15 : self._mb_indication_FileRecords,
            0x16 : self._mb_indication_WR_MASKHR,
            0x17 : self._mb_indication_RW_MHR,
            0x18 : self._mb_indication_FIFO_QR,
            0x2b : self._mb_indication_EIT
        }
        indication_handlers.update({x: self._mb_indication_SerialOnly for x in [0x07, 0x08, 0x0b, 0x0c, 0x11]})
        while isalive and not self.terminate:
            try:
                data = sock.recv(MODBUS_MAX_LENGTH)
                request : smb.ModbusADURequest = smb.ModbusADURequest(data)
                try:
                    # Verify MBAP Header
                    assert all(x in request.fields for x in ['transId', 'protoId', 'len', 'unitId'])
                    assert request.protoId == 0x0000 # MODBUS
                except AssertionError:
                    # Error on MBAP => MB indication discarded
                    continue
                transaction_id = request.transId
                unit_id = request.unitId
                request_pdu = request.payload
                function_code = request_pdu.funcCode
                try:
                    # Validate the function code
                    assert not isinstance(request_pdu, smb.ModbusPDUUserDefinedFunctionCodeRequest)
                    assert function_code in indication_handlers.keys() # Check for supported Modbus indications
                    assert bytes(request_pdu)[1] == 0x0e if function_code == 0x2b else True # Check for device identification if function code is Encapsulated Interface Transport (EIT)
                except AssertionError:
                    # Illegal function code
                    rawpdu : bytes = bytes(request_pdu)
                    function_code : int = (int(rawpdu[0]) + 0x80) & 0xff if int(rawpdu[0]) < 0x80 else int(rawpdu[0]) # The response function code = the request function code + 0x80
                    # Exception Response with code 0x01 (Illegal function code)
                    response : smb.ModbusADUResponse = smb.ModbusADUResponse(transId=transaction_id, unitId=unit_id)/bytes([function_code, ModbusErrorCode.ILLEGAL_FUNCTION_CODE.value])
                    sock.send(response.build())
                    continue
                response : smb.ModbusADUResponse = smb.ModbusADUResponse(transId=transaction_id, unitId=unit_id)
                # Process the MODBUS Indication according to the corresponding code
                response /= indication_handlers[function_code](function_code, request_pdu)
                sock.send(response.build())
            except (timeout, BrokenPipeError):
                # Either there was no communication with the other end for a long period of time
                # or the connection was closed
                isalive = False
        self._sock.close()

class ModbusListener(ProtocolListener):

    def __init__(self, *args, device : DeviceBase, **kwargs):
        super().__init__(*args, device=device, **kwargs)
        self._handlers : list[ModbusHandler] = list()
    
    def run(self):
        listening_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        listening_sock.bind(('', MODBUS_TCP_PORT))
        listening_sock.settimeout(2)
        listening_sock.listen()
        while not self._terminate:
            try:
                incoming, iaddr = listening_sock.accept()
                incoming.settimeout(MODBUS_TIMEOUT)
                new_handler = ModbusHandler(device=self._device, connection=incoming)
                self._handlers.append(new_handler)
                new_handler.start()
            except timeout:
                pass
        while any(hnd.is_alive() for hnd in self._handlers):
            for hnd in self._handlers:
                hnd.terminate = True
                hnd.join(1)
        listening_sock.close()

class ModbusClient:
    """
    Modbus TCP Client

    Uses a TCP socket to connect to a remote Modbus device, and provides
    the funcitonality to interact with the Coils, Direct Inputs, Input
    Registers, and Holding Registers.

    All the supported write requests are for single values. That is, this
    class supports the Modbus function codes 0x05 and 0x06 for writing
    values in the device.
    """
    
    def __init__(self, ipaddr : str):
        """
        Instantiates a new Modbus TCP Client with the socket used to connect to the device.

        :param ipaddr: The IPv4 address of the device.
        :type ipaddr: str
        """
        self._sock : socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        self._sock.settimeout(MODBUS_TIMEOUT)
        self._ipaddr : str = ipaddr
    
    def __str__(self) -> str:
        return f'Modbus TCP Client ({self._ipaddr}:{MODBUS_TCP_PORT})'
    
    def close(self):
        """
        Close the connection with the device.
        """
        try:
            self._sock.shutdown(SHUT_RDWR)
            self._sock.close()
        except OSError as e:
            sys.stderr.write(f'Error closing socket: {str(e)}')
            sys.stderr.flush()
    
    def connect(self):
        """
        Attempt to connect to the device
        """
        connected : bool = False
        retries : int = 0
        max_retries : int = 5
        while not connected and retries < max_retries:
            try:
                self._sock.connect((self._ipaddr, MODBUS_TCP_PORT))
                connected = True
            except timeout:
                sys.stderr.write(f'Unable to connect to {self._ipaddr}:{MODBUS_TCP_PORT}')
                sys.stderr.flush()
                retries += 1
        if not connected:
            sys.stderr.write(f'Failed to establish connection after {max_retries} attempts.')
            sys.stderr.flush()
    
    def reconnect(self):
        """
        Attempt to reconnect to the device
        """
        self.close()
        self.connect()
    
    def send_float(self, address : int, value : float, transaction : int = 0x01, unit : int = 0x01):
        """
        Send a float value to a Modbus holding register in the device.

        :param address: The address of the holding register in the device. Must be in the range [0, 65534].
        :type address: int
        :param value: The float value to store in the holding register.
        :type value: float
        :param transaction: The Modbus transaction ID to use in the request. Must be in the range [0, 255], defaults to 0x00.
        :type transaction: int, optional
        :param unit: The Modbus unit ID to use in the request. Must be in the range [0, 255], defaults to 0x00.
        :type unit: int, optional

        :raises AssertionError: If a parameter value is out of range or if a Modbus exception is received as a result of the transaction.
        :raises struct.error: If the float value cannot be encoded using the IEEE 754 16-bit half precision format.
        :raises BrokenPipe: If the socket disconnects from the device.
        :raises socket.timeout: If a socket timeout occurs.
        """
        assert address >= 0 and address <= 65534, f'Address out of range ({address})'
        assert transaction >= 0 and transaction <= 255, f'Transaction ID out of range ({transaction})'
        assert unit >= 0 and unit <= 255, f'Unid ID out of range ({unit})'
        mb_value : int = struct.unpack('<H',struct.pack('<e', value))[0]
        request : smb.ModbusADURequest = smb.ModbusADURequest(transId=transaction, unitId=unit)
        request /= smb.ModbusPDU06WriteSingleRegisterRequest(registerAddr=address, registerValue=mb_value)
        self._sock.send(request.build())
        buffer : bytes = self._sock.recv(MODBUS_MAX_LENGTH)
        response : smb.ModbusADUResponse = smb.ModbusADUResponse(buffer)
        pdu = response.payload
        assert isinstance(pdu, smb.ModbusPDU06WriteSingleRegisterResponse), f'Modbus exception: 0x{pdu.exceptCode:02x}' if isinstance(pdu, smb.ModbusPDU06WriteSingleRegisterError) else f'Received unknown payload: {bytes(pdu)}'

    def read_float(self, mapping : ModbusMemmap, address : int, transaction : int = 0x01, unit : int = 0x01) -> float:
        """
        Read a float value from the Modbus device registers.

        :param mapping: The Modbus memory mapping type to read from (ModbusMemmap.IR for holding registers or ModbusMemmap.HR for input registers).
        :type mapping: ModbusMemmap
        :param address: The address of the register in the device. Must be in the range [0, 65534].
        :type address: int
        :param transaction: The Modbus transaction ID to use in the request. Must be in the range [0, 255]. (default: 0x00)
        :type transaction: int
        :param unit: The Modbus unit ID to use in the request. Must be in the range [0, 255]. (default: 0x00)
        :type unit: int
        :return: The float value read from the device.
        :rtype: float
        :raises AssertionError: If a parameter value is out of range or if a Modbus exception is received as a result of the transaction.
        :raises struct.error: If the float value cannot be unpacked from the received data.
        :raises socket.timeout: If a socket timeout occurs during the operation.
        :raises BrokenPipe: If the socket disconnects from the device.
        """
        assert address >= 0 and address <= 65534, f'Address out of range ({address})'
        assert mapping in [ModbusMemmap.IR, ModbusMemmap.HR], f'Invalid memory mapping ({mapping.value})'
        assert transaction >= 0 and transaction <= 255, f'Transaction ID out of range ({transaction})'
        assert unit >= 0 and unit <= 255, f'Unid ID out of range ({unit})'
        pdus = {
            ModbusMemmap.IR: smb.ModbusPDU03ReadHoldingRegistersRequest,
            ModbusMemmap.HR: smb.ModbusPDU04ReadInputRegistersRequest
        }
        request : smb.ModbusADURequest = smb.ModbusADURequest(transId=transaction, unitId=unit)
        request /= pdus[mapping](startAddr=address, quantity=1)
        self._sock.send(request.build())
        buffer : bytes = self._sock.recv(MODBUS_MAX_LENGTH)
        response : smb.ModbusADUResponse = smb.ModbusADUResponse(buffer)
        pdu = response.payload
        assert isinstance(pdu, (smb.ModbusPDU03ReadHoldingRegistersResponse, smb.ModbusPDU04ReadInputRegistersResponse)), f'Modbus exception: 0x{pdu.exceptCode:02x}' if isinstance(pdu, (smb.ModbusPDU03ReadHoldingRegistersError, smb.ModbusPDU04ReadInputRegistersError)) else f'Received unknown payload: {bytes(pdu)}'
        raw : int = pdu.registerVal[0]
        return struct.unpack('<e', struct.pack('<H', raw))[0]
    
    def send_word(self, address : int, value : int, transaction : int = 0x01, unit : int = 0x01):
        """
        Send a 16-bit integer value to a Modbus holding register in the device.

        :param address: The address of the register in the device. Must be in the range [0, 65534].
        :type address: int
        :param value: The 16-bit integer value to store in the holding register. Must be in the range [0, 65535].
        :type value: int
        :param transaction: The Modbus transaction ID to use in the request. Must be in the range [0, 255], defaults to 0x00.
        :type transaction: int, optional
        :param unit: The Modbus unit ID to use in the request. Must be in the range [0, 255], defaults to 0x00.
        :type unit: int, optional
        :raises AssertionError: If a parameter value is out of range or if a Modbus exception is received as a result of the transaction.
        :raises socket.timeout: If a socket timeout occurs during the operation.
        :raises BrokenPipe: If the socket disconnects from the device.
        """
        assert address >= 0 and address <= 65534, f'Address out of range ({address})'
        assert value >= 0 and value <= 65535, f'Value out of range ({value})'
        assert transaction >= 0 and transaction <= 255, f'Transaction ID out of range ({transaction})'
        assert unit >= 0 and unit <= 255, f'Unid ID out of range ({unit})'
        request : smb.ModbusADURequest = smb.ModbusADURequest(transId = transaction, unitId = unit)
        request /= smb.ModbusPDU06WriteSingleRegisterRequest(registerAddr = address, registerValue = value)
        self._sock.send(request.build())
        buffer : bytes = self._sock.recv(MODBUS_MAX_LENGTH)
        response : smb.ModbusADUResponse = smb.ModbusADUResponse(buffer)
        pdu = response.payload
        assert isinstance(pdu, smb.ModbusPDU06WriteSingleRegisterResponse), f'Modbus exception: 0x{pdu.exceptCode:02x}' if isinstance(pdu, smb.ModbusPDU06WriteSingleRegisterError) else f'Received unknown payload: {bytes(pdu)}'

    def read_word(self, mapping : ModbusMemmap, address : int, transaction : int = 0x01, unit : int = 0x01) -> int:
        """
        Read a 16-bit integer value from the Modbus device registers.

        :param mapping: The Modbus memory mapping type to read from (ModbusMemmap.IR for holding registers or ModbusMemmap.HR for input registers).
        :type mapping: ModbusMemmap
        :param address: The address of the register in the device. Must be in the range [0, 65534].
        :type address: int
        :param transaction: The Modbus transaction ID to use in the request. Must be in the range [0, 255]. (default: 0x00)
        :type transaction: int
        :param unit: The Modbus unit ID to use in the request. Must be in the range [0, 255]. (default: 0x00)
        :type unit: int
        :return: The 16-bit integer value read from the device.
        :rtype: int
        :raises AssertionError: If a parameter value is out of range or if a Modbus exception is received as a result of the transaction.
        :raises struct.error: If the float value cannot be unpacked from the received data.
        :raises socket.timeout: If a socket timeout occurs during the operation.
        :raises BrokenPipe: If the socket disconnects from the device.
        """
        assert address >= 0 and address <= 65534, f'Address out of range ({address})'
        assert mapping in [ModbusMemmap.IR, ModbusMemmap.HR], f'Invalid memory mapping ({mapping.value})'
        assert transaction >= 0 and transaction <= 255, f'Transaction ID out of range ({transaction})'
        assert unit >= 0 and unit <= 255, f'Unid ID out of range ({unit})'
        pdus = {
            ModbusMemmap.HR: smb.ModbusPDU03ReadHoldingRegistersRequest,
            ModbusMemmap.IR: smb.ModbusPDU04ReadInputRegistersRequest
        }
        request : smb.ModbusADURequest = smb.ModbusADURequest(transId=transaction, unitId=unit)
        request /= pdus[mapping](startAddr=address, quantity=1)
        self._sock.send(request.build())
        buffer : bytes = self._sock.recv(MODBUS_MAX_LENGTH)
        response : smb.ModbusADUResponse = smb.ModbusADUResponse(buffer)
        pdu = response.payload
        assert isinstance(pdu, (smb.ModbusPDU03ReadHoldingRegistersResponse, smb.ModbusPDU04ReadInputRegistersResponse)), f'Modbus exception: 0x{pdu.exceptCode:02x}' if isinstance(pdu, (smb.ModbusPDU03ReadHoldingRegistersError, smb.ModbusPDU04ReadInputRegistersError)) else f'Received unknown payload: {bytes(pdu)}'
        value : int = pdu.registerVal[0]
        return value

    def send_bool(self, address : int, value : bool, transaction : int = 0x01, unit : int = 0x01):
        """
        Send a boolean value to a Modbus coil in the device.

        :param address: The address of the register in the device. Must be in the range [0, 65534].
        :type address: int
        :param value: The boolean value to use while setting the coil state.
        :type value: bool
        :param transaction: The Modbus transaction ID to use in the request. Must be in the range [0, 255], defaults to 0x00.
        :type transaction: int, optional
        :param unit: The Modbus unit ID to use in the request. Must be in the range [0, 255], defaults to 0x00.
        :type unit: int, optional
        :raises AssertionError: If a parameter value is out of range or if a Modbus exception is received as a result of the transaction.
        :raises socket.timeout: If a socket timeout occurs during the operation.
        :raises BrokenPipe: If the socket disconnects from the device.
        """
        assert address >= 0 and address <= 65534, f'Address out of range ({address})'
        assert transaction >= 0 and transaction <= 255, f'Transaction ID out of range ({transaction})'
        assert unit >= 0 and unit <= 255, f'Unid ID out of range ({unit})'
        request : smb.ModbusADURequest = smb.ModbusADURequest(transId = transaction, unitId = unit)
        request /= smb.ModbusPDU05WriteSingleCoilRequest(outputAddr = address, outputValue = 0xFF00 if value else 0x0000)
        self._sock.send(request.build())
        buffer : bytes = self._sock.recv(MODBUS_MAX_LENGTH)
        response : smb.ModbusADUResponse = smb.ModbusADUResponse(buffer)
        pdu = response.payload
        assert isinstance(pdu, smb.ModbusPDU05WriteSingleCoilResponse), f'Modbus exception: 0x{pdu.exceptCode:02x}' if isinstance(pdu, smb.ModbusPDU05WriteSingleCoilError) else f'Received unknown payload: {bytes(pdu)}'

    def read_bool(self, mapping : ModbusMemmap, address : int, transaction : int = 0x01, unit : int = 0x01) -> bool:
        """
        Read a boolean value from the Modbus device coils/discrete inputs.

        :param mapping: The Modbus memory mapping type to read from (ModbusMemmap.CO for coils or ModbusMemmap.DI for discrete inputs).
        :type mapping: ModbusMemmap
        :param address: The address of the register in the device. Must be in the range [0, 65534].
        :type address: int
        :param transaction: The Modbus transaction ID to use in the request. Must be in the range [0, 255]. (default: 0x00)
        :type transaction: int
        :param unit: The Modbus unit ID to use in the request. Must be in the range [0, 255]. (default: 0x00)
        :type unit: int
        :return: The voolean value read from the device.
        :rtype: bool
        :raises AssertionError: If a parameter value is out of range or if a Modbus exception is received as a result of the transaction.
        :raises struct.error: If the float value cannot be unpacked from the received data.
        :raises socket.timeout: If a socket timeout occurs during the operation.
        :raises BrokenPipe: If the socket disconnects from the device.
        """
        assert address >= 0 and address <= 65534, f'Address out of range ({address})'
        assert mapping in [ModbusMemmap.CO, ModbusMemmap.DI], f'Invalid memory mapping ({mapping.value})'
        assert transaction >= 0 and transaction <= 255, f'Transaction ID out of range ({transaction})'
        assert unit >= 0 and unit <= 255, f'Unid ID out of range ({unit})'
        pdus = {
            ModbusMemmap.CO: smb.ModbusPDU01ReadCoilsRequest,
            ModbusMemmap.DI: smb.ModbusPDU02ReadDiscreteInputsRequest
        }
        request : smb.ModbusADURequest = smb.ModbusADURequest(transId=transaction, unitId=unit)
        request /= pdus[mapping](startAddr=address, quantity=1)
        self._sock.send(request.build())
        buffer : bytes = self._sock.recv(MODBUS_MAX_LENGTH)
        response : smb.ModbusADUResponse = smb.ModbusADUResponse(buffer)
        pdu = response.payload
        assert isinstance(pdu, (smb.ModbusPDU01ReadCoilsResponse, smb.ModbusPDU02ReadDiscreteInputsResponse)), f'Modbus exception: 0x{pdu.exceptCode:02x}' if isinstance(pdu, (smb.ModbusPDU01ReadCoilsError, smb.ModbusPDU02ReadDiscreteInputsError)) else f'Received unknown payload: {bytes(pdu)}'
        value : int = pdu.coilStatus[0] if isinstance(pdu, smb.ModbusPDU01ReadCoilsResponse) else pdu.inputStatus[0]
        return value != 0

    def read_coil(self, address : int, transaction : int = 0x01, unit : int = 0x01) -> bool:
        return self.read_bool(ModbusMemmap.CO, address, transaction, unit)
    
    def read_discrete_input(self, address : int, transaction : int = 0x01, unit : int = 0x01) -> bool:
        return self.read_bool(ModbusMemmap.DI, address, transaction, unit)
    
    def read_holding_float(self, address : int, transaction : int = 0x01, unit : int = 0x01) -> float:
        return self.read_float(ModbusMemmap.HR, address, transaction, unit)
    
    def read_holding_word(self, address : int, transaction : int = 0x01, unit : int = 0x01) -> int:
        return self.read_word(ModbusMemmap.HR, address, transaction, unit)
    
    def read_input_float(self, address : int, transaction : int = 0x01, unit : int = 0x01) -> float:
        return self.read_float(ModbusMemmap.IR, address, transaction, unit)
    
    def read_input_word(self, address : int, transaction : int = 0x01, unit : int = 0x01) -> int:
        return self.read_word(ModbusMemmap.IR, address, transaction, unit)
