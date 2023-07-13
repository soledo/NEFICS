#!/usr/bin/env python3

from nefics.protos.iec10x.packets import *

def test_TESTFR_actcon():
    apdu = APDU(b'\x68\x04\x83\x00\x00\x00')
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert isinstance(apci, APCI)
    assert apci.length == 0x04
    assert apci.type    == 0x03
    assert apci.UType   == 0x20

def test_TESTFR_act ():
    apdu = APDU(b'\x68\x04\x43\x00\x00\x00')
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert isinstance(apci, APCI)
    assert apci.length == 0x04
    assert apci.type    == 0x03
    assert apci.UType   == 0x10

def test_STOPDT_actcon():
    apdu = APDU(b'\x68\x04\x23\x00\x00\x00')
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert apci.length == 0x04
    assert apci.type    == 0x03
    assert apci.UType   == 0x08

def test_STOPDT_act():
    apdu = APDU(b'\x68\x04\x13\x00\x00\x00')
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert apci.length == 0x04
    assert apci.type    == 0x03
    assert apci.UType   == 0x04

def test_STARTDT_actcon():
    apdu = APDU(b'\x68\x04\x0b\x00\x00\x00')
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert apci.length == 0x04
    assert apci.type    == 0x03
    assert apci.UType   == 0x02

def test_STARTDT_act():
    apdu = APDU(b'\x68\x04\x07\x00\x00\x00')
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert apci.length == 0x04
    assert apci.type    == 0x03
    assert apci.UType   == 0x01

def test_SFrame():
    apdu = APDU(b'\x68\x04\x01\x00\x3e\x22')
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert isinstance(apci, APCI)
    assert apci.length == 0x04
    assert apci.type    == 0x01
    assert apci.Rx      == 0x111f

def test_C_SC_NA_1():
    apdu = APDU()
    apdu /= APCI(type=0x00, Tx=1, Rx=1)
    apdu /= ASDU(type=0x2d, VSQ=VSQ(SQ=0, number=1), COT=0x03, CommonAddress=0x01, IO=IO45(SE=1, SCS=1, balanced=False))
    apdu = APDU(b'\x68\x0c\x08\x00\x0c\x00\x2d\x01\x03\x01\x04\x00\x00\x01')
    assert isinstance(apdu, APDU)
