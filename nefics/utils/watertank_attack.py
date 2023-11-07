#!/usr/bin/env python3

from argparse import ArgumentParser
from socket import inet_aton
from time import sleep
from datetime import datetime

from nefics.protos.modbus import ModbusClient

def valid_ipv4(ip_addr : str) -> bool:
    try:
        inet_aton(ip_addr)
        return True
    except OSError:
        return False

def main():
    try:
        aparser = ArgumentParser()
        aparser.add_argument('ip', metavar='<TARGET IP>',type=str)
        aparser.add_argument('read_addr', metavar='<Input Register address>', type=int)
        aparser.add_argument('write_addr', metavar='<Holding Register address>', type=int)
        args = aparser.parse_args()
        assert valid_ipv4(args.ip), f'Invalid IPv4 target'
        assert args.read_addr in range(65535), f'Input register address out of range'
        assert args.write_addr in range(65535), f'Holding register address out of range'
        hr_addr = args.write_addr
        ir_addr = args.read_addr
        target = ModbusClient(args.ip)
        target.connect()
        value = (target.read_input_word(ir_addr) * 3.0) / 1000.0
        target.send_word(hr_addr, 0) # New set point = 0
        with open(f'watertank_log_{int(datetime.now().timestamp())}.csv','wt') as log:
            while value > 0.33:
                log.write(f'{datetime.now().timestamp()},{value}\r\n')
                print(f'Current value: {value}', end='\r')
                value = (target.read_input_word(ir_addr) * 3.0) / 1000.0
                sleep(0.01)
            print('\r')
            log.flush()
        target.close()
    except AssertionError as e:
        print(str(e))



if __name__ == '__main__':
    main()
