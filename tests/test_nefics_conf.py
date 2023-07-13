#!/usr/bin/env python3

from netifaces import interfaces
from run_nefics import check_configuration

def test_mandatory_general():
    conf_missing = {}
    conf_so = {'switches': []}
    conf_do = {'devices': []}
    conf_ok = {'switches': [], 'devices': []}
    try:
        check_configuration(conf_missing)
    except AssertionError as e:
        assert str(e) == f"Missing configuration directives: ['switches', 'devices']"
    
    try:
        check_configuration(conf_so)
    except AssertionError as e:
        assert str(e) == f"Missing configuration directives: ['devices']"
    
    try:
        check_configuration(conf_do)
    except AssertionError as e:
        assert str(e) == f"Missing configuration directives: ['switches']"

    check_configuration(conf_ok)

def test_switches():
    conf_nl = {'devices': [], 'switches': 'dummy'}
    conf_nd = {'devices': [], 'switches': ['switch 1']}
    conf_nn = {'devices': [], 'switches': [{'dummy': 'dummy'}]}
    conf_ns = {'devices': [], 'switches': [{'name': True}]}
    conf_ni = {'devices': [], 'switches': [{'name': 's1', 'dpid': '1'}]}
    conf_dn = {'devices': [], 'switches': [{'name': 's1'}, {'name': 's1'}]}
    conf_dd = {'devices': [], 'switches': [{'name': 's1', 'dpid': 1}, {'name': 's2', 'dpid': 1}]}
    try:
        check_configuration(conf_nl)
    except AssertionError as e:
        assert str(e) == f'"switches" directive must be a list of switch configurations.'
    
    try:
        check_configuration(conf_nd)
    except AssertionError as e:
        assert str(e) == f"Switch configurations must be dictionaries.\r\nOffending switches: ['switch 1']"
    
    try:
        check_configuration(conf_nn)
    except AssertionError as e:
        assert str(e) == f'Missing "name" in switch configuration'

    try:
        check_configuration(conf_ns)
    except AssertionError as e:
        assert str(e) == f'Specified switch "name" value is not a string.\r\nOffending values: [True]'

    try:
        check_configuration(conf_ni)
    except AssertionError as e:
        assert str(e) == f'Specified switch "dpid" value is not an integer.\r\nOffending values: [\'1\']'

    try:
        check_configuration(conf_dn)
    except AssertionError as e:
        assert str(e) == f"Duplicate switch names: ['s1']"

    try:
        check_configuration(conf_dd)
    except AssertionError as e:
        assert str(e) == f'Duplicate switch dpid: [1]'


def test_devices():
    conf_nl = {'switches': [{'name': 's1'}], 'devices': 'dummy'}
    conf_nd = {'switches': [{'name': 's1'}], 'devices': ['dummy']}
    conf_bd = {'switches': [{'name': 's1'}], 'devices': [{'test': 'dummy'}]}
    conf_dd = {'switches': [{'name': 's1'}], 'devices': [{'name': 'h1', 'interfaces': []}, {'name': 'h1', 'interfaces': []}]}
    conf_inl = {'switches': [{'name': 's1'}], 'devices': [{'name': 'h1', 'interfaces': 'dummy'}]}
    conf_ind = {'switches': [{'name': 's1'}], 'devices': [{'name': 'h1', 'interfaces': ['dummy']}]}
    conf_iud = {'switches': [{'name': 's1'}], 'devices': [{'name': 'h1', 'interfaces': [{'dummy': 'dummy'}]}]}
    conf_imd = {'switches': [{'name': 's1'}], 'devices': [{'name': 'h1', 'interfaces': [{'name': 'eth0'}]}]}
    conf_ius = {'switches': [{'name': 's1'}], 'devices': [{'name': 'h1', 'interfaces': [{'name': 'eth0', 'switch': 'dummy', 'ip': '10.0.0.1/24'}]}]}
    conf_ibi = {'switches': [{'name': 's1'}], 'devices': [{'name': 'h1', 'interfaces': [{'name': 'eth0', 'switch': 's1', 'ip': '300.0.0.0/99'}]}]}
    conf_idn = {'switches': [{'name': 's1'}], 'devices': [{'name': 'h1','interfaces': [{'name': 'eth0', 'switch': 's1', 'ip': '10.0.0.1/24'}, {'name': 'eth0', 'switch': 's1', 'ip': '10.0.0.2/24'}]}]}
    conf_idi = {'switches': [{'name': 's1'}], 'devices': [{'name': 'h1','interfaces': [{'name': 'eth0', 'switch': 's1', 'ip': '10.0.0.1/24'}]}, {'name': 'h2','interfaces': [{'name': 'eth0', 'switch': 's1', 'ip': '10.0.0.1/24'}]}]}
    conf_idm = {'switches': [{'name': 's1'}], 'devices': [{'name': 'h1','interfaces': [{'name': 'eth0', 'switch': 's1', 'ip': '10.0.0.1/24', 'mac': 'aa:bb:cc:dd:ee:ff'},{'name': 'eth1', 'switch': 's1', 'ip': '10.0.0.2/24', 'mac': 'aa:bb:cc:dd:ee:ff'}]}]}
    conf_ok = {'switches': [{'name': 's1'}], 'devices': [{'name': 'h1', 'interfaces': [{'name': 'eth0', 'switch': 's1', 'ip': '10.0.0.1/24', 'mac': 'aa:bb:cc:dd:ee:ff'}]}]}
    try:
        check_configuration(conf_nl)
    except AssertionError as e:
        assert str(e) == '"devices" directive must be a list of device configurations.'

    try:
        check_configuration(conf_nd)
    except AssertionError as e:
        assert str(e) == "Device configurations must be dictionaries.\r\nOffending devices: ['dummy']"

    try:
        check_configuration(conf_bd)
    except AssertionError as e:
        assert str(e) == "Unrecognized device directives: ['test']"

    try:
        check_configuration(conf_dd)
    except AssertionError as e:
        assert str(e) == "Duplicate device names: ['h1']"

    try:
        check_configuration(conf_inl)
    except AssertionError as e:
        assert str(e) == '"Interfaces" directive must be a list of interfaces.\r\nOffending devices: [\'h1\']'

    try:
        check_configuration(conf_ind)
    except AssertionError as e:
        assert str(e) == "Interface configurations must be dictionaries.\r\nOffending interfaces: ['dummy']"

    try:
        check_configuration(conf_iud)
    except AssertionError as e:
        assert str(e) == 'Unrecognized interface directives: ["dummy in {\'dummy\': \'dummy\'}"]'

    try:
        check_configuration(conf_imd)
    except AssertionError as e:
        assert str(e) == 'Missing required interface directives: ["ip in {\'name\': \'eth0\'}", "switch in {\'name\': \'eth0\'}"]'

    try:
        check_configuration(conf_ius)
    except AssertionError as e:
        assert str(e) == "Specified switch has not been defined: ['dummy']"

    try:
        check_configuration(conf_ibi)
    except AssertionError as e:
        assert str(e) == "Bad IPv4: ['300.0.0.0/99']"

    try:
        check_configuration(conf_idn)
    except AssertionError as e:
        assert str(e) == "Duplicate interface names: {'h1': ['eth0']}"

    try:
        check_configuration(conf_idi)
    except AssertionError as e:
        assert str(e) == "Duplicate IP addresses: ['10.0.0.1/24']"

    try:
        check_configuration(conf_idm)
    except AssertionError as e:
        assert str(e) == "Duplicate MAC addresses: ['aa:bb:cc:dd:ee:ff']"

    check_configuration(conf_ok)


def test_localiface():
    conf_nd = {'switches': [], 'devices': [], 'localiface': 'dummy'}
    conf_ud = {'switches': [], 'devices': [], 'localiface': {'dummy': 'dummy'}}
    conf_ns = {'switches': [], 'devices': [], 'localiface': {'iface': 0, 'switch': 's1'}}
    conf_ui = {'switches': [], 'devices': [], 'localiface': {'iface': 'test', 'switch': 's1'}}
    conf_us = {'switches': [{'name': 's1', 'dpid': 1}], 'devices': [], 'localiface': {'iface': interfaces()[0], 'switch': 's2'}}
    conf_ok = {'switches': [{'name': 's1', 'dpid': 1}], 'devices': [], 'localiface': {'iface': interfaces()[0], 'switch': 's1'}}
    try:
        check_configuration(conf_nd)
    except AssertionError as e:
        assert str(e) == 'Local interface configuration must be a dictionary.'

    try:
        check_configuration(conf_ud)
    except AssertionError as e:
        assert str(e) == "Unknown local interface directives: ['dummy']"

    try:
        check_configuration(conf_ns)
    except AssertionError as e:
        assert str(e) == 'Local interface value is not a string: [0]'

    try:
        check_configuration(conf_ui)
    except AssertionError as e:
        assert str(e) == 'Cannot find local interface: test'

    try:
        check_configuration(conf_us)
    except AssertionError as e:
        assert str(e) == 'Specified switch has not been defined: s2'

    check_configuration(conf_ok)
