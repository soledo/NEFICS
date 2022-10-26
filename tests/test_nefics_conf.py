#!/usr/bin/env python3

from netifaces import interfaces
from run_nefics import check_configuration

def test_mandatory_general():
    conf_missing = {}
    conf_so = {'switches': []}
    conf_do = {'devices': []}
    conf_ok = {'switches': [], 'devices': []}
    assert not check_configuration(conf_missing)
    assert not check_configuration(conf_so)
    assert not check_configuration(conf_do)
    assert check_configuration(conf_ok)

def test_switches():
    conf_nl = {'devices': [], 'switches': 'dummy'}
    conf_nd = {'devices': [], 'switches': ['switch 1']}
    conf_nn = {'devices': [], 'switches': [{'dummy': 'dummy'}]}
    conf_ns = {'devices': [], 'switches': [{'name': True}]}
    conf_ni = {'devices': [], 'switches': [{'name': 's1', 'dpid': '1'}]}
    conf_dn = {'devices': [], 'switches': [{'name': 's1'}, {'name': 's1'}]}
    conf_dd = {'devices': [], 'switches': [{'name': 's1', 'dpid': 1}, {'name': 's2', 'dpid': 1}]}
    assert not check_configuration(conf_nl)
    assert not check_configuration(conf_nd)
    assert not check_configuration(conf_nn)
    assert not check_configuration(conf_ns)
    assert not check_configuration(conf_ni)
    assert not check_configuration(conf_dn)
    assert not check_configuration(conf_dd)

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
    assert not check_configuration(conf_nl)
    assert not check_configuration(conf_nd)
    assert not check_configuration(conf_bd)
    assert not check_configuration(conf_dd)
    assert not check_configuration(conf_inl)
    assert not check_configuration(conf_ind)
    assert not check_configuration(conf_iud)
    assert not check_configuration(conf_imd)
    assert not check_configuration(conf_ius)
    assert not check_configuration(conf_ibi)
    assert not check_configuration(conf_idn)
    assert not check_configuration(conf_idi)
    assert not check_configuration(conf_idm)
    assert check_configuration(conf_ok)

def test_localiface():
    conf_nd = {'switches': [], 'devices': [], 'localiface': 'dummy'}
    conf_ud = {'switches': [], 'devices': [], 'localiface': {'dummy': 'dummy'}}
    conf_ns = {'switches': [], 'devices': [], 'localiface': {'iface': 0, 'switch': 's1'}}
    conf_ui = {'switches': [], 'devices': [], 'localiface': {'iface': 'test', 'switch': 's1'}}
    conf_us = {'switches': [{'name': 's1', 'dpid': 1}], 'devices': [], 'localiface': {'iface': interfaces()[0], 'switch': 's2'}}
    conf_ok = {'switches': [{'name': 's1', 'dpid': 1}], 'devices': [], 'localiface': {'iface': interfaces()[0], 'switch': 's1'}}
    assert not check_configuration(conf_nd)
    assert not check_configuration(conf_ud)
    assert not check_configuration(conf_ns)
    assert not check_configuration(conf_ui)
    assert not check_configuration(conf_us)
    assert check_configuration(conf_ok)
