#!/usr/bin/env python3

from sys import argv, exit
from socket import AF_INET, IPPROTO_TCP, SOCK_STREAM, socket, timeout
from typing import IO
from netaddr import valid_ipv4
from random import randint
from cmd import Cmd
from scapy.contrib.modbus import *

class MBCLI(Cmd):
    prompt = '> '

    def __init__(self, sock: socket) -> None:
        super().__init__()
        self._sock = sock
    
    def do_readcoil(self, arg):
        try:
            coil_addr = int(arg)
            assert coil_addr >= 0
            assert coil_addr <= 65535
            req:ModbusADURequest = ModbusADURequest(unitId=0x01, transId=randint(1,65535))
            req /= ModbusPDU01ReadCoilsRequest(startAddr=0, quantity=1)
            self._sock.send(req.build())
            buffer:bytes = self._sock.recv(2048)
            data:ModbusADUResponse = ModbusADUResponse(buffer)
            if data.haslayer(ModbusPDU01ReadCoilsResponse):
                response:ModbusPDU01ReadCoilsResponse = data['ModbusPDU01ReadCoilsResponse']
                status:bool = bool(response.coilStatus[0] & 0x0001)
                print(f'Coil {coil_addr} status: {"ON" if status else "OFF"}')
        except AssertionError:
            print(f'Invalid address: {coil_addr}')
        except timeout:
            print(f'Socket timeout')
    
    def do_writecoil(self, arg):
        try:
            coil_addr:int = int(arg.split(' ')[0])
            value:bool = True if arg.split(' ')[1].lower() == 'true' else False
            assert coil_addr >= 0
            assert coil_addr <= 65535
            req:ModbusADURequest = ModbusADURequest(unitId=0x01, transId=randint(1, 65535))
            req /= ModbusPDU05WriteSingleCoilRequest(outputAddr=coil_addr, outputValue=0xFF00 if value else 0x0000)
            self._sock.send(req.build())
            buffer:bytes = self._sock.recv(2048)
            res:ModbusADUResponse = ModbusADUResponse(buffer)
            res.show2()
        except AssertionError:
            print(f'Invalid address or value')
    
    def do_readhr(self, arg):
        try:
            hr_addr = int(arg)
            assert hr_addr >= 0
            assert hr_addr <= 65535
            req:ModbusADURequest = ModbusADURequest(unitId=0x01, transId=randint(1, 65535))
            req /= ModbusPDU03ReadHoldingRegistersRequest(startAddr=hr_addr, quantity=1)
            self._sock.send(req.build())
            buffer:bytes = self._sock.recv(2048)
            data:ModbusADUResponse = ModbusADUResponse(buffer)
            if data.haslayer(ModbusPDU03ReadHoldingRegistersResponse):
                response = data['ModbusPDU03ReadHoldingRegistersResponse']
                value:int = response.registerVal[0]
                print(f'Holding register {hr_addr} value: {value}')
            else:
                data.show2()
        except AssertionError:
            print(f'Invalid register address')
    
    def do_writehr(self, arg):
        try:
            hr_addr:int = int(arg.split(' ')[0])
            value:int = int(arg.split(' ')[1])
            assert hr_addr >= 0 and hr_addr <= 65535
            assert value >= 0 and value <= 65535
            req:ModbusADURequest = ModbusADURequest(unitId=0x01, transId=randint(1, 65535))
            req /= ModbusPDU06WriteSingleRegisterRequest(registerAddr=hr_addr, registerValue=value)
            self._sock.send(req.build())
            buffer:bytes = self._sock.recv(2048)
            response:ModbusADUResponse = ModbusADUResponse(buffer)
            response.show2()
        except AssertionError:
            print(f'Invalid address or value')
    def do_exit(self, arg):
        return True

if __name__ == '__main__':
    try:
        assert len(argv) >= 2
        assert valid_ipv4(argv[1])
        if len(argv) > 2:
            assert int(argv[2]) > 0
            assert int(argv[2]) < 65535
    except AssertionError:
        print(f'Usage: python -m nefics.utils.modbus_poller <Modbus device IP> <port>')
        exit(1)
    ipaddress = str(argv[1])
    dport = int(argv[2]) if len(argv) > 2 else 502
    sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
    sock.connect((ipaddress, dport))
    sock.settimeout(1)
    cli = MBCLI(sock=sock)
    cli.cmdloop()
    sock.close()
