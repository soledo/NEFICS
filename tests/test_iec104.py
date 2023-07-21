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
