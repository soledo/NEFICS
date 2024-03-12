#!/usr/bin/env python3

import os
import sys
import signal
from time import sleep

from nefics.modules.devicebase import DeviceBase, DeviceHandler
from run import print_error

def launcher_main():
    from importlib import import_module
    import io
    import argparse
    import json
    # Acquire configuration values for the device
    aparser = argparse.ArgumentParser(description='NEFICS Simulated device launcher')
    agr = aparser.add_mutually_exclusive_group(required=True)
    agr.add_argument('-c','--configfile', dest='config', type=argparse.FileType('r', encoding='UTF-8'))
    agr.add_argument('-C','--configstr', dest='config', type=str)
    args = aparser.parse_args()
    configarg = args.config
    if isinstance(configarg, io.TextIOWrapper):
        config = json.load(configarg)
        configarg.close()
    else:
        try:
            config = json.loads(configarg)
        except json.decoder.JSONDecodeError:
            print_error(f'{configarg} is not a valid JSON string\r\n')
            sys.exit()
    # Assert whether the provided configuration has the minimum values
    try:
        required_values = ['module', 'handler', 'device', 'guid', 'in', 'out', 'parameters']
        assert all(x in config.keys() for x in required_values), f'Corrupt configuration detected. Missing values: {", ".join([x for x in required_values if x not in config.keys()])}\r\n'
    except AssertionError as e:
        print_error(str(e))
        sys.exit()
    # Assert whether the provided values are correctly typed
    try:
        assert all(isinstance(x, str) for x in [config['module'], config['handler'], config['device']]), f'A "module", "handler" or "device" value is not a string'
        assert all(isinstance(x, list) for x in [config['in'], config['out']]), f'Either "in" or "out" values are not lists'
        assert all(isinstance(x, int) for x in [config['guid']] + config['in'] + config['out']), f'"guid" or values in the "in" and "out" lists are not integers'
    except AssertionError as e:
        print_error(f'Type mismatch detected within the provided configuration.\r\n{str(e)}\r\n')
        sys.exit()
    # Try to import the specified device module
    try:
        device_module = import_module(f'nefics.modules.{config["module"]}')
    except ModuleNotFoundError:
        print_error(f'Could not find module "nefics.modules.{config["module"]}"\r\n')
        sys.exit()
    # Try to get the configured class from the specified module
    try:
        device_class = getattr(device_module, config['device'])
    except AttributeError:
        print_error(f'Could not find class "{config["device"]}" in module "nefics.modules.{config["module"]}"\r\n')
        sys.exit()
    # Instantiate the device and assert whether it is compatible (devicebase.IEDBase)
    device = device_class(guid=config['guid'], neighbors_in=config['in'], neighbors_out=config['out'], **config['parameters'])
    try:
        assert isinstance(device, DeviceBase), f'Instantiated device ({device_class.__name__}) is not supported by NEFICS\r\n'
    except AssertionError as e:
        print_error(str(e))
        sys.exit()
    # Try to get the configured handler from the specified module
    try:
        handler_class = getattr(device_module, config['handler'])
    except AttributeError:
        print_error(f'Could not find class "{config["handler"]}" in module "nefics.modules.{config["module"]}"\r\n')
        sys.exit()
    handler = handler_class(device=device)
    try:
        assert isinstance(handler, DeviceHandler), f'Instantiated handler ({handler.__name__}) is not supported by NEFICS\r\n'
    except AssertionError as e:
        print_error(str(e))
        sys.exit()
    signal.signal(signal.SIGINT, handler.set_terminate)
    signal.signal(signal.SIGTERM, handler.set_terminate)

    def clearscreen():
        if os.name == 'nt':
            _ = os.system('cls')
        else:
            _ = os.system('clear')
    
    if os.name == 'posix':
        os.system('stty -echo')
    handler.start()
    while not handler.terminate:
        clearscreen()
        handler.status()
        sleep(1)
    handler.join()
    if os.name == 'posix':
        os.system('stty echo')
    
if __name__ == '__main__':
    launcher_main()