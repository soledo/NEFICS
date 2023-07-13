#!/usr/bin/env python3
'''Custom scapy fields for IEC-101/104'''

from scapy.fields import Field, BitField
from typing import Any

class NVA(Field):
    def __init__(self, name: str, default: Any, fmt: str = "<e") -> None:
        super().__init__(name, default, fmt)

class BBitField(BitField):
    def i2repr(self, pkt, x) -> str:
        return f'0b{self.i2h(pkt, x):0{self.size}b}'
