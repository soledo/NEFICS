#!/usr/bin/env python3
'''Custom scapy fields for IEC-101/104'''

from scapy.fields import Field, BitField, I
from scapy.packet import Packet
from scapy.volatile import VolatileValue, RandShort
from typing import Callable, Optional, Tuple, Any
from struct import unpack

class IOA(Field):

    __slots__ = ['check_balanced']

    def __init__(self, name: str, default: Any, check_balanced : Optional[Callable] = None, fmt: str = '<I') -> None:
        self.check_balanced : Optional[Callable] = check_balanced if check_balanced else None
        super().__init__(name, default, fmt)
    
    def i2len(self, pkt: Packet, x: Any) -> int:
        if self.check_balanced is not None and not self.check_balanced(pkt):
            return 3
        return 2

    def addfield(self, pkt: Packet, s: bytes, val: Optional[I]) -> bytes:
        if val is None:
            return s
        value : list[int]= []
        value.append(int(val & 0xff))
        value.append(int(val & 0xff00) >> 8)
        if self.check_balanced is not None and not self.check_balanced(pkt):
            value.append(int(val & 0xff0000) >> 16)
        return s + bytes(value)

    def getfield(self, pkt: Packet, s: bytes) -> Tuple[bytes, I]:
        if self.check_balanced is not None and not self.check_balanced(pkt):
            return s[3:], self.m2i(pkt, unpack('<I', s[:3] + b'\x00')[0])
        return s[2:], self.m2i(pkt, unpack('<H', s[:2])[0])
    
    def randval(self) -> VolatileValue:
        return RandShort()

class NVA(Field):
    def __init__(self, name: str, default: Any, fmt: str = "<e") -> None:
        super().__init__(name, default, fmt)

class BBitField(BitField):
    def i2repr(self, pkt, x) -> str:
        return f'0b{self.i2h(pkt, x):0{self.size}b}'
