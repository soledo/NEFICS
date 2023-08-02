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

def test_M_SP_NA_1():
    '''
    Test IEC-104 Type 1: Single-point information without time tag (M_SP_NA_1)
    '''
    # Sequence of IO (SQ=0)
    vsq1 : VSQ = VSQ(SQ=0, number=1)
    vsq2 : VSQ = VSQ(SQ=0, number=2)
    apci : APCI = APCI(type=0x00, Tx=1, Rx=1)
    io : IO1 = IO1(IOA=1, SIQ=0xa1, _balanced=True)
    io1 : IO1 = IO1(IOA=2, SIQ=0x01, _balanced=True)
    asdu : ASDU = ASDU(type=0x01, VSQ=vsq1, COT_flags=0b00, COT=3, CommonAddress=1, IO=[io])
    apdu : APDU = APDU()
    apdu /= apci/asdu
    assert apdu.build() == b'\x68\x0b\x02\x00\x02\x00\x01\x01\x03\x01\x01\x00\xa1'
    asdu = ASDU(type=0x01, VSQ=vsq2, COT_flags=0b00, COT=3, CommonAddress=1, IO=[io, io1])
    apdu : APDU = APDU()
    apdu /= apci/asdu
    assert apdu.build() == b'\x68\x0e\x02\x00\x02\x00\x01\x02\x03\x01\x01\x00\xa1\x02\x00\x01'
    io : IO1 = IO1(IOA=1, SIQ=0xa1, _balanced=False)
    io1 : IO1 = IO1(IOA=2, SIQ=0x01, _balanced=False)
    asdu : ASDU = ASDU(type=0x01, VSQ=vsq1, COT_flags=0b00, COT=3, CommonAddress=1, IO=[io])
    apdu : APDU = APDU()
    apdu /= apci/asdu
    assert apdu.build() == b'\x68\x0c\x02\x00\x02\x00\x01\x01\x03\x01\x01\x00\x00\xa1'
    asdu = ASDU(type=0x01, VSQ=vsq2, COT_flags=0b00, COT=3, CommonAddress=1, IO=[io, io1])
    apdu : APDU = APDU()
    apdu /= apci/asdu
    assert apdu.build() == b'\x68\x10\x02\x00\x02\x00\x01\x02\x03\x01\x01\x00\x00\xa1\x02\x00\x00\x01'
    apdu : APDU = APDU(b'\x68\x0b\x02\x00\x02\x00\x01\x01\x03\x01\x01\x00\xa1')
    assert apdu.haslayer('APCI')
    apci : APCI = apdu['APCI']
    assert apci.Tx == 1
    assert apci.Rx == 1
    assert apci.length == 11
    assert apci.haslayer('ASDU')
    asdu : ASDU = apci['ASDU']
    assert asdu.type == 0x01
    assert asdu.VSQ.SQ == 0
    assert asdu.VSQ.number == 1
    assert asdu.COT_flags == 0b00
    assert asdu.COT == 3
    assert asdu.CommonAddress == 1
    assert isinstance(asdu.IO, list)
    assert len(asdu.IO) == 1
    assert isinstance(asdu.IO[0], IO1)
    assert asdu.IO[0].IOA == 1
    assert asdu.IO[0].SIQ == 0xa1
    assert asdu.IO[0].balanced
    apdu = APDU(b'\x68\x0e\x02\x00\x02\x00\x01\x02\x03\x01\x01\x00\xa1\x02\x00\x01')
    assert apdu.haslayer('APCI')
    apci : APCI = apdu['APCI']
    assert apci.Tx == 1
    assert apci.Rx == 1
    assert apci.length == 14
    asdu : ASDU = apci['ASDU']
    assert asdu.type == 0x01
    assert asdu.VSQ.SQ == 0
    assert asdu.VSQ.number == 2
    assert asdu.COT_flags == 0b00
    assert asdu.COT == 3
    assert asdu.CommonAddress == 1
    assert isinstance(asdu.IO, list)
    assert len(asdu.IO) == 2
    assert all(isinstance(x, IO1) for x in asdu.IO)
    assert asdu.IO[0].IOA == 1
    assert asdu.IO[0].SIQ == 0xa1
    assert asdu.IO[0].balanced
    assert asdu.IO[1].IOA == 2
    assert asdu.IO[1].SIQ == 0x01
    assert asdu.IO[1].balanced
    apdu = APDU(b'\x68\x0c\x02\x00\x02\x00\x01\x01\x03\x01\x01\x00\x00\xa1')
    assert apdu.haslayer('APCI')
    apci : APCI = apdu['APCI']
    assert apci.Tx == 1
    assert apci.Rx == 1
    assert apci.length == 12
    asdu : ASDU = apci['ASDU']
    assert asdu.type == 0x01
    assert asdu.VSQ.SQ == 0
    assert asdu.VSQ.number == 1
    assert asdu.COT_flags == 0b00
    assert asdu.COT == 3
    assert asdu.CommonAddress == 1
    assert isinstance(asdu.IO, list)
    assert len(asdu.IO) == 1
    assert isinstance(asdu.IO[0], IO1)
    assert asdu.IO[0].IOA == 1
    assert asdu.IO[0].SIQ == 0xa1
    assert not asdu.IO[0].balanced
    apdu = APDU(b'\x68\x10\x02\x00\x02\x00\x01\x02\x03\x01\x01\x00\x00\xa1\x02\x00\x00\x01')
    assert apdu.haslayer('APCI')
    apci : APCI = apdu['APCI']
    assert apci.Tx == 1
    assert apci.Rx == 1
    assert apci.length == 16
    asdu : ASDU = apci['ASDU']
    assert asdu.type == 0x01
    assert asdu.VSQ.SQ == 0
    assert asdu.VSQ.number == 2
    assert asdu.COT_flags == 0b00
    assert asdu.COT == 3
    assert asdu.CommonAddress == 1
    assert isinstance(asdu.IO, list)
    assert len(asdu.IO) == 2
    assert all(isinstance(x, IO1) for x in asdu.IO)
    assert asdu.IO[0].IOA == 1
    assert asdu.IO[0].SIQ == 0xa1
    assert not asdu.IO[0].balanced
    assert asdu.IO[1].IOA == 2
    assert asdu.IO[1].SIQ == 0x01
    assert not asdu.IO[1].balanced
    # Sequence of IO in a single IO (SQ=1)
    apci : APCI = APCI(type=0x00, Tx=1, Rx=1)
    vsq1 : VSQ = VSQ(SQ=1, number=1)
    vsq2 : VSQ = VSQ(SQ=1, number=2)
    io : IO1 = IO1(IOA=1, SIQ=0xa1, _sq=1, _number=1, _balanced=True)
    io1 : IO1 = IO1(IOA=1, SIQ=[0xa1, 0x01], _sq=1, _number=2, _balanced=True)
    asdu : ASDU = ASDU(type=0x01, VSQ=vsq1, COT_flags=0b00, COT=3, CommonAddress=1, IO=io)
    apdu : APDU = APDU()
    apdu /= apci/asdu
    assert apdu.build() == b'\x68\x0b\x02\x00\x02\x00\x01\x81\x03\x01\x01\x00\xa1'
    asdu : ASDU = ASDU(type=0x01, VSQ=vsq2, COT_flags=0b00, COT=3, CommonAddress=1, IO=io1)
    apdu : APDU = APDU()
    apdu /= apci/asdu
    assert apdu.build() == b'\x68\x0c\x02\x00\x02\x00\x01\x82\x03\x01\x01\x00\xa1\x01'
    io : IO1 = IO1(IOA=1, SIQ=0xa1, _sq=1, _number=1, _balanced=False)
    io1 : IO1 = IO1(IOA=1, SIQ=[0xa1, 0x01], _sq=1, _number=2, _balanced=False)
    asdu : ASDU = ASDU(type=0x01, VSQ=vsq1, COT_flags=0b00, COT=3, CommonAddress=1, IO=io)
    apdu : APDU = APDU()
    apdu /= apci/asdu
    assert apdu.build() == b'\x68\x0c\x02\x00\x02\x00\x01\x81\x03\x01\x01\x00\x00\xa1'
    asdu : ASDU = ASDU(type=0x01, VSQ=vsq2, COT_flags=0b00, COT=3, CommonAddress=1, IO=io1)
    apdu : APDU = APDU()
    apdu /= apci/asdu
    assert apdu.build() == b'\x68\x0d\x02\x00\x02\x00\x01\x82\x03\x01\x01\x00\x00\xa1\x01'
    apdu = APDU(b'\x68\x0b\x02\x00\x02\x00\x01\x81\x03\x01\x01\x00\xa1')
    assert apdu.haslayer('APCI')
    apci : APCI = apdu['APCI']
    assert apci.Tx == 1
    assert apci.Rx == 1
    assert apci.length == 11
    asdu : ASDU = apci['ASDU']
    assert asdu.type == 0x01
    assert asdu.VSQ.SQ == 1
    assert asdu.VSQ.number == 1
    assert asdu.COT_flags == 0b00
    assert asdu.COT == 3
    assert asdu.CommonAddress == 1
    assert isinstance(asdu.IO, IO1)
    assert asdu.IO.IOA == 1
    assert asdu.IO.SIQ == 0xa1
    assert asdu.IO.balanced
    apdu = APDU(b'\x68\x0c\x02\x00\x02\x00\x01\x82\x03\x01\x01\x00\xa1\x01')
    assert apdu.haslayer('APCI')
    apci : APCI = apdu['APCI']
    assert apci.Tx == 1
    assert apci.Rx == 1
    assert apci.length == 12
    asdu : ASDU = apci['ASDU']
    assert asdu.type == 0x01
    assert asdu.VSQ.SQ == 1
    assert asdu.VSQ.number == 2
    assert asdu.COT_flags == 0b00
    assert asdu.COT == 3
    assert asdu.CommonAddress == 1
    assert isinstance(asdu.IO, IO1)
    assert asdu.IO.IOA == 1
    assert isinstance(asdu.IO.SIQ, list)
    assert asdu.IO.SIQ == [0xa1, 0x01]
    assert asdu.IO.balanced
    apdu = APDU(b'\x68\x0c\x02\x00\x02\x00\x01\x81\x03\x01\x01\x00\x00\xa1')
    assert apdu.haslayer('APCI')
    apci : APCI = apdu['APCI']
    assert apci.Tx == 1
    assert apci.Rx == 1
    assert apci.length == 12
    asdu : ASDU = apci['ASDU']
    assert asdu.type == 0x01
    assert asdu.VSQ.SQ == 1
    assert asdu.VSQ.number == 1
    assert asdu.COT_flags == 0b00
    assert asdu.COT == 3
    assert asdu.CommonAddress == 1
    assert isinstance(asdu.IO, IO1)
    assert asdu.IO.IOA == 1
    assert asdu.IO.SIQ == 0xa1
    assert not asdu.IO.balanced
    apdu = APDU(b'\x68\x0d\x02\x00\x02\x00\x01\x82\x03\x01\x01\x00\x00\xa1\x01')
    assert apdu.haslayer('APCI')
    apci : APCI = apdu['APCI']
    assert apci.Tx == 1
    assert apci.Rx == 1
    assert apci.length == 13
    asdu : ASDU = apci['ASDU']
    assert asdu.type == 0x01
    assert asdu.VSQ.SQ == 1
    assert asdu.VSQ.number == 2
    assert asdu.COT_flags == 0b00
    assert asdu.COT == 3
    assert asdu.CommonAddress == 1
    assert isinstance(asdu.IO, IO1)
    assert asdu.IO.IOA == 1
    assert isinstance(asdu.IO.SIQ, list)
    assert asdu.IO.SIQ == [0xa1, 0x01]

def test_M_SP_TA_1():
    # Sequence of information objects (SQ=0)
    apci : APCI = APCI(type=0x00, Tx=1, Rx=1)
    cptime : CP24Time2a = CP24Time2a(Milliseconds=12345, IV=0b0, GEN=0b0, minute=0b100101)
    vsq1 : VSQ = VSQ(SQ=0, number=1)
    vsq2 : VSQ = VSQ(SQ=0, number=2)
    io0 : IO2 = IO2(_sq=0, _number=1, _balanced=True, IOA=1, SIQ=0xa1, time=cptime)
    io1 : IO2 = IO2(_sq=0, _number=1, _balanced=True, IOA=2, SIQ=0x01, time=cptime)
    asdu : ASDU = ASDU(type=0x02, VSQ=vsq1, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io0])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0e\x02\x00\x02\x00\x02\x01\x03\x01\x01\x00\xa1\x39\x30\x25'
    asdu = ASDU(type=0x02, VSQ=vsq2, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io0, io1])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x14\x02\x00\x02\x00\x02\x02\x03\x01\x01\x00\xa1\x39\x30\x25\x02\x00\x01\x39\x30\x25'
    io0 : IO2 = IO2(_sq=0, _number=1, _balanced=False, IOA=1, SIQ=0xa1, time=cptime)
    io1 : IO2 = IO2(_sq=0, _number=1, _balanced=False, IOA=2, SIQ=0x01, time=cptime)
    asdu : ASDU = ASDU(type=0x02, VSQ=vsq1, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io0])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0f\x02\x00\x02\x00\x02\x01\x03\x01\x01\x00\x00\xa1\x39\x30\x25'
    asdu = ASDU(type=0x02, VSQ=vsq2, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io0, io1])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x16\x02\x00\x02\x00\x02\x02\x03\x01\x01\x00\x00\xa1\x39\x30\x25\x02\x00\x00\x01\x39\x30\x25'
    apdu = APDU(b'\x68\x0e\x02\x00\x02\x00\x02\x01\x03\x01\x01\x00\xa1\x39\x30\x25')
    assert apdu.haslayer('APCI')
    apci : APCI = apdu['APCI']
    assert apci.length == 14
    assert apci.type == 0x00
    assert apci.Tx == 0x01
    assert apci.Rx == 0x01
    assert apci.haslayer('ASDU')
    asdu : ASDU = apci['ASDU']
    assert asdu.type == 0x02
    assert asdu.VSQ.SQ == 0
    assert asdu.VSQ.number == 1
    assert asdu.COT_flags == 0b00
    assert asdu.COT == 0x03
    assert asdu.CommonAddress == 0x01
    assert isinstance(asdu.IO, list)
    assert all(isinstance(x, IO2) for x in asdu.IO)
    assert len(asdu.IO) == 1
    assert asdu.IO[0].IOA == 1
    assert asdu.IO[0].SIQ == 0xa1
    assert asdu.IO[0].getfieldval('time') == CP24Time2a(b'\x39\x30\x25')
    assert asdu.IO[0].balanced
    apdu = APDU(b'\x68\x14\x02\x00\x02\x00\x02\x02\x03\x01\x01\x00\xa1\x39\x30\x25\x02\x00\x01\x39\x30\x25')
    assert apdu.haslayer('APCI')
    apci : APCI = apdu['APCI']
    assert apci.length == 20
    assert apci.type == 0x00
    assert apci.Tx == 0x01
    assert apci.Rx == 0x01
    assert apci.haslayer('ASDU')
    asdu : ASDU = apci['ASDU']
    assert asdu.type == 0x02
    assert asdu.VSQ.SQ == 0
    assert asdu.VSQ.number == 2
    assert asdu.COT_flags == 0b00
    assert asdu.COT == 0x03
    assert asdu.CommonAddress == 0x01
    assert isinstance(asdu.IO, list)
    assert all(isinstance(x, IO2) for x in asdu.IO)
    assert len(asdu.IO) == 2
    assert asdu.IO[0].IOA == 1
    assert asdu.IO[0].SIQ == 0xa1
    assert asdu.IO[0].getfieldval('time') == CP24Time2a(b'\x39\x30\x25')
    assert asdu.IO[0].balanced
    assert asdu.IO[1].IOA == 2
    assert asdu.IO[1].SIQ == 0x01
    assert asdu.IO[1].getfieldval('time') == CP24Time2a(b'\x39\x30\x25')
    assert asdu.IO[1].balanced
    apdu = APDU(b'\x68\x0f\x02\x00\x02\x00\x02\x01\x03\x01\x01\x00\x00\xa1\x39\x30\x25')
    assert apdu.haslayer('APCI')
    apci : APCI = apdu['APCI']
    assert apci.length == 15
    assert apci.type == 0x00
    assert apci.Tx == 0x01
    assert apci.Rx == 0x01
    assert apci.haslayer('ASDU')
    asdu : ASDU = apci['ASDU']
    assert asdu.type == 0x02
    assert asdu.VSQ.SQ == 0
    assert asdu.VSQ.number == 1
    assert asdu.COT_flags == 0b00
    assert asdu.COT == 0x03
    assert asdu.CommonAddress == 0x01
    assert isinstance(asdu.IO, list)
    assert all(isinstance(x, IO2) for x in asdu.IO)
    assert len(asdu.IO) == 1
    assert asdu.IO[0].IOA == 1
    assert asdu.IO[0].SIQ == 0xa1
    assert asdu.IO[0].getfieldval('time') == CP24Time2a(b'\x39\x30\x25')
    assert not asdu.IO[0].balanced
    apdu = APDU(b'\x68\x16\x02\x00\x02\x00\x02\x02\x03\x01\x01\x00\x00\xa1\x39\x30\x25\x02\x00\x00\x01\x39\x30\x25')
    assert apdu.haslayer('APCI')
    apci : APCI = apdu['APCI']
    assert apci.length == 22
    assert apci.type == 0x00
    assert apci.Tx == 0x01
    assert apci.Rx == 0x01
    assert apci.haslayer('ASDU')
    asdu : ASDU = apci['ASDU']
    assert asdu.type == 0x02
    assert asdu.VSQ.SQ == 0
    assert asdu.VSQ.number == 2
    assert asdu.COT_flags == 0b00
    assert asdu.COT == 0x03
    assert asdu.CommonAddress == 0x01
    assert isinstance(asdu.IO, list)
    assert all(isinstance(x, IO2) for x in asdu.IO)
    assert len(asdu.IO) == 2
    assert asdu.IO[0].IOA == 1
    assert asdu.IO[0].SIQ == 0xa1
    assert asdu.IO[0].getfieldval('time') == CP24Time2a(b'\x39\x30\x25')
    assert not asdu.IO[0].balanced
    assert asdu.IO[1].IOA == 2
    assert asdu.IO[1].SIQ == 0x01
    assert asdu.IO[1].getfieldval('time') == CP24Time2a(b'\x39\x30\x25')
    assert not asdu.IO[1].balanced

def test_M_DP_NA_1():
    # Sequence of information objects (SQ = 0)
    apci : APCI = APCI(type=0x00, Tx=1, Rx=1)
    vsq1 : VSQ = VSQ(SQ=0, number=1)
    vsq2 : VSQ = VSQ(SQ=0, number=2)
    diq : DIQ = DIQ(quality=0b000000, DPI=0b11)
    io1 : IO3 = IO3(IOA=1, DIQ=diq, _balanced=True)
    io2 : IO3 = IO3(IOA=2, DIQ=diq, _balanced=True)
    asdu : ASDU = ASDU(type=0x03, VSQ=vsq1, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0b\x02\x00\x02\x00\x03\x01\x03\x01\x01\x00\x03'
    asdu : ASDU = ASDU(type=0x03, VSQ=vsq2, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1, io2])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0e\x02\x00\x02\x00\x03\x02\x03\x01\x01\x00\x03\x02\x00\x03'
    io1 : IO3 = IO3(IOA=1, DIQ=diq, _balanced=False)
    io2 : IO3 = IO3(IOA=2, DIQ=diq, _balanced=False)
    asdu : ASDU = ASDU(type=0x03, VSQ=vsq1, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0c\x02\x00\x02\x00\x03\x01\x03\x01\x01\x00\x00\x03'
    asdu : ASDU = ASDU(type=0x03, VSQ=vsq2, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1, io2])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x10\x02\x00\x02\x00\x03\x02\x03\x01\x01\x00\x00\x03\x02\x00\x00\x03'
    apdu = APDU(b'\x68\x0b\x02\x00\x02\x00\x03\x01\x03\x01\x01\x00\x03')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 11
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x03
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 1
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO3) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 1
    assert apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 0x01
    assert apdu['ASDU'].IO[0].DIQ.quality == 0b000000
    assert apdu['ASDU'].IO[0].DIQ.DPI == 0b11
    apdu = APDU(b'\x68\x0e\x02\x00\x02\x00\x03\x02\x03\x01\x01\x00\x03\x02\x00\x03')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 14
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x03
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 2
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO3) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 2
    assert apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 0x01
    assert apdu['ASDU'].IO[0].DIQ.quality == 0b000000
    assert apdu['ASDU'].IO[0].DIQ.DPI == 0b11
    assert apdu['ASDU'].IO[1].balanced
    assert apdu['ASDU'].IO[1].IOA == 0x02
    assert apdu['ASDU'].IO[1].DIQ.quality == 0b000000
    assert apdu['ASDU'].IO[1].DIQ.DPI == 0b11
    apdu = APDU(b'\x68\x0c\x02\x00\x02\x00\x03\x01\x03\x01\x01\x00\x00\x03')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 12
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x03
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 1
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO3) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 1
    assert not apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 0x01
    assert apdu['ASDU'].IO[0].DIQ.quality == 0b000000
    assert apdu['ASDU'].IO[0].DIQ.DPI == 0b11
    apdu = APDU(b'\x68\x10\x02\x00\x02\x00\x03\x02\x03\x01\x01\x00\x00\x03\x02\x00\x00\x03')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 16
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x03
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 2
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO3) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 2
    assert not apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 0x01
    assert apdu['ASDU'].IO[0].DIQ.quality == 0b000000
    assert apdu['ASDU'].IO[0].DIQ.DPI == 0b11
    assert not apdu['ASDU'].IO[1].balanced
    assert apdu['ASDU'].IO[1].IOA == 0x02
    assert apdu['ASDU'].IO[1].DIQ.quality == 0b000000
    assert apdu['ASDU'].IO[1].DIQ.DPI == 0b11
    # Sequence of information elements in a single information object (SQ = 1)
    vsq1 : VSQ = VSQ(SQ=1, number=1)
    vsq2 : VSQ = VSQ(SQ=1, number=2)
    io : IO3 = IO3(IOA=1, DIQ=diq, _sq=1, _number=1, _balanced=True)
    asdu : ASDU = ASDU(type=0x03, VSQ=vsq1, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=io)
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0b\x02\x00\x02\x00\x03\x81\x03\x01\x01\x00\x03'
    io : IO3 = IO3(IOA=1, DIQ=[diq, diq], _sq=1, _number=2, _balanced=True)
    asdu : ASDU = ASDU(type=0x03, VSQ=vsq2, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=io)
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0c\x02\x00\x02\x00\x03\x82\x03\x01\x01\x00\x03\x03'
    io : IO3 = IO3(IOA=1, DIQ=diq, _sq=1, _number=1, _balanced=False)
    asdu : ASDU = ASDU(type=0x03, VSQ=vsq1, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=io)
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0c\x02\x00\x02\x00\x03\x81\x03\x01\x01\x00\x00\x03'
    io : IO3 = IO3(IOA=1, DIQ=[diq, diq], _sq=1, _number=2, _balanced=False)
    asdu : ASDU = ASDU(type=0x03, VSQ=vsq2, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=io)
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0d\x02\x00\x02\x00\x03\x82\x03\x01\x01\x00\x00\x03\x03'
    apdu = APDU(b'\x68\x0b\x02\x00\x02\x00\x03\x81\x03\x01\x01\x00\x03')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 11
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x03
    assert apdu['ASDU'].VSQ.SQ == 1
    assert apdu['ASDU'].VSQ.number == 1
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, IO3)
    assert apdu['ASDU'].IO.balanced
    assert apdu['ASDU'].IO.IOA == 0x01
    assert isinstance(apdu['ASDU'].IO.DIQ, list)
    assert all(isinstance(x, DIQ) for x in apdu['ASDU'].IO.DIQ)
    assert len(apdu['ASDU'].IO.DIQ) == 1
    assert apdu['ASDU'].IO.DIQ[0].quality == 0b000000
    assert apdu['ASDU'].IO.DIQ[0].DPI == 0b11
    apdu = APDU(b'\x68\x0c\x02\x00\x02\x00\x03\x82\x03\x01\x01\x00\x03\x03')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 12
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x03
    assert apdu['ASDU'].VSQ.SQ == 1
    assert apdu['ASDU'].VSQ.number == 2
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, IO3)
    assert apdu['ASDU'].IO.balanced
    assert apdu['ASDU'].IO.IOA == 0x01
    assert isinstance(apdu['ASDU'].IO.DIQ, list)
    assert all(isinstance(x, DIQ) for x in apdu['ASDU'].IO.DIQ)
    assert len(apdu['ASDU'].IO.DIQ) == 2
    assert apdu['ASDU'].IO.DIQ[0].quality == 0b000000
    assert apdu['ASDU'].IO.DIQ[0].DPI == 0b11
    assert apdu['ASDU'].IO.DIQ[1].quality == 0b000000
    assert apdu['ASDU'].IO.DIQ[1].DPI == 0b11
    apdu = APDU(b'\x68\x0c\x02\x00\x02\x00\x03\x81\x03\x01\x01\x00\x00\x03')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 12
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x03
    assert apdu['ASDU'].VSQ.SQ == 1
    assert apdu['ASDU'].VSQ.number == 1
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, IO3)
    assert not apdu['ASDU'].IO.balanced
    assert apdu['ASDU'].IO.IOA == 0x01
    assert isinstance(apdu['ASDU'].IO.DIQ, list)
    assert all(isinstance(x, DIQ) for x in apdu['ASDU'].IO.DIQ)
    assert len(apdu['ASDU'].IO.DIQ) == 1
    assert apdu['ASDU'].IO.DIQ[0].quality == 0b000000
    assert apdu['ASDU'].IO.DIQ[0].DPI == 0b11
    apdu = APDU(b'\x68\x0d\x02\x00\x02\x00\x03\x82\x03\x01\x01\x00\x00\x03\x03')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 13
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x03
    assert apdu['ASDU'].VSQ.SQ == 1
    assert apdu['ASDU'].VSQ.number == 2
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, IO3)
    assert not apdu['ASDU'].IO.balanced
    assert apdu['ASDU'].IO.IOA == 0x01
    assert isinstance(apdu['ASDU'].IO.DIQ, list)
    assert all(isinstance(x, DIQ) for x in apdu['ASDU'].IO.DIQ)
    assert len(apdu['ASDU'].IO.DIQ) == 2
    assert apdu['ASDU'].IO.DIQ[0].quality == 0b000000
    assert apdu['ASDU'].IO.DIQ[0].DPI == 0b11
    assert apdu['ASDU'].IO.DIQ[1].quality == 0b000000
    assert apdu['ASDU'].IO.DIQ[1].DPI == 0b11

def test_M_DP_TA_1():
    apci : APCI = APCI(type=0x00, Tx=1, Rx=1)
    cptime : CP24Time2a = CP24Time2a(Milliseconds=12345, IV=0, GEN=0, minute=37)
    diq : DIQ = DIQ(quality=0b000000, DPI=0b11)
    vsq1 : VSQ = VSQ(SQ=0, number=1)
    vsq2 : VSQ = VSQ(SQ=0, number=2)
    io1 : IO4 = IO4(IOA=1, DIQ=diq, time=cptime, _sq=0, _balanced=True)
    io2 : IO4 = IO4(IOA=2, DIQ=diq, time=cptime, _sq=0, _balanced=True)
    asdu : ASDU = ASDU(type=0x04, VSQ=vsq1, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0e\x02\x00\x02\x00\x04\x01\x03\x01\x01\x00\x03\x39\x30\x25'
    asdu : ASDU = ASDU(type=0x04, VSQ=vsq2, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1, io2])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x14\x02\x00\x02\x00\x04\x02\x03\x01\x01\x00\x03\x39\x30\x25\x02\x00\x03\x39\x30\x25'
    io1 : IO4 = IO4(IOA=1, DIQ=diq, time=cptime, _sq=0, _balanced=False)
    io2 : IO4 = IO4(IOA=2, DIQ=diq, time=cptime, _sq=0, _balanced=False)
    asdu : ASDU = ASDU(type=0x04, VSQ=vsq1, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0f\x02\x00\x02\x00\x04\x01\x03\x01\x01\x00\x00\x03\x39\x30\x25'
    asdu : ASDU = ASDU(type=0x04, VSQ=vsq2, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1, io2])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x16\x02\x00\x02\x00\x04\x02\x03\x01\x01\x00\x00\x03\x39\x30\x25\x02\x00\x00\x03\x39\x30\x25'
    apdu = APDU(b'\x68\x0e\x02\x00\x02\x00\x04\x01\x03\x01\x01\x00\x03\x39\x30\x25')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 14
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x04
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 1
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO4) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 1
    assert apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 1
    assert apdu['ASDU'].IO[0].DIQ.quality == 0b000000
    assert apdu['ASDU'].IO[0].DIQ.DPI == 0b11
    assert apdu['ASDU'].IO[0].getfieldval('time') == cptime
    apdu = APDU(b'\x68\x14\x02\x00\x02\x00\x04\x02\x03\x01\x01\x00\x03\x39\x30\x25\x02\x00\x03\x39\x30\x25')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 20
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x04
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 2
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO4) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 2
    assert apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 1
    assert apdu['ASDU'].IO[0].DIQ.quality == 0b000000
    assert apdu['ASDU'].IO[0].DIQ.DPI == 0b11
    assert apdu['ASDU'].IO[0].getfieldval('time') == cptime
    assert apdu['ASDU'].IO[1].balanced
    assert apdu['ASDU'].IO[1].IOA == 2
    assert apdu['ASDU'].IO[1].DIQ.quality == 0b000000
    assert apdu['ASDU'].IO[1].DIQ.DPI == 0b11
    assert apdu['ASDU'].IO[1].getfieldval('time') == cptime
    apdu = APDU(b'\x68\x0f\x02\x00\x02\x00\x04\x01\x03\x01\x01\x00\x00\x03\x39\x30\x25')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 15
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x04
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 1
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO4) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 1
    assert not apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 1
    assert apdu['ASDU'].IO[0].DIQ.quality == 0b000000
    assert apdu['ASDU'].IO[0].DIQ.DPI == 0b11
    assert apdu['ASDU'].IO[0].getfieldval('time') == cptime
    apdu = APDU(b'\x68\x16\x02\x00\x02\x00\x04\x02\x03\x01\x01\x00\x00\x03\x39\x30\x25\x02\x00\x00\x03\x39\x30\x25')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 22
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x04
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 2
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO4) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 2
    assert not apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 1
    assert apdu['ASDU'].IO[0].DIQ.quality == 0b000000
    assert apdu['ASDU'].IO[0].DIQ.DPI == 0b11
    assert apdu['ASDU'].IO[0].getfieldval('time') == cptime
    assert not apdu['ASDU'].IO[1].balanced
    assert apdu['ASDU'].IO[1].IOA == 2
    assert apdu['ASDU'].IO[1].DIQ.quality == 0b000000
    assert apdu['ASDU'].IO[1].DIQ.DPI == 0b11
    assert apdu['ASDU'].IO[1].getfieldval('time') == cptime

def test_M_ST_NA_1():
    apci : APCI = APCI(type=0x00, Tx=1, Rx=1)
    spos : StepPosition = StepPosition(transient=0b0, value=0x01, QDS=0x00)
    # Sequence of information objects (SQ = 0)
    vsq1 : VSQ = VSQ(SQ=0, number=1)
    vsq2 : VSQ = VSQ(SQ=0, number=2)
    io1 : IO5 = IO5(IOA=0x01, information=spos, _sq=0, _balanced=True)
    io2 : IO5 = IO5(IOA=0x02, information=spos, _sq=0, _balanced=True)
    asdu : ASDU = ASDU(type=0x05, VSQ=vsq1, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0c\x02\x00\x02\x00\x05\x01\x03\x01\x01\x00\x01\x00'
    asdu : ASDU = ASDU(type=0x05, VSQ=vsq2, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1, io2])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x10\x02\x00\x02\x00\x05\x02\x03\x01\x01\x00\x01\x00\x02\x00\x01\x00'
    io1 : IO5 = IO5(IOA=0x01, information=spos, _sq=0, _balanced=False)
    io2 : IO5 = IO5(IOA=0x02, information=spos, _sq=0, _balanced=False)
    asdu : ASDU = ASDU(type=0x05, VSQ=vsq1, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0d\x02\x00\x02\x00\x05\x01\x03\x01\x01\x00\x00\x01\x00'
    asdu : ASDU = ASDU(type=0x05, VSQ=vsq2, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1, io2])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x12\x02\x00\x02\x00\x05\x02\x03\x01\x01\x00\x00\x01\x00\x02\x00\x00\x01\x00'
    apdu = APDU(b'\x68\x0c\x02\x00\x02\x00\x05\x01\x03\x01\x01\x00\x01\x00')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 12
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x05
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 1
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO5) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 1
    assert apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 1
    assert apdu['ASDU'].IO[0].information == spos
    apdu = APDU(b'\x68\x10\x02\x00\x02\x00\x05\x02\x03\x01\x01\x00\x01\x00\x02\x00\x01\x00')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 16
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x05
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 2
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO5) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 2
    assert apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 1
    assert apdu['ASDU'].IO[0].information == spos
    assert apdu['ASDU'].IO[1].balanced
    assert apdu['ASDU'].IO[1].IOA == 2
    assert apdu['ASDU'].IO[1].information == spos
    apdu = APDU(b'\x68\x0d\x02\x00\x02\x00\x05\x01\x03\x01\x01\x00\x00\x01\x00')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 13
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x05
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 1
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO5) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 1
    assert not apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 1
    assert apdu['ASDU'].IO[0].information == spos
    apdu = APDU(b'\x68\x12\x02\x00\x02\x00\x05\x02\x03\x01\x01\x00\x00\x01\x00\x02\x00\x00\x01\x00')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 18
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x05
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 2
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO5) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 2
    assert not apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 1
    assert apdu['ASDU'].IO[0].information == spos
    assert not apdu['ASDU'].IO[1].balanced
    assert apdu['ASDU'].IO[1].IOA == 2
    assert apdu['ASDU'].IO[1].information == spos
    # Sequence of information elements in a single information object (SQ = 1)
    vsq1 : VSQ = VSQ(SQ=1, number=1)
    vsq2 : VSQ = VSQ(SQ=1, number=2)
    io : IO5 = IO5(IOA=0x01, information=[spos], _sq=1, _number=1, _balanced=True)
    asdu : ASDU = ASDU(type=0x05, VSQ=vsq1, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=io)
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0c\x02\x00\x02\x00\x05\x81\x03\x01\x01\x00\x01\x00'
    io : IO5 = IO5(IOA=0x01, information=[spos, spos], _sq=1, _number=2, _balanced=True)
    asdu : ASDU = ASDU(type=0x05, VSQ=vsq2, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=io)
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0e\x02\x00\x02\x00\x05\x82\x03\x01\x01\x00\x01\x00\x01\x00'
    io : IO5 = IO5(IOA=0x01, information=[spos], _sq=1, _number=1, _balanced=False)
    asdu : ASDU = ASDU(type=0x05, VSQ=vsq1, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=io)
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0d\x02\x00\x02\x00\x05\x81\x03\x01\x01\x00\x00\x01\x00'
    io : IO5 = IO5(IOA=0x01, information=[spos, spos], _sq=1, _number=2, _balanced=False)
    asdu : ASDU = ASDU(type=0x05, VSQ=vsq2, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=io)
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0f\x02\x00\x02\x00\x05\x82\x03\x01\x01\x00\x00\x01\x00\x01\x00'
    apdu = APDU(b'\x68\x0c\x02\x00\x02\x00\x05\x81\x03\x01\x01\x00\x01\x00')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 12
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x05
    assert apdu['ASDU'].VSQ.SQ == 1
    assert apdu['ASDU'].VSQ.number == 1
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, IO5)
    assert apdu['ASDU'].IO.balanced
    assert apdu['ASDU'].IO.IOA == 0x01
    assert isinstance(apdu['ASDU'].IO.information, list)
    assert all(isinstance(x, StepPosition) for x in apdu['ASDU'].IO.information)
    assert all(x == spos for x in apdu['ASDU'].IO.information)
    assert len(apdu['ASDU'].IO.information) == 1
    apdu = APDU(b'\x68\x0e\x02\x00\x02\x00\x05\x82\x03\x01\x01\x00\x01\x00\x01\x00')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 14
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x05
    assert apdu['ASDU'].VSQ.SQ == 1
    assert apdu['ASDU'].VSQ.number == 2
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, IO5)
    assert apdu['ASDU'].IO.balanced
    assert apdu['ASDU'].IO.IOA == 0x01
    assert isinstance(apdu['ASDU'].IO.information, list)
    assert all(isinstance(x, StepPosition) for x in apdu['ASDU'].IO.information)
    assert all(x == spos for x in apdu['ASDU'].IO.information)
    assert len(apdu['ASDU'].IO.information) == 2
    apdu = APDU(b'\x68\x0d\x02\x00\x02\x00\x05\x81\x03\x01\x01\x00\x00\x01\x00')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 13
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x05
    assert apdu['ASDU'].VSQ.SQ == 1
    assert apdu['ASDU'].VSQ.number == 1
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, IO5)
    assert not apdu['ASDU'].IO.balanced
    assert apdu['ASDU'].IO.IOA == 0x01
    assert isinstance(apdu['ASDU'].IO.information, list)
    assert all(isinstance(x, StepPosition) for x in apdu['ASDU'].IO.information)
    assert all(x == spos for x in apdu['ASDU'].IO.information)
    assert len(apdu['ASDU'].IO.information) == 1
    apdu = APDU(b'\x68\x0f\x02\x00\x02\x00\x05\x82\x03\x01\x01\x00\x00\x01\x00\x01\x00')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 15
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x05
    assert apdu['ASDU'].VSQ.SQ == 1
    assert apdu['ASDU'].VSQ.number == 2
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, IO5)
    assert not apdu['ASDU'].IO.balanced
    assert apdu['ASDU'].IO.IOA == 0x01
    assert isinstance(apdu['ASDU'].IO.information, list)
    assert all(isinstance(x, StepPosition) for x in apdu['ASDU'].IO.information)
    assert all(x == spos for x in apdu['ASDU'].IO.information)
    assert len(apdu['ASDU'].IO.information) == 2

def test_M_ST_TA_1():
    apci : APCI = APCI(type=0x00, Tx=1, Rx=1)
    cptime : CP24Time2a = CP24Time2a(Milliseconds=12345, IV=0, GEN=0, minute=37)
    vsq1 : VSQ = VSQ(SQ=0, number=1)
    vsq2 : VSQ = VSQ(SQ=0, number=2)
    io1 : IO6 = IO6(IOA=1, transient=0b0, value=0x01, QDS=0x00, time=cptime, _sq=0, _balanced=True)
    io2 : IO6 = IO6(IOA=2, transient=0b0, value=0x01, QDS=0x00, time=cptime, _sq=0, _balanced=True)
    asdu : ASDU = ASDU(type=0x06, VSQ=vsq1, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x0f\x02\x00\x02\x00\x06\x01\x03\x01\x01\x00\x01\x00\x39\x30\x25'
    asdu : ASDU = ASDU(type=0x06, VSQ=vsq2, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1, io2])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x16\x02\x00\x02\x00\x06\x02\x03\x01\x01\x00\x01\x00\x39\x30\x25\x02\x00\x01\x00\x39\x30\x25'
    io1 : IO6 = IO6(IOA=1, transient=0b0, value=0x01, QDS=0x00, time=cptime, _sq=0, _balanced=False)
    io2 : IO6 = IO6(IOA=2, transient=0b0, value=0x01, QDS=0x00, time=cptime, _sq=0, _balanced=False)
    asdu : ASDU = ASDU(type=0x06, VSQ=vsq1, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x10\x02\x00\x02\x00\x06\x01\x03\x01\x01\x00\x00\x01\x00\x39\x30\x25'
    asdu : ASDU = ASDU(type=0x06, VSQ=vsq2, COT_flags=0b00, COT=0x03, CommonAddress=0x01, IO=[io1, io2])
    apdu : APDU = APDU()/apci/asdu
    assert apdu.build() == b'\x68\x18\x02\x00\x02\x00\x06\x02\x03\x01\x01\x00\x00\x01\x00\x39\x30\x25\x02\x00\x00\x01\x00\x39\x30\x25'
    apdu = APDU(b'\x68\x0f\x02\x00\x02\x00\x06\x01\x03\x01\x01\x00\x01\x00\x39\x30\x25')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 15
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x06
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 1
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO6) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 1
    assert apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 1
    assert apdu['ASDU'].IO[0].transient == 0
    assert apdu['ASDU'].IO[0].value == 1
    assert apdu['ASDU'].IO[0].QDS == 0x00
    assert apdu['ASDU'].IO[0].getfieldval('time') == cptime
    apdu = APDU(b'\x68\x16\x02\x00\x02\x00\x06\x02\x03\x01\x01\x00\x01\x00\x39\x30\x25\x02\x00\x01\x00\x39\x30\x25')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 22
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x06
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 2
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO6) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 2
    assert apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 1
    assert apdu['ASDU'].IO[0].transient == 0
    assert apdu['ASDU'].IO[0].value == 1
    assert apdu['ASDU'].IO[0].QDS == 0x00
    assert apdu['ASDU'].IO[0].getfieldval('time') == cptime
    assert apdu['ASDU'].IO[1].balanced
    assert apdu['ASDU'].IO[1].IOA == 2
    assert apdu['ASDU'].IO[1].transient == 0
    assert apdu['ASDU'].IO[1].value == 1
    assert apdu['ASDU'].IO[1].QDS == 0x00
    assert apdu['ASDU'].IO[1].getfieldval('time') == cptime
    apdu = APDU(b'\x68\x10\x02\x00\x02\x00\x06\x01\x03\x01\x01\x00\x00\x01\x00\x39\x30\x25')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 16
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x06
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 1
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO6) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 1
    assert not apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 1
    assert apdu['ASDU'].IO[0].transient == 0
    assert apdu['ASDU'].IO[0].value == 1
    assert apdu['ASDU'].IO[0].QDS == 0x00
    assert apdu['ASDU'].IO[0].getfieldval('time') == cptime
    apdu = APDU(b'\x68\x18\x02\x00\x02\x00\x06\x02\x03\x01\x01\x00\x00\x01\x00\x39\x30\x25\x02\x00\x00\x01\x00\x39\x30\x25')
    assert apdu.haslayer('APCI')
    assert apdu['APCI'].type == 0x00
    assert apdu['APCI'].length == 24
    assert apdu['APCI'].Tx == 1
    assert apdu['APCI'].Rx == 1
    assert apdu.haslayer('ASDU')
    assert apdu['ASDU'].type == 0x06
    assert apdu['ASDU'].VSQ.SQ == 0
    assert apdu['ASDU'].VSQ.number == 2
    assert apdu['ASDU'].COT_flags == 0b00
    assert apdu['ASDU'].COT == 0x03
    assert apdu['ASDU'].CommonAddress == 0x01
    assert isinstance(apdu['ASDU'].IO, list)
    assert all(isinstance(x, IO6) for x in apdu['ASDU'].IO)
    assert len(apdu['ASDU'].IO) == 2
    assert not apdu['ASDU'].IO[0].balanced
    assert apdu['ASDU'].IO[0].IOA == 1
    assert apdu['ASDU'].IO[0].transient == 0
    assert apdu['ASDU'].IO[0].value == 1
    assert apdu['ASDU'].IO[0].QDS == 0x00
    assert apdu['ASDU'].IO[0].getfieldval('time') == cptime
    assert not apdu['ASDU'].IO[1].balanced
    assert apdu['ASDU'].IO[1].IOA == 2
    assert apdu['ASDU'].IO[1].transient == 0
    assert apdu['ASDU'].IO[1].value == 1
    assert apdu['ASDU'].IO[1].QDS == 0x00
    assert apdu['ASDU'].IO[1].getfieldval('time') == cptime
    

def test_C_SC_NA_1():
    vsq : VSQ = VSQ(SQ=0, number = 1)
    apci : APCI = APCI(type=0x00, Tx=1, Rx=1)
    io : IO45 = IO45(IOA=3, SE=1, QU=0, reserved=0, SCS=1, _balanced=True)
    asdu : ASDU = ASDU(type=0x2d, VSQ=vsq, COT=0x03, CommonAddress=0x01, IO=io)
    apdu : APDU = APDU()
    apdu /= apci/asdu
    assert apdu.build() == b'\x68\x0b\x02\x00\x02\x00\x2d\x01\x03\x01\x03\x00\x81'
    io : IO45 = IO45(IOA=3, SE=1, QU=0, reserved=0, SCS=1, _balanced=False)
    asdu : ASDU = ASDU(type=0x2d, VSQ=vsq, COT=0x03, CommonAddress=0x01, IO=io)
    apdu : APDU = APDU()
    apdu /= apci/asdu
    assert apdu.build() == b'\x68\x0c\x02\x00\x02\x00\x2d\x01\x03\x01\x03\x00\x00\x81'
    apdu = APDU(b'\x68\x0b\x02\x00\x02\x00\x2d\x01\x03\x01\x04\x00\x01')
    assert isinstance(apdu, APDU)
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert isinstance(apci, APCI)
    assert apci.length == 0x0b
    assert apci.Tx == 1
    assert apci.Rx == 1
    assert apci.haslayer(ASDU)
    asdu = apci['ASDU']
    assert isinstance(asdu, ASDU)
    assert asdu.type == 0x2d
    assert asdu.VSQ.SQ == 0
    assert asdu.VSQ.number == 1
    assert asdu.COT == 0x03
    assert asdu.CommonAddress == 0x01
    io = asdu.IO
    assert isinstance(io, IO45)
    assert io.balanced == True
    assert io.IOA == 4
    assert io.SE == 0
    assert io.SCS == 1
    apdu = APDU(b'\x68\x0c\x02\x00\x02\x00\x2d\x01\x03\x01\x04\x00\x00\x01')
    assert isinstance(apdu, APDU)
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert isinstance(apci, APCI)
    assert apci.length == 0x0c
    assert apci.Tx == 1
    assert apci.Rx == 1
    assert apci.haslayer(ASDU)
    asdu = apci['ASDU']
    assert isinstance(asdu, ASDU)
    assert asdu.type == 0x2d
    assert asdu.VSQ.SQ == 0
    assert asdu.VSQ.number == 1
    assert asdu.COT == 0x03
    assert asdu.CommonAddress == 0x01
    io = asdu.IO
    assert isinstance(io, IO45)
    assert io.balanced == False
    assert io.IOA == 4
    assert io.SE == 0
    assert io.SCS == 1
