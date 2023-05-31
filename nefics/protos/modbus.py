#!/usr/bin/env python3

# Standard imports
from math import ceil
from enum import Enum
from threading import Thread
from socket import socket, timeout, AF_INET, SOCK_STREAM, IPPROTO_TCP
# Scapy imports
from scapy.packet import Packet
import scapy.contrib.modbus as smb
# NEFICS imports
from nefics.modules.devicebase import IEDBase, ProtocolListener

MODBUS_TCP_PORT = 502
MODBUS_MAX_LENGTH = 260

MODBUS_WRITE_COIL_VALUES = {
    0x0000: False,
    0xFF00: True
}

class ModbusErrorCode(Enum):
    'Modbus Exception codes'
    ILLEGAL_FUNCTION_CODE : int = 0x01
    ILLEGAL_DATA_ADDRESS : int = 0x02
    ILLEGAL_DATA_VALUE : int = 0x03
    SERVER_FAILURE : int = 0x04
    ACKNOWLEDGE : int = 0x05
    SERVER_BUSY : int = 0x06
    GATEWAY_PATH_PROBLEM : int = 0x07
    GATEWAY_NO_RESPONSE : int = 0x08

class ModbusMemmap(Enum):
    '''Emulated memory offsets for Modbus'''
    DI : int = 0x00000
    CO : int = 0x10000
    IR : int = 0x20000
    HR : int = 0x30000

class ModbusReadCodes(Enum):
    'Modbus Device ID Read Codes'
    BASIC : int = 0x01
    REGULAR : int = 0x02
    EXTENDED : int = 0x03
    SPECIFIC : int = 0x04

class ModbusDeviceID(Enum):
    'Modbus Device ID values'
    VENDOR_NAME : int = 0x00
    PRODUCT_CODE : int = 0x01
    MAJOR_MINOR_REVISION : int = 0x02
    VENDOR_URL : int = 0x03
    PRODUCT_NAME : int = 0x04
    MODEL_NAME : int = 0x05
    USER_APP_NAME : int = 0x06

class ModbusHandler(Thread):

    def __init__(self, *args, device : IEDBase, connection : socket, **kwargs):
        super().__init__(*args, **kwargs)
        self._device = device
        self._sock = connection
        self._terminate = False
    
    @property
    def terminate(self) -> bool:
        return self._terminate
    
    @terminate.setter
    def terminate(self, value : bool = False):
        self._terminate = value
    
    def _mb_indication_RDCO_RDDI(self, function_code : int = 0x01, request_pdu : Packet = None) -> Packet:
        '''Read coils request / Read Discrete Input Request'''
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
            try:
                coils = 0
                for addr in range((mem_offset.value + address) + quantity - 1, (mem_offset.value + address) - 1, -1):
                    coils += 1 if self._device.read_bool(addr) else 0
                    coils <<= 1
                status = []
                while coils > 0:
                    status.append(coils & 0xff)
                    coils >>= 8
                return smb.ModbusPDU01ReadCoilsResponse(coilStatus=status) if function_code == 0x01 else smb.ModbusPDU02ReadDiscreteInputsResponse(inputStatus=status)
            except AssertionError:
                # Exception Response with code 0x04 (Serve Failure)
                return smb.ModbusPDU01ReadCoilsError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value) if function_code == 0x01 else smb.ModbusPDU02ReadDiscreteInputsError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_RDHR_RDIR(self, function_code : int = 0x03, request_pdu : Packet = None) -> Packet:
        '''Read Holding Registers / Input Registers'''
        address : int = request_pdu.startAddr
        quantity : int = request_pdu.quantity
        mem_offset : ModbusMemmap = ModbusMemmap.HR if function_code == 0x03 else ModbusMemmap.IR
        if not (0x0001 <= quantity and quantity <= 0x7d): # Validate quantity. Up to 125 according to protocol specs
            # Exception Response with code 0x03 (Illegal Data Value)
            return smb.ModbusPDU03ReadHoldingRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value) if function_code == 0x03 else smb.ModbusPDU04ReadInputRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value)
        elif not self._device.check_addr(mem_offset.value, address, quantity * 2): # Validate addresses. All addresses must be mapped in the device. Double the quantity due to 16-bit data.
            # Exception Response with code 0x02 (Illegal Data Address)
            return smb.ModbusPDU03ReadHoldingRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value) if function_code == 0x03 else smb.ModbusPDU04ReadInputRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
        else:
            try:
                # Read register values
                values = [self._device.read_word(mem_offset.value + a) for a in range(address, address + (2 * quantity), 2)]
                return smb.ModbusPDU03ReadHoldingRegistersResponse(registerVal=values) if function_code == 0x03 else smb.ModbusPDU04ReadInputRegistersResponse(registerVal=values)
            except AssertionError:
                # Exception Response with code 0x04 (Server Failure)
                return smb.ModbusPDU03ReadHoldingRegistersError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value) if function_code == 0x03 else smb.ModbusPDU04ReadInputRegistersError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_WR_SCO(self, function_code : int = 0x05, request_pdu : smb.ModbusPDU05WriteSingleCoilRequest = None) -> Packet:
        '''Write Single Coil Request'''
        address : int = request_pdu.outputAddr
        value : int = request_pdu.outputValue
        if value not in MODBUS_WRITE_COIL_VALUES.keys(): # Value is not 'ON' (0xFF00) or 'OFF' (0x0000)
            # Exception Response with code 0x03 (Illegal Data Value)
            return smb.ModbusPDU05WriteSingleCoilError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value)
        elif not self._device.check_addr(ModbusMemmap.CO.value, address, 1): # Validate address
            # Exception Response with code 0x02 (Illegal Data Address)
            return smb.ModbusPDU05WriteSingleCoilError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
        else:
            try:
                self._device.write_bool(ModbusMemmap.CO.value + address, MODBUS_WRITE_COIL_VALUES[value])
                return smb.ModbusPDU05WriteSingleCoilResponse(outputAddr=address, outputValue=value)
            except AssertionError:
                # Exception Response with code 0x04 (Server Failure)
                return smb.ModbusPDU05WriteSingleCoilError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_WR_SHR(self, function_code : int = 0x06, request_pdu : smb.ModbusPDU06WriteSingleRegisterRequest = None) -> Packet:
        '''Write Single Register Request'''
        address : int = request_pdu.registerAddr
        value : int = request_pdu.registerValue
        if not self._device.check_addr(ModbusMemmap.HR.value, address, 2): # Validate addresses (2 bytes) for a 16-bit WORD value
            # Exception Response with code 0x02 (Illegal Data Address)
            return smb.ModbusPDU06WriteSingleRegisterError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
        else:
            try:
                self._device.write_word(address, value)
                return smb.ModbusPDU06WriteSingleRegisterResponse(registerAddr=address, registerValue=value)
            except AssertionError:
                # Exception Response with code 0x04 (Server Failure)
                return smb.ModbusPDU06WriteSingleRegisterError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_SerialOnly(self, function_code : int = 0x07, request_pdu : Packet = None) -> Packet:
        'Handle request meant for serial line only (No TCP)'
        appropriate_response : dict = {
            0x07 : smb.ModbusPDU07ReadExceptionStatusError,
            0x08 : smb.ModbusPDU08DiagnosticsError,
            0x0b : smb.ModbusPDU0BGetCommEventCounterError,
            0x0c : smb.ModbusPDU0CGetCommEventLogError,
            0x11 : smb.ModbusPDU11ReportSlaveIdError
        }
        return appropriate_response[function_code](exceptCode=ModbusErrorCode.ILLEGAL_FUNCTION_CODE.value)

    def _mb_indication_WR_MCO(self, function_code : int = 0x0f, request_pdu : smb.ModbusPDU0FWriteMultipleCoilsRequest = None) -> Packet:
        'Write Multiple Coils Request'
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
            try:
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

    def _mb_indication_WR_MHR(self, function_code : int = 0x10, request_pdu : smb.ModbusPDU10WriteMultipleRegistersRequest = None) -> Packet:
        'Write Multiple Registers Request'
        address : int = request_pdu.startAddr
        quantity : int = request_pdu.quantityRegisters
        count : int = request_pdu.byteCount
        values : list[int] = request_pdu.outputsValue
        if not ((0x0001 <= quantity and quantity <= 0x007b) and count == (quantity * 2) and count == len(values)): # Validate quantity
            # Exception Response with code 0x03
            return smb.ModbusPDU10WriteMultipleRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value)
        elif not self._device.check_addr(ModbusMemmap.HR.value, address, 2 * quantity): # Validate addresses. All addresses must be mapped in the device. Twice the quantity to account for 16-bit values
            # Exception Response with code 0x02
            return smb.ModbusPDU10WriteMultipleRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
        else:
            try:
                for offset in range(quantity):
                    self._device.write_word(ModbusMemmap.HR.value + address + offset, values[offset])
                return smb.ModbusPDU10WriteMultipleRegistersResponse(startAddr=address, quantityRegisters=quantity)
            except AssertionError:
                # Exception Response with code 0x04
                return smb.ModbusPDU10WriteMultipleRegistersError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_FileRecords(self, function_code : int = 0x14, request_pdu : Packet = None) -> Packet:
        'On File records requests, respond with "Server Busy", as we are ont going to support file records'
        return smb.ModbusPDU14ReadFileRecordError(exceptCode=ModbusErrorCode.SERVER_BUSY.value) if function_code == 0x14 else smb.ModbusPDU15WriteFileRecordError(exceptCode=ModbusErrorCode.SERVER_BUSY.value)

    def _mb_indication_WR_MASKHR(self, function_code : int = 0x16, request_pdu : smb.ModbusPDU16MaskWriteRegisterRequest = None) -> Packet:
        'Mask Write Register Request'
        address : int = request_pdu.refAddr
        andmask : int = request_pdu.andMask
        ormask : int = request_pdu.orMask
        if not self._device.check_addr(ModbusMemmap.HR.value, address, 2): # Validate Addresses (2 bytes for 16-bit data)
            # Exception Response with code 0x02
            return smb.ModbusPDU16MaskWriteRegisterError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
        try:
            current = self._device.read_word(ModbusMemmap.HR.value + address)
            self._device.write_word(ModbusMemmap.HR.value + address, ((current & andmask) | (ormask and (andmask ^ 0xffff))) & 0xffff)
            return smb.ModbusPDU16MaskWriteRegisterResponse(refAddr=address, andMask=andmask, orMask=ormask)
        except AssertionError:
            # Exception Response with code 0x04
            return smb.ModbusPDU16MaskWriteRegisterError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_RW_MHR(self, function_code : int = 0x17, request_pdu : smb.ModbusPDU17ReadWriteMultipleRegistersRequest = None) -> Packet:
        'Read/Write Multiple registers Request'
        rd_address : int = request_pdu.readStartingAddr
        rd_quantity : int = request_pdu.readQuantityRegisters
        wr_address : int = request_pdu.writeStartingAddress
        wr_quantity : int = request_pdu.writeQuantityRegisters
        count : int = request_pdu.byteCount
        wr_values : list[int] = request_pdu.writeRegistersValue
        if not (0x0001 <= rd_quantity and rd_quantity <= 0x7d and 0x0001 <= wr_quantity and wr_quantity <= 0x0079 and count == (wr_quantity * 2)): # Validate quantities
            # Exception Response with code 0x03
            return smb.ModbusPDU17ReadWriteMultipleRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value)
        elif not (self._device.check_addr(ModbusMemmap.HR.value, rd_address, 2 * rd_quantity) and self._device.check_addr(ModbusMemmap.HR.value, wr_address, 2 * wr_quantity)): # Validate addresses. All addresses must be mapped in the device, 2 bytes per requested 16-bit value
            # Exception Response with code 0x02
            return smb.ModbusPDU17ReadWriteMultipleRegistersError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
        else:
            try:
                # Read register values
                values = [self._device.read_word(ModbusMemmap.HR.value + a) for a in range(rd_address, rd_address + (2 * rd_quantity), 2)]
                # Write register values
                for offset in range(0, 2 * wr_quantity, 2):
                    self._device.write_word(ModbusMemmap.HR.value + wr_address + offset, wr_values[offset // 2])
                return smb.ModbusPDU17ReadWriteMultipleRegistersResponse(registerVal=values)
            except AssertionError:
                # Exception Response with code 0x04
                return smb.ModbusPDU17ReadWriteMultipleRegistersError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_FIFO_QR(self, function_code : int = 0x18, request_pdu : smb.ModbusPDU18ReadFIFOQueueRequest = None) -> Packet:
        'Read FIFO Queue Request'
        fifo : int = request_pdu.FIFOPointerAddr
        if not self._device.check_addr(ModbusMemmap.HR.value, fifo, 2): # Validate FIFO pointer address (2 bytes)
            # Exception Response with code 0x02
            return smb.ModbusPDU18ReadFIFOQueueError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
        try:
            count = self._device.read_word(ModbusMemmap.HR.value + fifo)
            if count > 31:
                # Exception Response with code 0x03
                return smb.ModbusPDU18ReadFIFOQueueError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE.value)
            elif not self._device.check_addr(ModbusMemmap.HR.value, fifo + 1, 2 * count): # Validate queue addresses (2 bytes per value)
                # Exception Response with code 0x02
                return smb.ModbusPDU18ReadFIFOQueueError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_ADDRESS.value)
            else:
                # Read queue
                values : list[int] = [self._device.read_word(ModbusMemmap.HR.value + fifo + offset) for offset in range(1, (2 * count) + 1, 2)]
                return smb.ModbusPDU18ReadFIFOQueueResponse(FIFOCount=count, FIFOVal=values)
        except AssertionError:
            # Exception Response with code 0x04
            return smb.ModbusPDU18ReadFIFOQueueError(exceptCode=ModbusErrorCode.SERVER_FAILURE.value)

    def _mb_indication_EIT(self, function_code : int = 0x2b, request_pdu : smb.ModbusPDU2B0EReadDeviceIdentificationRequest = None) -> Packet:
        'Encapsulated Interface Transport (0x2B / 0x0E) Read Device Identification'
        readcode : int = request_pdu.readCode
        try:
            ModbusReadCodes(readcode)
        except ValueError:
            return smb.ModbusPDU2B0EReadDeviceIdentificationError(exceptCode=ModbusErrorCode.ILLEGAL_DATA_VALUE)
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

    def run(self) -> None:
        isalive = True
        sock = self._sock
        indication_handlers : dict[int, function] = {
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

    def __init__(self, *args, device : IEDBase, **kwargs):
        super().__init__(*args, **kwargs)
        self._device : IEDBase = device
        self._handlers : list[ModbusHandler] = []
    
    def run(self):
        listening_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        listening_sock.bind(('', MODBUS_TCP_PORT))
        listening_sock.settimeout(2)
        listening_sock.listen()
        while not self._terminate:
            try:
                incoming, iaddr = listening_sock.accept()
                incoming.settimeout(60)
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

