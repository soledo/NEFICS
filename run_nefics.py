#!/usr/bin/env python3

import re
import argparse
import json
import sys
from os import environ, name as OS_NAME
from ipaddress import ip_address
from netifaces import interfaces
from Crypto.Random.random import randint
from time import sleep
from subprocess import PIPE, Popen
# Mininet imports
if OS_NAME == 'posix':
    # POSIX systems
    from mininet.node import Host, OVSKernelSwitch
    from mininet.cli import CLI
    from mininet.net import Mininet
    from mininet.term import makeTerm
else:
    # Win32
    from cmd import Cmd

    class Controller(object):
        '''Dummy Controller'''

        def start():
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
        
        def __init__(self):
            self.intfs = dict[int,Intf]()
        
        def setDefaultRoute(self, intf: (Intf | str)):
            pass

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

    class Mininet(object):
        '''Dummy Mininet'''

        def __init__( self, topo=None, switch=OVSKernelSwitch, host=Host,
            controller=DefaultController, link=Link, intf=Intf,
            build=True, xterms=False, cleanup=False, ipBase='10.0.0.0/8',
            inNamespace=False,
            autoSetMacs=False, autoStaticArp=False, autoPinCpus=False,
            listenPort=None, waitConnected=False ):
            self.terms = []
            object.__init__(self)
        
        def addController(self, name='c0', controller=None, **params) -> Controller:
            return Controller()
        
        def addSwitch(self, name, cls=None, **params) -> Switch:
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

    def makeTerm(node, title='Node', term='xterm', display=None, cmd='bash') -> (list | None):
        return []

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
    'switch',
    'default'
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
check_mac = lambda mac: bool(MAC_REGEX.match(mac) is not None) if isinstance(mac, str) else False

def check_ipv4(ip: str) -> bool:
    try:
        IP_REGEX = re.compile(r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$')
        assert IP_REGEX.match(ip) is not None
        assert '/' in ip
        assert int(ip.split('/')[1]) <= 32
        assert int(ip.split('/')[1]) >= 0
        ip_address(ip.split('/')[0])
        return True
    except (ValueError, AssertionError):
        return False

def check_configuration(conf: dict) -> bool:
    # Check for mandatory configuration directives
    if not all(x in conf.keys() for x in CONFIG_DIRECTIVES_R):
        print_error(f'Missing configuration directives: {[x for x in CONFIG_DIRECTIVES_R if x not in conf.keys()]}')
        return False
    # Check configured switches
    if not isinstance(conf['switches'], list):
        print_error('"switches" directive must be a list of switch configurations.')
        return False
    if not all(isinstance(x, dict) for x in conf['switches']):
        print_error('Switch configurations must be dictionaries.')
        print_error(f'Offending switches: {[x for x in conf["switches"] if not isinstance(x, dict)]}')
        return False
    if not all('name' in x.keys() for x in conf['switches']):
        for x in conf['switches']:
            if 'name' not in x.keys():
                print_error(f'Missing "name" in switch configuration: {x}')
                break
        return False
    if not all(isinstance(x['name'], str) for x in conf['switches']):
        for x in conf['switches']:
            if not isinstance(x['name'], str):
                print_error(f'"name" {x["name"]} is not a string. In: {x}')
                break
        return False
    if not all(isinstance(x['dpid'], int) for x in conf['switches'] if 'dpid' in x.keys()):
        for x in conf['switches']:
            if not isinstance(x['dpid'], int):
                print_error(f'{x["dpid"]} is not an integer')
                break
        return False
    if not len(set([sw['name'] for sw in conf['switches']])) == len(conf['switches']):
        print_error(f'Duplicate switch names: {[z for z, w in {x["name"]:sum([1 for y in conf["switches"] if y["name"] == x["name"]]) for x in conf["switches"]}.items() if w > 1]}')
        return False
    if not len(set([sw['dpid'] for sw in conf['switches'] if 'dpid' in sw.keys()])) == len([sw['dpid'] for sw in conf['switches'] if 'dpid' in sw.keys()]):
        print_error(f'Duplicate switch dpid: {[z for z, w in {x["dpid"]:sum([1 for y in conf["switches"] if y["dpid"] == x["dpid"]]) for x in conf["switches"]}.items() if w > 1]}')
        return False
    # Check configured devices
    if not isinstance(conf['devices'], list):
        print_error('"devices" directive must be a list of device configurations.')
        return False
    if not all(isinstance(dev, dict) for dev in conf['devices']):
        print_error('Device configurations must be dictionaries.')
        print_error(f'Offending devices: {[x for x in conf["devices"] if not isinstance(x, dict)]}')
        return False
    if not all(k in DEVICE_DIRECTIVES for dev in conf['devices'] for k in dev.keys()):
        print_error(f'Unrecognized device directives: {[k for dev in conf["devices"] for k in dev.keys() if k not in DEVICE_DIRECTIVES]}')
        return False
    if not len(set([dev['name'] for dev in conf['devices']])) == len(conf['devices']):
        print_error(f'Duplicate device names: {[z for z, w in {x["name"]:sum([1 for y in conf["devices"] if y["name"] == x["name"]]) for x in conf["devices"]}.items() if w > 1]}')
        return False
    if not all(isinstance(i, list) for i in [dev['interfaces'] for dev in conf['devices']]):
        print_error(f'"Interfaces" directive must be a list of interfaces.')
        print_error(f"Offending devices: {[dev['name'] for dev in conf['devices'] if not isinstance(dev['interfaces'], list)]}")
        return False
    if not all(isinstance(i, dict) for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc):
        print_error('Interface configurations must be dictionaries.')
        print_error(f'Offending interfaces: {[i for ifc in [dev["interfaces"] for dev in conf["devices"]] for i in ifc if not isinstance(i, dict)]}')
        return False
    if not all(k in INTERFACE_DIRECTIVES for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc for k in i.keys()):
        print_error(f'Unrecognized interface directives: {[f"{k} in {i}" for ifc in [d["interfaces"] for d in conf["devices"]] for i in ifc for k in i.keys() if k not in INTERFACE_DIRECTIVES]}')
        return False
    if not all(k in i.keys() for k in INTERFACE_DIRECTIVES_R for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc):
        print_error(f'Missing required interface directives: {[f"{k} in {i}" for k in INTERFACE_DIRECTIVES_R for ifc in [d["interfaces"] for d in conf["devices"]] for i in ifc if k not in i.keys()]}')
        return False
    if not all(i['switch'] in [sw['name'] for sw in conf['switches']] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc):
        print_error(f"Specified switch has not been defined: {[i['switch'] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc if i['switch'] not in [sw['name'] for sw in conf['switches']]]}")
        return False
    if not all(check_ipv4(ip) for ip in set(i['ip'] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc)):
        print_error(f"Bad IPv4: {[ip for ip in set(i['ip'] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc) if not check_ipv4(ip)]}")
        return False
    if not sum([len(set(i['name'] for i in ifc)) for ifc in [dev['interfaces'] for dev in conf['devices']]]) == sum([len([i['name'] for i in ifc]) for ifc in [dev['interfaces'] for dev in conf['devices']]]):
        print_error(f"Duplicate interface names: { {d['name']:[z for z, w in {x['name']:sum([1 for y in d['interfaces'] if y['name'] == x['name']]) for x in d['interfaces']}.items() if w > 1] for d in conf['devices']}}")
        return False
    if not len(set(i['ip'] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc)) == len([i['ip'] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc]):
        print_error(f"Duplicate IP addresses: {list(set(i['ip'] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc))}")
        return False
    if not len(set(i['mac'] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc)) == len([i['mac'] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc]):
        print_error(f"Duplicate MAC addresses: {list(set(i['mac'] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc))}")
        return False
    # Check for host interface
    if 'localiface' in conf.keys():
        if not isinstance(conf['localiface'], dict):
            print_error('Local interface configuration must be a dictionary.')
            return False
        if not all(x in LOCALIFACE_DIRECTIVES_R for x in conf['localiface'].keys()):
            print_error(f"Unknown local interface directives: {[x for x in conf['localiface'].keys() if x not in LOCALIFACE_DIRECTIVES_R]}")
            return False
        if not all(isinstance(x, str) for x in conf['localiface'].values()):
            print_error(f"Local interface value is not a string: {[x for x in conf['localiface'].values() if not isinstance(x, str)]}")
            return False
        if not conf['localiface']['iface'] in interfaces():
            print_error(f"Cannot find local interface: {conf['localiface']['iface']}")
            return False
        if not conf['localiface']['switch'] in [sw['name'] for sw in conf['switches']]:
            print_error(f"Specified switch has not been defined: {conf['localiface']['switch']}")
            return False
    return True

def nefics(conf: dict):
    # Check configuration
    try:
        assert check_configuration(conf)
    except AssertionError:
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
                assert f'{s["dpid"]:016x}' not in [x.dpid for x in switches.values()]
                switches[s['name']] = net.addSwitch(s['name'], dpid=f'{s["dpid"]:016x}', cls=OVSKernelSwitch)
            else:
                switches[s['name']] = net.addSwitch(s['name'], dpid=next_dpid(switches), cls=OVSKernelSwitch)
        except AssertionError:
            print_error(f'Bad switch definition: {str(s)}')
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
                while ifmac.upper() in ['00:00:00:00:00:00', 'FF:FF:FF:FF:FF:FF'] + [str(i['mac']).upper() for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc]:
                    ifmac = new_mac()
                print_error(f'Generated MAC address "{ifmac}" for interface {iface["name"]} in host {dev["name"]}.')
            # Create interface
            ln = net.addLink(dhost, switches[iface['switch']])
            niface = ln.intf1
            niface.rename(f'{hname}-{iface["name"]}')
            niface.setMAC(iface['mac'])
            niface.setIP(iface['ip'])    
    # Start network
    net.build()
    c0.start()
    for sw in switches.values():
        sw.start([c0])
    if 'localiface' in conf.keys():
        switches[conf['localiface']['switch']].attach(conf['localiface']['iface'])
    net.pingAll()
    # Launch instances
    for dev in conf['devices']:
        device = devices[dev['name']]
        for iface in device.intfs.values():
            iconf = [i for i in dev['interfaces'] if i['name'] == iface.name.split('-')[1]][0]
            iface.setIP(iconf['ip'])
            if iconf['default'] == True:
                device.setDefaultRoute(iface)
        if 'launcher' in dev.keys():
            net.terms += makeTerm(devices[dev['name']], cmd=f"python3 -m nefics.launcher -C \"{json.dumps(dev['launcher'])}\"")
            sleep(0.333)
    localxterm = Popen(['xterm', '-display', environ['DISPLAY']], stdout=PIPE, stdin=PIPE)
    CLI(net)
    localxterm.kill()
    localxterm.wait()
    if 'localiface' in conf.keys():
        switches[conf['localiface']['switch']].detach(conf['localiface']['iface'])
    net.stop()

if __name__ == '__main__':
    try:
        assert OS_NAME == 'posix'
    except AssertionError:
        print_error(f'ERROR: NEFICS needs a POSIX system\r\n')
        sys.exit()
    ap = argparse.ArgumentParser(description='NEFICS topology simulator')
    ap.add_argument('config', metavar='CONFIGURATION_FILE', type=argparse.FileType('r', encoding='utf-8'))
    config_file = ap.parse_args().config
    try:
        config = json.load(config_file)
    except json.decoder.JSONDecodeError:
        print_error(f'Error reading configuration: JSON decode error\r\n')
        sys.exit()
    nefics(config)
