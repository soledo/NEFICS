#!/usr/bin/env python3
'''Main script for executing NEFICS.'''

import argparse
import json
import os
import re
import sys
from typing import Optional
from ipaddress import ip_address
from netifaces import interfaces
from Crypto.Random.random import randint
from time import sleep
from subprocess import PIPE, Popen
# Mininet imports
if os.name == 'posix':
    # POSIX systems
    from mininet.node import Host, OVSKernelSwitch
    from mininet.cli import CLI
    from mininet.net import Mininet
    from mininet.term import makeTerm
else:
    # Win32
    #
    # For Win32 platforms we need dummy imports, as mininet is not supported.
    from cmd import Cmd

    class Controller(object):
        '''Dummy Controller'''

        def start(self):
            pass

    class DefaultController(Controller):
        '''Dummy DefaultController'''
    
    class Intf(object):
        '''Dummy Intf'''

        def __init__(self):
            self.name = ''

        def rename(self, name:str):
            pass

        def setMAC(self, mac:str):
            pass

        def setIP(self, ip:str):
            pass
    
    class Host(object):
        '''Dummy Host'''
        
        def __init__(self, name):
            self.name = name
            self.intfs = dict[int,Intf]()
        
        def cmd(self, *args, **kwargs) -> Optional[str]:
            return None

    class Link(object):
        '''Dummy Link'''
        def __init__(self):
            self.intf1 = Intf()
    
    class Switch(object):
        '''Dummy Switch'''

        def attach(self, i:str):
            pass

        def detach(self, i:str):
            pass

        def start(self, c:list):
            pass

    class OVSKernelSwitch(Switch):
        '''Dummy OVSKernelSwitch'''

        def __init__(self, name : str) -> None:
            self.name = name
            self.dpid : str = 15 * '0' + '1'
            super().__init__()

    class Mininet(object):
        '''Dummy Mininet'''

        def __init__( self, topo=None, switch=OVSKernelSwitch, host=Host,
            controller=DefaultController, link=Link, intf=Intf,
            build=True, xterms=False, cleanup=False, ipBase='10.0.0.0/8',
            inNamespace=False,
            autoSetMacs=False, autoStaticArp=False, autoPinCpus=False,
            listenPort=None, waitConnected=False ):
            self.terms : list = list()
            object.__init__(self)
        
        def addController(self, name='c0', controller=None, **params) -> Controller:
            return Controller()
        
        def addSwitch(self, name, cls=None, **params) -> OVSKernelSwitch:
            return OVSKernelSwitch(name)
        
        def addHost(self, name, cls=None, **params) -> Host:
            return Host(name)
        
        def addLink(self, node1, node2, port1=None, port2=None, cls=None, **params) -> Link:
            return Link()
        
        def build(self):
            pass

        def pingAll(self):
            pass
        
        def stop(self):
            pass

    class CLI(Cmd):

        def __init__(self, mininet: Mininet, stdin=sys.stdin, script=None, **kwargs):
            self.mn = mininet
            Cmd.__init__(self, stdin=stdin, **kwargs)

        def do_exit( self, _line ):
            "Exit"
            assert self  # satisfy pylint and allow override
            return 'exited by user command'

        def do_quit( self, line ):
            "Exit"
            return self.do_exit( line )

        def do_EOF( self, line ):
            "Exit"
            return self.do_exit( line )
        
        def default(self, line):
            print_error('Dummy CLI')

    def makeTerm(node, title='Node', term='xterm', display=None, cmd='bash') -> list:
        return list()

# ** Configuration directives **

# Required directives
CONFIG_DIRECTIVES_R = [
    'switches',
    'devices'
]

DEVICE_DIRECTIVES_R = [
    'interfaces',
    'name',
]

INTERFACE_DIRECTIVES_R = [
    'ip',
    'name',
    'switch'
]

LOCALIFACE_DIRECTIVES_R = ['iface', 'switch']

# Optional directives
CONFIG_DIRECTIVES = CONFIG_DIRECTIVES_R + [
    'localiface',
]

DEVICE_DIRECTIVES = DEVICE_DIRECTIVES_R + [
    'iptables',
    'launcher',
    'routes',
]

INTERFACE_DIRECTIVES = INTERFACE_DIRECTIVES_R + [
    'mac',
]

# ** Helper functions **

def print_error(msg: str):
    if re.match(r'[\r]?\n',msg[-2:]) is None:
        msg += '\r\n'
    sys.stderr.write(msg)
    sys.stderr.flush()

def next_dpid(sw: list[OVSKernelSwitch]) -> str:
    nxt = 1
    while nxt in [int(d.dpid, 16) for d in sw]:
        nxt += 1
    return f'{nxt:016x}'

def new_mac() -> str:
    mac = '00:' * 6
    while mac in ['00:' * 6, 'FF:' * 6]:
        mac = ''.join([f'{randint(i-i,255):02X}:' for i in range(6)])
    return mac[:-1]

MAC_REGEX = re.compile(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$')
IP_REGEX = re.compile(r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$')

check_mac = lambda mac: bool(MAC_REGEX.match(mac) is not None) if isinstance(mac, str) else False

def check_ipv4(ip: str) -> bool:
    '''Check for an IPv4 format.'''
    try:
        assert IP_REGEX.match(ip) is not None
        assert '/' in ip
        assert int(ip.split('/')[1]) <= 32
        assert int(ip.split('/')[1]) >= 0
        ip_address(ip.split('/')[0])
        return True
    except (ValueError, AssertionError):
        return False

def check_configuration(conf: dict):
    '''Verify the launch configuration.'''
    # Check for mandatory configuration directives
    assert all(x in conf.keys() for x in CONFIG_DIRECTIVES_R), f'Missing configuration directives: {[x for x in CONFIG_DIRECTIVES_R if x not in conf.keys()]}'
    # Check configured switches
    switches = conf['switches']
    assert isinstance(switches, list), '"switches" directive must be a list of switch configurations.'
    assert all(isinstance(sw, dict) for sw in switches), f'Switch configurations must be dictionaries.\r\nOffending switches: {[x for x in switches if not isinstance(x, dict)]}'
    assert all('name' in x.keys() for x in switches), f'Missing "name" in switch configuration'
    assert all(isinstance(x['name'], str) for x in switches), f'Specified switch "name" value is not a string.\r\nOffending values: {[x["name"] for x in switches]}'
    assert all(isinstance(x['dpid'], int) for x in switches if 'dpid' in x.keys()), f'Specified switch "dpid" value is not an integer.\r\nOffending values: {[x["dpid"] for x in switches if not isinstance(x["dpid"], int)]}'
    assert len(set([sw['name'] for sw in switches])) == len(switches), f'Duplicate switch names: {[z for z, w in {x["name"]:sum([1 for y in switches if y["name"] == x["name"]]) for x in switches}.items() if w > 1]}'
    assert len(set([sw['dpid'] for sw in switches if 'dpid' in sw.keys()])) == len([sw['dpid'] for sw in switches if 'dpid' in sw.keys()]), f'Duplicate switch dpid: {[z for z, w in {x["dpid"]:sum([1 for y in switches if y["dpid"] == x["dpid"]]) for x in switches}.items() if w > 1]}'
    # Check configured devices
    devices = conf['devices']
    assert isinstance(devices, list), f'"devices" directive must be a list of device configurations.'
    assert all(isinstance(dev, dict) for dev in devices), f'Device configurations must be dictionaries.\r\nOffending devices: {[x for x in devices if not isinstance(x, dict)]}'
    assert all(k in DEVICE_DIRECTIVES for dev in devices for k in dev.keys()), f'Unrecognized device directives: {[k for dev in devices for k in dev.keys() if k not in DEVICE_DIRECTIVES]}'
    assert len(set([dev['name'] for dev in devices])) == len(devices), f'Duplicate device names: {[z for z, w in {x["name"]:sum([1 for y in devices if y["name"] == x["name"]]) for x in devices}.items() if w > 1]}'
    assert all(isinstance(i, list) for i in [dev['interfaces'] for dev in devices]), f'"Interfaces" directive must be a list of interfaces.\r\nOffending devices: {[dev["name"] for dev in devices if not isinstance(dev["interfaces"], list)]}'
    assert all(isinstance(i, dict) for ifc in [dev['interfaces'] for dev in devices] for i in ifc), f'Interface configurations must be dictionaries.\r\nOffending interfaces: {[i for ifc in [dev["interfaces"] for dev in devices] for i in ifc if not isinstance(i, dict)]}'
    assert all(k in INTERFACE_DIRECTIVES for ifc in [dev['interfaces'] for dev in devices] for i in ifc for k in i.keys()), f'Unrecognized interface directives: {[f"{k} in {i}" for ifc in [d["interfaces"] for d in devices] for i in ifc for k in i.keys() if k not in INTERFACE_DIRECTIVES]}'
    assert all(k in i.keys() for k in INTERFACE_DIRECTIVES_R for ifc in [dev['interfaces'] for dev in devices] for i in ifc), f'Missing required interface directives: {[f"{k} in {i}" for k in INTERFACE_DIRECTIVES_R for ifc in [d["interfaces"] for d in devices] for i in ifc if k not in i.keys()]}'
    assert all(i['switch'] in [sw['name'] for sw in switches] for ifc in [dev['interfaces'] for dev in devices] for i in ifc), f"Specified switch has not been defined: {[i['switch'] for ifc in [dev['interfaces'] for dev in devices] for i in ifc if i['switch'] not in [sw['name'] for sw in switches]]}"
    assert all(check_ipv4(ip) for ip in set(i['ip'] for ifc in [dev['interfaces'] for dev in devices] for i in ifc)), f"Bad IPv4: {[ip for ip in set(i['ip'] for ifc in [dev['interfaces'] for dev in devices] for i in ifc) if not check_ipv4(ip)]}"
    assert sum([len(set(i['name'] for i in ifc)) for ifc in [dev['interfaces'] for dev in devices]]) == sum([len([i['name'] for i in ifc]) for ifc in [dev['interfaces'] for dev in devices]]), f"Duplicate interface names: { {d['name']:[z for z, w in {x['name']:sum([1 for y in d['interfaces'] if y['name'] == x['name']]) for x in d['interfaces']}.items() if w > 1] for d in devices}}"
    assert len(set(i['ip'] for ifc in [dev['interfaces'] for dev in devices] for i in ifc)) == len([i['ip'] for ifc in [dev['interfaces'] for dev in devices] for i in ifc]), f"Duplicate IP addresses: {list(set(i['ip'] for ifc in [dev['interfaces'] for dev in devices] for i in ifc))}"
    assert len(set(i['mac'] for ifc in [dev['interfaces'] for dev in devices] for i in ifc if 'mac' in i.keys())) == len([i['mac'] for ifc in [dev['interfaces'] for dev in devices] for i in ifc if 'mac' in i.keys()]), f"Duplicate MAC addresses: {list(set(i['mac'] for ifc in [dev['interfaces'] for dev in devices] for i in ifc))}"
    # Check for host interface
    if 'localiface' in conf.keys():
        liface = conf['localiface']
        assert isinstance(liface, dict), 'Local interface configuration must be a dictionary.'
        assert all(x in LOCALIFACE_DIRECTIVES_R for x in liface.keys()), f"Unknown local interface directives: {[x for x in liface.keys() if x not in LOCALIFACE_DIRECTIVES_R]}"
        assert all(isinstance(x, str) for x in liface.values()), f"Local interface value is not a string: {[x for x in liface.values() if not isinstance(x, str)]}"
        assert liface['iface'] in interfaces(), f"Cannot find local interface: {conf['localiface']['iface']}"
        assert liface['switch'] in [sw['name'] for sw in switches], f"Specified switch has not been defined: {liface['switch']}"

def nefics(conf: dict):
    '''Main function'''
    # Check configuration
    try:
        check_configuration(conf)
    except AssertionError as e:
        print_error(str(e))
        sys.exit()
    # Initialize Mininet
    net = Mininet(topo=None, build=False, autoSetMacs=False)
    # Add SDN controller
    c0 = net.addController(name='c0') # TODO: Add the possibility of using an external controller
    # Setup virtual switches
    switches = dict[str, OVSKernelSwitch]()
    for s in conf['switches']:
        try:
            if 'dpid' in s.keys():
                assert f'{s["dpid"]:016x}' not in [x.dpid for x in switches.values()], f'Duplicate switch DPID: {s["dpid"]:016x}'
                switches[s['name']] = net.addSwitch(s['name'], dpid=f'{s["dpid"]:016x}', cls=OVSKernelSwitch)
            else:
                switches[s['name']] = net.addSwitch(s['name'], dpid=next_dpid(list(switches.values())), cls=OVSKernelSwitch)
        except AssertionError as e:
            print_error(str(e))
            sys.exit()
    # Setup virtual devices
    devices:dict[str, Host] = {}
    for dev in conf['devices']:
        hname = str(dev['name'])
        dhost = net.addHost(hname, cls=Host)
        devices[hname] = dhost
        for iface in dev['interfaces']:
            # Get MAC address
            ifmac = None
            if 'mac' in iface.keys() and check_mac(iface['mac']):
                ifmac = iface['mac']
            elif 'mac' in iface.keys():
                print_error(f'Bad MAC address: {iface["mac"]}. Generating random MAC address for this interface ...\r\n')
            if ifmac is None:
                ifmac = new_mac()
                while ifmac.upper() in ['00:00:00:00:00:00', 'FF:FF:FF:FF:FF:FF'] + [str(i['mac']).upper() if 'mac' in dict(i).keys() else '' for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc]:
                    ifmac = new_mac()
                print_error(f'Generated MAC address "{ifmac}" for interface {iface["name"]} in host {dev["name"]}.')
            # Create interface
            ln = net.addLink(dhost, switches[iface['switch']])
            niface = ln.intf1
            niface.rename(f'{hname}-{iface["name"]}')
            niface.setMAC(ifmac)
            niface.setIP(iface['ip'])    
    # Start network
    net.build()
    c0.start()
    for sw in switches.values():
        sw.start([c0])
    # Add local interface to its switch, if necessary
    if 'localiface' in conf.keys():
        switches[conf['localiface']['switch']].attach(conf['localiface']['iface'])
    net.pingAll()
    # Launch instances
    for dev in conf['devices']:
        device = devices[dev['name']]
        for iface in device.intfs.values():
            iconf = [i for i in dev['interfaces'] if i['name'] == iface.name.split('-')[1]][0]
            iface.setIP(iconf['ip'])
        for rt in dev['routes']:
            if isinstance(rt, list) and len(rt) == 2 and all(isinstance(r, str) for r in rt):
                device.cmd(f'ip route add {rt[0]} via {rt[1]}')
        if 'launcher' in dev.keys():
            # Always run launcher in background mode for reliability
            print(f"Starting launcher for {dev['name']} in background...")
            devices[dev['name']].cmd(f"cd {os.getcwd()} && python3 -m nefics.launcher -C \'{json.dumps(dev['launcher'])}\' &")
            sleep(2.0)  # Increased wait time for services to start
    # Local terminal (Mininet host)
    if 'DISPLAY' in os.environ:
        localxterm = Popen(['xterm', '-display', os.environ['DISPLAY']], stdout=PIPE, stdin=PIPE)
    else:
        localxterm = None
    
    # Wait for services to fully start before CLI
    print("Waiting for services to start...")
    sleep(5.0)
    print("Services should be ready. Starting CLI...")
    CLI(net)
    if localxterm is not None:
        localxterm.kill()
        localxterm.wait()
    if 'localiface' in conf.keys():
        switches[conf['localiface']['switch']].detach(conf['localiface']['iface'])
    net.stop()

if __name__ == '__main__':
    try:
        assert os.name == 'posix'
    except AssertionError:
        print_error(f'ERROR: NEFICS needs a POSIX system supporting Mininet.\r\n')
        sys.exit()
    ap = argparse.ArgumentParser(description='NEFICS sandbox')
    ap.add_argument('config', metavar='CONFIGURATION_FILE', type=argparse.FileType('r', encoding='utf-8'))
    config_file = ap.parse_args().config
    try:
        config = json.load(config_file)
    except json.decoder.JSONDecodeError:
        print_error(f'Error reading configuration: JSON decode error\r\n')
        sys.exit()
    nefics(config)
