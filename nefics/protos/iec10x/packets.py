#!/usr/bin/env python3
'''Packet definitions for IEC101/104'''

# Global imports
from copy import deepcopy
from typing import Any, Optional
from scapy.packet import Packet, Padding
from scapy.fields import (
    XBitField, XByteField, XByteEnumField, XLEShortField, ByteField,
    BitField, BitEnumField, IEEEFloatField, LEThreeBytesField,
    LEShortField, LESignedShortField, LESignedIntField, LEX3BytesField,
    FlagsField, PacketLenField, FieldLenField, StrLenField, PacketField,
    XStrField, MultipleTypeField, FieldListField, PacketListField,
    ConditionalField, ShortField, LenField
)
from scapy.config import conf

# NEFICS imports

from nefics.protos.iec10x.enums import *
from nefics.protos.iec10x.fields import *

# Common IEC-10x Packets: Information Objects, ASDU and internal values

class CP24Time2a(Packet):
    name = 'CP24Time2a'
    fields_desc = [
        LEShortField('Milliseconds',0x0000),
        BitEnumField('IV', 0, 1, {0: 'valid', 1:'invalid'}),
        BitEnumField('GEN', 0, 1, {0: 'genuine', 1:'substituted'}),
        BitField('minute', 0, 6),
    ]

    def extract_padding(self, s: bytes):
        return b'', s

class CP56Time2a(Packet):
    name = 'Seven octet binary time'
    fields_desc = [
        LEShortField('milliseconds',0x0000),
        BitField('IV',0b0,1),
        BitField('GEN',0b0,1),
        BitField('minute',0b000000,6),
        BitField('SU',0b0,1),
        BitField('RES2',0b00,2),
        BitField('hour',0b00000,5),
        BitEnumField('DOW', 0x000, 3, DOW_ENUM),
        BitField('day', 0b00001, 5),
        BitField('RES3', 0x0, 4),
        BitField('month', 0x1, 4),
        BitField('RES4', 0b0, 1),
        BitField('year', 0b0000000, 7),
    ]

    def extract_padding(self, s: bytes):
        return b'', s

class IOVal(Packet):
    name = 'Information object value'
    def extract_padding(self, s: bytes):
        return b'', s

class DIQ(IOVal):
    name = 'Double-point information with quality descriptor'
    fields_desc = [
        FlagsField('quality', 0b000000, 6, DIQ_FLAGS),
        BitEnumField('DPI', 0b11, 2, DPI_ENUM),
    ]

class SOF(Packet):
    name = 'Status of file'
    fields_desc = [
        FlagsField('flags', 0b000, 3, SOF_FLAGS),
        BitEnumField('status', 0b00000, 5, SOF_ENUM)
    ]

class IOFile(Packet):
    name = 'entry'
    fields_desc = [
        LEShortField('NOF', 0x0000),
        LEThreeBytesField('LOF', 0x000000),
        PacketField('SOF', SOF(), SOF),
        PacketField('created', CP56Time2a(), CP56Time2a)
    ]

class VSQ(IOVal):
    name = 'Variable Structure Qualifier'
    fields_desc = [
        BitEnumField('SQ',0x0, 1, SQ_ENUM),
        BitField('number',0x0,7)
    ]

class StepPosition(IOVal):
    fields_desc=[
        BitField('transient', 0b0, 1),
        BitField('value', 0b0000000, 7),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
    ]

class Bitstring32(IOVal):
    name = 'Bitstring 32 bit'
    fields_desc=[
        XBitField('BSI', 0x00, 32),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
    ]

class NormalizedValue(IOVal):
    name = 'Normalized value'
    fields_desc = [
        NVA('NVA', 0.0),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
    ]

class ScaledValue(IOVal):
    name = 'Scaled value'
    fields_desc = [
        LESignedShortField('SVA', 0x0000),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
    ]

class ShortFloat(IOVal):
    name = 'Short floating point number'
    fields_desc = [
        IEEEFloatField('value', 0.0),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
    ]

class BCR(IOVal):
    name = 'Binary counter reading'
    fields_desc = [
        LESignedIntField('value', 0),
        FlagsField('flags', 0b000, 3, BCR_FLAGS),
        BitField('sequence', 0b00000, 5),
    ]

class StatusChange(IOVal):
    name = 'Status change detection'
    fields_desc = [
        BBitField('status', 0x0000, 16),
        BBitField('change', 0x0000, 16),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
    ]

class VTI(IOVal):
    name = 'Value with transient Value state indication'
    fields_desc = [
        BitField('transient', 0b0, 1),
        BitField('value', 0b0000000, 7),
    ]

class QCC(IOVal):
    name = 'Qualifier of counter interrogation command'
    fields_desc = [
        BitEnumField('FRZ', 0b00, 2, FRZ_ENUM),
        BitEnumField('RQT', 0b000000, 6, RQT_ENUM)
    ]

class QPM(IOVal):
    name = 'Qualifier of parameter of measured values'
    fields_desc = [
        FlagsField('parameter', 0b00, 2, LPCPOP_FLAGS),
        BitEnumField('KPA', 0b000000, 6, KPA_ENUM)
    ]

class FRQ(IOVal):
    name = 'File ready qualifier'
    fields_desc = [
        BitField('PN', 0b0, 1),
        BitEnumField('qualifier', 0b0000000, 7, FRQ_ENUM)
    ]

class SRQ(IOVal):
    name = 'Section ready qualifier'
    fields_desc = [
        BitField('ready', 0b0, 1),
        BitEnumField('qualifier', 0b000000, 7, SRQ_ENUM)
    ]

class SCQ(IOVal):
    name = 'Select and call qualifier'
    fields_desc = [
        BitEnumField('error', 0x0, 4, SCQ_ENUM_B),
        BitEnumField('qualifier', 0x0, 4, SCQ_ENUM_A)
    ]

class AFQ(IOVal):
    name = 'Acknowledge file or section qualifier'
    fields_desc = [
        BitEnumField('error', 0x0, 4, AFQ_ENUM_B),
        BitEnumField('qualifier', 0x0, 4, AFQ_ENUM_A)
    ]

class IO(Packet):
    name = 'Information object'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _iolen: int = 1, _number : Optional[int] = None, _balanced : Optional[bool] = None, **fields: Any) -> None:
        self.iolen : int = _iolen
        self.sq : int = _sq if _iolen > 0 else 0
        if _balanced:
            self.balanced : bool = _balanced
            if len(_pkt):
                self.number : int = (len(_pkt) - 2) // self.iolen if self.iolen > 0 else 0
            else:
                self.number : Optional[int] = _number
        elif _balanced is not None:
            self.balanced : bool = _balanced
            if len(_pkt):
                self.number : int = (len(_pkt) - 3) // self.iolen if self.iolen > 0 else 0
            else:
                self.number : Optional[int] = _number
        else:
            if len(_pkt):
                if _iolen > 0 :
                    if _number:
                        self.balanced = (len(_pkt) - (_number * _iolen)) == 2
                    else:
                        self.balanced : bool = len(_pkt) - 2 > 0 and (float(len(_pkt) - 2)/float(_iolen)).is_integer() if _sq == 1 else (float(len(_pkt))/float(_iolen + 2)).is_integer()
                    if self.balanced:
                        self.number : int = (len(_pkt) - 2) // _iolen if _sq == 1 else len(_pkt) // (_iolen + 2)
                    else:                        
                        self.number : int = (len(_pkt) - 3) // _iolen if _sq == 1 else len(_pkt) // (_iolen + 3)
                else:
                    self.balanced : bool = len(_pkt) % 2 == 0
                    self.number : int = len(_pkt) // 2 if self.balanced else len(_pkt) // 3
            else:
                self.balanced : bool = True
                self.number : Optional[int] = _number
        super().__init__(_pkt, post_transform, _internal, _underlayer, **fields)
    
    def clone_with(self, payload: Optional[Any] = None, **kargs: Any) -> Any:
        # type: (Optional[Any], **Any) -> Any
        pkt = self.__class__(_sq=self.sq, _number=self.number, _balanced=self.balanced)
        pkt.explicit = 1
        pkt.fields = kargs
        pkt.default_fields = self.copy_fields_dict(self.default_fields)
        pkt.overloaded_fields = self.overloaded_fields.copy()
        pkt.time = self.time
        pkt.underlayer = self.underlayer
        pkt.parent = self.parent
        pkt.post_transforms = self.post_transforms
        pkt.raw_packet_cache = self.raw_packet_cache
        pkt.raw_packet_cache_fields = self.copy_fields_dict(
            self.raw_packet_cache_fields
        )
        pkt.wirelen = self.wirelen
        pkt.comment = self.comment
        if payload is not None:
            pkt.add_payload(payload)
        return pkt

    def copy(self) -> Packet:
        """Returns a deep copy of the instance."""
        clone = self.__class__(_sq=self.sq, _number=self.number, _balanced=self.balanced)
        clone.fields = self.copy_fields_dict(self.fields)
        clone.default_fields = self.copy_fields_dict(self.default_fields)
        clone.overloaded_fields = self.overloaded_fields.copy()
        clone.underlayer = self.underlayer
        clone.parent = self.parent
        clone.explicit = self.explicit
        clone.raw_packet_cache = self.raw_packet_cache
        clone.raw_packet_cache_fields = self.copy_fields_dict(
            self.raw_packet_cache_fields
        )
        clone.wirelen = self.wirelen
        clone.post_transforms = self.post_transforms[:]
        clone.payload = self.payload.copy()
        clone.payload.add_underlayer(clone)
        clone.time = self.time
        clone.comment = self.comment
        return clone

    def extract_padding(self, s: bytes):
        return b'', s

class IO1(IO):
    name = 'Single-point information without time tag'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        MultipleTypeField(
            [
                (FieldListField('SIQ', [], FlagsField('', 0x00, 8, SIQ_FLAGS), length_from=lambda pkt: pkt.number), lambda pkt: pkt.sq == 1 and pkt.number > 1),
            ],
            FlagsField('SIQ', 0x00, 8, SIQ_FLAGS)
        )
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x01], _number=_number, _balanced=_balanced, **fields)

class IO2(IO):
    name = 'Single-Point information with time tag'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        FlagsField('SIQ', 0x00, 8, SIQ_FLAGS),
        PacketField('time', CP24Time2a(b'\x00\x00\x00'), CP24Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x02], _number=_number, _balanced=_balanced, **fields)

class IO3(IO):
    name = 'Double-point information without time tag'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        MultipleTypeField(
            [
                (PacketListField('DIQ', [], DIQ, count_from=lambda pkt: pkt.number), lambda pkt: pkt.sq == 1),
            ],
            PacketField('DIQ', DIQ(b'\x03'), DIQ)
        )
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x03], _number=_number, _balanced=_balanced, **fields)

class IO4(IO):
    name = 'Double-point information with time tag'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        PacketField('DIQ', DIQ(b'\x03'), DIQ),
        PacketField('time', CP24Time2a(b'\x00\x00\x00'), CP24Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x04], _number=_number, _balanced=_balanced, **fields)

class IO5(IO):
    name = 'Step position information'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        MultipleTypeField(
            [
                (PacketListField('information', [], StepPosition, count_from=lambda pkt: pkt.number), lambda pkt: pkt.sq == 1),
            ],
            PacketField('information', StepPosition(b'\x00\x00'), StepPosition)
        )
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x05], _number=_number, _balanced=_balanced, **fields)

class IO6(IO):
    name = 'Step position information with time tag'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        BitField('transient', 0b0, 1),
        BitField('value', 0b0000000, 7),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
        PacketField('time', CP24Time2a(b'\x00\x00\x00'), CP24Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x06], _number=_number, _balanced=_balanced, **fields)

class IO7(IO):
    name = 'Bitstring of 32 bit'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        MultipleTypeField(
            [
                (PacketListField('Bitstring', [], Bitstring32, count_from=lambda pkt: pkt.number), lambda pkt: pkt.sq == 1),
            ],
            PacketField('Bitstring', Bitstring32(), Bitstring32)
        )
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x07], _number=_number, _balanced=_balanced, **fields)

class IO8(IO):
    name = 'Bitstring of 32 bit with time tag'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        XBitField('BSI', 0x00, 32),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
        PacketField('time', CP24Time2a(b'\x00\x00\x00'), CP24Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x08], _number=_number, _balanced=_balanced, **fields)

class IO9(IO):
    name = 'Measured value, normalized value'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        MultipleTypeField(
            [
                (PacketListField('value', [], NormalizedValue, count_from=lambda pkt: pkt.number), lambda pkt: pkt.sq == 1),
            ],
            PacketField('value', NormalizedValue(), NormalizedValue)
        )
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x09], _number=_number, _balanced=_balanced, **fields)

class IO10(IO):
    name = 'Measured value, normalized value with time tag'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        NVA('NVA', 0.0),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
        PacketField('time', CP24Time2a(), CP24Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x0a], _number=_number, _balanced=_balanced, **fields)

class IO11(IO):
    name = 'Measured value, scaled value'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        MultipleTypeField(
            [
                (PacketListField('value', [], ScaledValue, count_from=lambda pkt: pkt.number), lambda pkt: pkt.sq == 1),
            ],
            PacketField('value', ScaledValue(), ScaledValue)
        )
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x0b], _number=_number, _balanced=_balanced, **fields)

class IO12(IO):
    name = 'Measured value, scaled value with time tag'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        LESignedShortField('SVA', 0x0000),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
        PacketField('time', CP24Time2a(), CP24Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x0c], _number=_number, _balanced=_balanced, **fields)

class IO13(IO):
    name = 'Measured value, short floating point number'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        MultipleTypeField(
            [
                (PacketListField('value', [], ShortFloat, count_from=lambda pkt: pkt.number), lambda pkt: pkt.sq == 1),
            ],
            PacketField('value', ShortFloat(), ShortFloat)
        )
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x0d], _number=_number, _balanced=_balanced, **fields)

class IO14(IO):
    name = 'Measured value, short floating point number with time tag'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        IEEEFloatField('value', 0.0),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
        PacketField('time', CP24Time2a(), CP24Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x0e], _number=_number, _balanced=_balanced, **fields)

class IO15(IO):
    name = 'Integrated totals'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        MultipleTypeField(
            [
                (PacketListField('BCR', [], BCR, count_from=lambda pkt: pkt.number), lambda pkt: pkt.sq == 1),
            ],
            PacketField('BCR', BCR(), BCR)
        )
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x0f], _number=_number, _balanced=_balanced, **fields)

class IO16(IO):
    name = 'Integrated totals with time tag'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        PacketField('BCR', BCR(), BCR),
        PacketField('time', CP24Time2a(), CP24Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x10], _number=_number, _balanced=_balanced, **fields)

class IO17(IO):
    name = 'Event of protection equipment with time tag'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        FlagsField('flags', 0b00000, 5, SEP_FLAGS),
        BitField('reserved', 0b0, 1),
        BitEnumField('event_state', 0b01, 2, ES_ENUM),
        LEShortField('elapsed_time', 0x0000),
        PacketField('time', CP24Time2a(), CP24Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x11], _number=_number, _balanced=_balanced, **fields)

class IO18(IO):
    name = 'Packed start events of protection equipment with time tag'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        FlagsField('SPE', 0x00, 8, SPE_FLAGS),
        FlagsField('QDP', 0x00, 8, QDP_FLAGS),
        LEShortField('relay_duration', 0x0000),
        PacketField('time', CP24Time2a(), CP24Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x12], _number=_number, _balanced=_balanced, **fields)

class IO19(IO):
    name = 'Packed output circuit information of protection equipment with time tag'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        FlagsField('OCI', 0x00, 8, OCI_FLAGS),
        FlagsField('QDP', 0x00, 8, QDP_FLAGS),
        LEShortField('relay_time', 0x0000),
        PacketField('time', CP24Time2a(), CP24Time2a),
    ]
    
    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x13], _number=_number, _balanced=_balanced, **fields)

class IO20(IO):
    name = 'Packed single-point information with status change detection'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        MultipleTypeField(
            [
                (PacketListField('SCD', [], StatusChange, count_from=lambda pkt: pkt.number), lambda pkt: pkt.sq == 1),
            ],
            PacketField('SCD', StatusChange(), StatusChange)
        )
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x14], _number=_number, _balanced=_balanced, **fields)

class IO21(IO):
    name = 'Measured value, normalized value without quality descriptor'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        MultipleTypeField(
            [
                (FieldListField('NVA', [], NVA, count_from=lambda pkt: pkt.number), lambda pkt: pkt.sq == 1),
            ],
            NVA('NVA', 0x0000)
        )
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x15], _number=_number, _balanced=_balanced, **fields)

class IO30(IO):
    name = 'Single-point information with time tag CP56Time2a'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        FlagsField('SIQ', 0x00, 8, SIQ_FLAGS),
        PacketField('time', CP56Time2a(), CP56Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x1e], _number=_number, _balanced=_balanced, **fields)

class IO31(IO):
    name = 'Double-point information with time tag CP56Time2a'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        PacketField('DIQ', 0x00, DIQ),
        PacketField('time', CP56Time2a(), CP56Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x1f], _number=_number, _balanced=_balanced, **fields)

class IO32(IO):
    name = 'Step position information with time tag CP56Time2a'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        PacketField('VTI', 0x00, VTI),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
        PacketField('time', CP56Time2a(), CP56Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x20], _number=_number, _balanced=_balanced, **fields)

class IO33(IO):
    name = 'Bitstring of 32 bits with time tag CP56Time2a'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        PacketField('BSI', 0x00000000, Bitstring32),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
        PacketField('time', CP56Time2a(), CP56Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x21], _number=_number, _balanced=_balanced, **fields)

class IO34(IO):
    name = 'Measured value, normalized value with time tag CP56Time2a'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        NVA('NVA',0x0000),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
        PacketField('time', CP56Time2a(), CP56Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x22], _number=_number, _balanced=_balanced, **fields)

class IO35(IO):
    name = 'Measured value, scaled value with time tag CP56Time2a'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        LESignedShortField('SVA', 0x0000),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
        PacketField('time', CP56Time2a(), CP56Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x23], _number=_number, _balanced=_balanced, **fields)

class IO36(IO):
    name = 'Measured value, short floating point number with time tag CP56Time2a'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        IEEEFloatField('value', 0.0),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
        PacketField('time', CP56Time2a(), CP56Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x24], _number=_number, _balanced=_balanced, **fields)

class IO37(IO):
    name = 'Integrated totals with time tag CP56Time2a'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        PacketField('BCR', 0x0000000000, BCR),
        PacketField('time', CP56Time2a(), CP56Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x25], _number=_number, _balanced=_balanced, **fields)

class IO38(IO):
    name = 'Event of protection equipment with time tag CP56Time2a'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        FlagsField('flags', 0b00000, 5, SEP_FLAGS),
        BitField('reserved', 0b0, 1),
        BitEnumField('event_state', 0b01, 2, ES_ENUM),
        LEShortField('elapsed_time', 0x0000),
        PacketField('time', CP56Time2a(), CP56Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x26], _number=_number, _balanced=_balanced, **fields)

class IO39(IO):
    name = 'Packed start events of protection equipment with time tag CP56Time2a'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        FlagsField('SPE', 0x00, 8, SPE_FLAGS),
        FlagsField('QDP', 0x00, 8, QDP_FLAGS),
        LEShortField('relay_duration', 0x0000),
        PacketField('time', CP56Time2a(), CP56Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x27], _number=_number, _balanced=_balanced, **fields)

class IO40(IO):
    name = 'Packed output circuit information of protection equipment with time tag CP56Time2a'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        FlagsField('OCI', 0x00, 8, OCI_FLAGS),
        FlagsField('QDP', 0x00, 8, QDP_FLAGS),
        LEShortField('relay_time', 0x0000),
        PacketField('time', CP56Time2a(), CP56Time2a),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x28], _number=_number, _balanced=_balanced, **fields)

class IO45(IO):
    name = 'Single Command'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        BitEnumField('SE',0b0, 1, SE_ENUM),
        BitField('QU', 0b00000, 5),
        BitField('reserved',0b0, 1),
        BitEnumField('SCS', 0, 1, SC_ENUM)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x2d], _number=_number, _balanced=_balanced, **fields)

class IO46(IO):
    name = 'Double Command'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        BitEnumField('SE',0b0, 1, SE_ENUM),
        BitField('QU', 0b00000, 5),
        BitEnumField('DCS', 0b01, 2, DC_ENUM)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x2e], _number=_number, _balanced=_balanced, **fields)

class IO47(IO):
    name = 'Regulating step command'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        BitEnumField('SE', 0b0, 1, SE_ENUM),
        BitField('QU', 0b00000, 5),
        BitEnumField('RCS', 0b00, 2, RCS_ENUM),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x2f], _number=_number, _balanced=_balanced, **fields)

class IO48(IO):
    name = 'Set-point command, normalized value'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        NVA('NVA', 0x0000),
        BitEnumField('SE', 0b0, 1, SE_ENUM),
        BitField('QL', 0b0000000, 7),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x30], _number=_number, _balanced=_balanced, **fields)

class IO49(IO):
    name = 'Set-point command, scaled value'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        LESignedShortField('SVA', 0x0000),
        BitEnumField('SE', 0b0, 1, SE_ENUM),
        BitField('QL', 0b0000000, 7),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x31], _number=_number, _balanced=_balanced, **fields)

class IO50(IO):
    name = 'Set-point command, short floating point number'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        IEEEFloatField('value', 0.0),
        BitEnumField('SE', 0b0, 1, SE_ENUM),
        BitField('QL', 0b0000000, 7),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x32], _number=_number, _balanced=_balanced, **fields)

class IO51(IO):
    name = 'Bitstring of 32 bit'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        XBitField('BSI', 0x00, 32),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x33], _number=_number, _balanced=_balanced, **fields)

class IO70(IO):
    name = 'End of initialization'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        BitField('after_change', 0b0, 1),
        BitEnumField('COI', 0b0000000, 7, COI_ENUM),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x46], _number=_number, _balanced=_balanced, **fields)

class IO100(IO):
    name = 'Interrogation command'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        XByteEnumField('QOI', 0x00, QOI_ENUM),
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x64], _number=_number, _balanced=_balanced, **fields)

class IO101(IO):
    name = 'Counter interrogation command'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        PacketField('QCC', QCC(), QCC)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x65], _number=_number, _balanced=_balanced, **fields)

class IO102(IO):
    name  = 'Read command'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        MultipleTypeField(
            [
                (XLEShortField('IOA', 0x0000), lambda pkt: 'balanced' in pkt.__slots__ and pkt.balanced)
            ],
            LEX3BytesField('IOA', 0x000000)
        )
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x66], _number=_number, _balanced=_balanced, **fields)

class IO103(IO):
    name = 'Clock synchronization command'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        PacketField('time', CP56Time2a(), CP56Time2a)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x67], _number=_number, _balanced=_balanced, **fields)

class IO104(IO):
    name = 'Test command'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        XLEShortField('FBP', 0x55aa)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x68], _number=_number, _balanced=_balanced, **fields)

class IO105(IO):
    name = 'Reset process command'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        XByteEnumField('QRP', 0x00, QRP_ENUM)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x69], _number=_number, _balanced=_balanced, **fields)

class IO106(IO):
    name = 'Delay acquisition command'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        LEShortField('delay_ms', 0x0000)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x6a], _number=_number, _balanced=_balanced, **fields)

class IO110(IO):
    name = 'Parameter of measured values, normalized value'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        NVA('NVA', 0.0),
        PacketField('QPM', QPM(), QPM)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x6e], _number=_number, _balanced=_balanced, **fields)

class IO111(IO):
    name = 'Parameter of measured values, scaled value'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        LESignedShortField('SVA', 0x0000),
        PacketField('QPM', QPM(), QPM)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x6f], _number=_number, _balanced=_balanced, **fields)

class IO112(IO):
    name = 'Parameter of measured values, short floating point number'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        IEEEFloatField('value', 0.0),
        PacketField('QPM', QPM(), QPM)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x70], _number=_number, _balanced=_balanced, **fields)

class IO113(IO):
    name = 'Parameter activation'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        XByteEnumField('QPA', 0x00, QPA_ENUM)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x71], _number=_number, _balanced=_balanced, **fields)

class IO120(IO):
    name = 'File ready'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        LEShortField('NOF', 0x0000),
        LEThreeBytesField('LOF', 0x000000),
        PacketField('FRQ', FRQ(), FRQ)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x78], _number=_number, _balanced=_balanced, **fields)

class IO121(IO):
    name = 'Section ready'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        LEShortField('NOF', 0x0000),
        ByteField('NOS', 0x00),
        LEThreeBytesField('LOF', 0x000000),
        PacketField('SRQ', SRQ(), SRQ)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x79], _number=_number, _balanced=_balanced, **fields)

class IO122(IO):
    name = 'Call directory, select file, call file, call section'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        LEShortField('NOF', 0x0000),
        ByteField('NOS', 0x00),
        PacketField('SCQ', SCQ(), SCQ)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x7a], _number=_number, _balanced=_balanced, **fields)

class IO123(IO):
    name = 'Last section, last segment'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        LEShortField('NOF', 0x0000),
        ByteField('NOS', 0x00),
        XByteEnumField('LSQ', 0x00, LSQ_ENUM),
        XByteField('CHS', 0x00)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x7b], _number=_number, _balanced=_balanced, **fields)

class IO124(IO):
    name = 'ACK file, ACK section'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        LEShortField('NOF', 0x0000),
        ByteField('NOS', 0x00),
        PacketField('AFQ', AFQ(), AFQ)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x7c], _number=_number, _balanced=_balanced, **fields)

class IO125(IO):
    name = 'Segment'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        LEShortField('NOF', 0x0000),
        ByteField('NOS', 0x00),
        FieldLenField('LOS', 0x00, length_of='segment', fmt='B'),
        StrLenField('segment', b'', length_from=lambda pkt: pkt.LOS, max_length=255)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, sq: int = 0, **fields: Any) -> None:
        if len(_pkt):
            plen = int(_pkt[5]) if int(_pkt[5]) == len(_pkt[6:]) else int(_pkt[6])
            plen += 4
        else:
            plen = 259
        super().__init__(_pkt, post_transform, _internal, _underlayer, sq, _iolen=plen, **fields)

class IO126(IO):
    name = 'Directory'
    __slots__ = ['sq', 'number', 'iolen', 'balanced']
    fields_desc = [
        IOA('IOA', 0x0000, check_balanced=lambda pkt: pkt.balanced),
        PacketListField('entries', [], IOFile, length_from=lambda pkt: pkt.number)
    ]

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, _sq: int = 0, _number : Optional[int] = None, _balanced: Optional[bool] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, _sq, _iolen=IO_LEN[0x7e], _number=_number, _balanced=_balanced, **fields)

class ASDU(Packet):
    name = 'ASDU'
    fields_desc = [
        XByteEnumField('type', 0x00, TYPEID_ASDU),
        PacketLenField('VSQ', VSQ(), VSQ, length_from=lambda pkt: 1),
        FlagsField('COT_flags', 0x00, 2, CAUSE_OF_TX_FLAGS),
        BitEnumField('COT', 0x00, 6, CAUSE_OF_TX),
        XByteField('CommonAddress', 0x00),
        MultipleTypeField(
            [
                (PacketListField('IO', [], lambda b: IO1(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x01),
                (PacketField('IO', IO1(), lambda b: IO1(b, _sq=1)), lambda pkt: pkt.VSQ.SQ == 1 and pkt.type == 0x01),
                (PacketListField('IO', [], IO2, count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.type == 0x02),
                (PacketListField('IO', [], lambda b: IO3(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x03),
                (PacketField('IO', IO3(), lambda b: IO3(b, _sq=1)), lambda pkt: pkt.VSQ.SQ == 1 and pkt.type == 0x03),
                (PacketListField('IO', [], IO4, count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.type == 0x04),
                (PacketListField('IO', [], lambda b: IO5(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x05),
                (PacketField('IO', IO5(), lambda b: IO5(b, _sq=1)), lambda pkt: pkt.VSQ.SQ == 1 and pkt.type == 0x05),
                (PacketListField('IO', [], IO6, count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.type == 0x06),
                (PacketListField('IO', [], lambda b: IO7(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x07),
                (PacketField('IO', IO7(), lambda b: IO7(b, _sq=1)), lambda pkt: pkt.VSQ.SQ == 1 and pkt.type == 0x07),
                (PacketListField('IO', [], IO8, count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.type == 0x08),
                (PacketListField('IO', [], lambda b: IO9(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x09),
                (PacketField('IO', IO9(), lambda b: IO9(b, _sq=1)), lambda pkt: pkt.VSQ.SQ == 1 and pkt.type == 0x09),
                (PacketListField('IO', [], IO10, count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.type == 0x0a),
                (PacketListField('IO', [], lambda b: IO11(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x0b),
                (PacketField('IO', IO11(), lambda b: IO11(b, _sq=1)), lambda pkt: pkt.VSQ.SQ == 1 and pkt.type == 0x0b),
                (PacketListField('IO', [], IO12, count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.type == 0x0c),
                (PacketListField('IO', [], lambda b: IO13(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x0d),
                (PacketField('IO', IO13(), lambda b: IO13(b, _sq=1)), lambda pkt: pkt.VSQ.SQ == 1 and pkt.type == 0x0d),
                (PacketListField('IO', [], IO14, count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.type == 0x0e),
                (PacketListField('IO', [], lambda b: IO15(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x0f),
                (PacketField('IO', IO15(), lambda b: IO15(b, _sq=1)), lambda pkt: pkt.VSQ.SQ == 1 and pkt.type == 0x0f),
                (PacketListField('IO', [], IO16, count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.type == 0x10),
                (PacketListField('IO', [], IO17, count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.type == 0x11),
                (PacketField('IO', IO18(), IO18), lambda pkt: pkt.type == 0x12),
                (PacketField('IO', IO19(), IO19), lambda pkt: pkt.type == 0x13),
                (PacketListField('IO', [], lambda b: IO20(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x14),
                (PacketField('IO', IO20(), lambda b: IO20(b, _sq=1)), lambda pkt: pkt.VSQ.SQ == 1 and pkt.type == 0x14),
                (PacketListField('IO', [], lambda b: IO21(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x15),
                (PacketField('IO', IO21(), lambda b: IO21(b, _sq=1)), lambda pkt: pkt.VSQ.SQ == 1 and pkt.type == 0x15),
                (PacketListField('IO', [], lambda b: IO30(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x1e),
                (PacketListField('IO', [], lambda b: IO31(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x1f),
                (PacketListField('IO', [], lambda b: IO32(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x20),
                (PacketListField('IO', [], lambda b: IO33(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x21),
                (PacketListField('IO', [], lambda b: IO34(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x22),
                (PacketListField('IO', [], lambda b: IO35(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x23),
                (PacketListField('IO', [], lambda b: IO36(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x24),
                (PacketListField('IO', [], lambda b: IO37(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x25),
                (PacketListField('IO', [], lambda b: IO38(b, _sq=0), count_from=lambda pkt: pkt.VSQ.number), lambda pkt: pkt.VSQ.SQ == 0 and pkt.type == 0x26),
                (PacketField('IO', IO39(), IO39), lambda pkt: pkt.type == 0x27),
                (PacketField('IO', IO40(), IO40), lambda pkt: pkt.type == 0x28),
                (PacketField('IO', IO45(), IO45), lambda pkt: pkt.type == 0x2d),
                (PacketField('IO', IO46(), IO46), lambda pkt: pkt.type == 0x2e),
                (PacketField('IO', IO47(), IO47), lambda pkt: pkt.type == 0x2f),
                (PacketField('IO', IO48(), IO48), lambda pkt: pkt.type == 0x30),
                (PacketField('IO', IO49(), IO49), lambda pkt: pkt.type == 0x31),
                (PacketField('IO', IO50(), IO50), lambda pkt: pkt.type == 0x32),
                (PacketField('IO', IO51(), IO51), lambda pkt: pkt.type == 0x33),
                (PacketField('IO', IO70(), IO70), lambda pkt: pkt.type == 0x46),
                (PacketField('IO', IO100(), IO100), lambda pkt: pkt.type == 0x64),
                (PacketField('IO', IO101(), IO101), lambda pkt: pkt.type == 0x65),
                (PacketField('IO', IO102(), IO102), lambda pkt: pkt.type == 0x66),
                (PacketField('IO', IO103(), IO103), lambda pkt: pkt.type == 0x67),
                (PacketField('IO', IO104(), IO104), lambda pkt: pkt.type == 0x68),
                (PacketField('IO', IO105(), IO105), lambda pkt: pkt.type == 0x69),
                (PacketField('IO', IO106(), IO106), lambda pkt: pkt.type == 0x6a),
                (PacketField('IO', IO110(), IO110), lambda pkt: pkt.type == 0x6e),
                (PacketField('IO', IO111(), IO111), lambda pkt: pkt.type == 0x6f),
                (PacketField('IO', IO112(), IO112), lambda pkt: pkt.type == 0x70),
                (PacketField('IO', IO113(), IO113), lambda pkt: pkt.type == 0x71),
                (PacketField('IO', IO120(), IO120), lambda pkt: pkt.type == 0x78),
                (PacketField('IO', IO121(), IO121), lambda pkt: pkt.type == 0x79),
                (PacketField('IO', IO122(), IO122), lambda pkt: pkt.type == 0x7a),
                (PacketField('IO', IO123(), IO123), lambda pkt: pkt.type == 0x7b),
                (PacketField('IO', IO124(), IO124), lambda pkt: pkt.type == 0x7c),
                (PacketField('IO', IO125(), IO125), lambda pkt: pkt.type == 0x7d),
                (PacketField('IO', IO126(), IO126), lambda pkt: pkt.type == 0x7e),
            ],
            XStrField('IO', b'')
        ),
    ]

    def post_dissect(self, s: bytes) -> bytes:
        if isinstance(self.IO, IO):
            io = self.IO
            nio = io.__class__(io.original, _sq=self.VSQ.SQ, _number=self.VSQ.number)
            self.IO = nio
        return s

# IEC-101 Packets (FT 1.2 Frame format)
# IEC-101 ASDU uses the balanced mode

class FT12Fixed(Packet):
    name = 'FT 1.2 Fixed length'
    fields_desc = [
        XByteField('start', 0x10),
        FlagsField('Control_Flags',0x4, 4, CONTROL_FLAGS),
        BitEnumField('fcode',0x9,4, FUNCTION_CODES),
        XByteField('address',0x00),
        XByteField('checksum', 0x00),
        XByteField('end', 0x16)
    ]

class FT12Variable(Packet):
    name = 'FT 1.2 Variable Length'
    fields_desc = [
        XByteField('start', 0x68),
        ByteField('length_1', 0x09),
        ByteField('length_2', 0x09),
        XByteField('start2', 0x68),
        FlagsField('Control_Flags',0x4, 4, CONTROL_FLAGS),
        BitEnumField('fcode',0x9,4, FUNCTION_CODES),
        XByteField('address',0x00),
        PacketLenField('LinkUserData', ASDU(), ASDU, length_from=lambda pkt: pkt.getfieldval('length_1') - 2),
        XByteField('checksum', 0x00),
        XByteField('end', 0x16)
    ]

class FT12Single(Packet):
    name = 'FT 1.2 Single character data'
    fields_desc = [
        XByteEnumField('acknowledge', 0xe5, {0xe5: 'positive', 0xa2: 'negative'})
    ]

class FT12Frame(Packet):
    name = 'FT 1.2 Frame'

    def guess_payload_class(self, payload: bytes):
        if payload[0] in [0xa2, 0xe5]:
            return FT12Single
        if payload[0] == 0x10:
            return FT12Fixed
        if payload[0] == 0x68:
            return FT12Variable
        return self.default_payload_class(payload)

# IEC_104 Packets

class APCI(Packet):
    name = 'Application Protocol Control Information'
    fields_desc = [
        XByteField('Start', 0x68),
        LenField('length', None, adjust=lambda x: x + 4),
        XByteEnumField('type', 0x00, APCI_TYPE),
        ConditionalField(XByteField('UType', 0x01), lambda pkt: pkt.type == 0x03),
        ConditionalField(ShortField('Tx', 0x00), lambda pkt: pkt.type == 0x00),
        ConditionalField(ShortField('Rx', 0x00), lambda pkt: pkt.type < 3),
    ]

    def do_dissect(self, s):
        self.START = s[0]
        self.length = s[1]
        self.type = s[2] & 0x03 if bool(s[2] & 0x01) else 0x00
        if self.type == 3:
            self.UType = (s[2] & 0xfc) >> 2
        else:
            if self.type == 0:
                self.Tx = (s[3] << 7) | (s[2] >> 1)
            self.Rx = (s[5] << 7) | (s[4] >> 1)
        return s[6:]

    def dissect(self, s):
        s = self.pre_dissect(s)
        s = self.do_dissect(s)
        s = self.post_dissect(s)
        payl, pad = self.extract_padding(s)
        self.do_dissect_payload(payl)
        if pad and conf.padding:
            self.add_payload(APDU(pad))

    def do_build(self):
        s = list(range(6))
        if self.length is None:
            self.length = len(self.payload) + 4 if self.payload is not None else 4
        s[0] = 0x68
        s[1] = self.length
        if self.type == 0x03:
            s[2] = ((self.UType << 2) & 0xfc) | self.type 
            s[3] = 0
            s[4] = 0
            s[5] = 0
        else:
            if self.type == 0x00:
                s[2] = ((self.Tx << 1) & 0x00fe) | self.type
                s[3] = ((self.Tx << 1) & 0xff00) >> 8
            else:
                s[2] = self.type
                s[3] = 0
            s[4] = (self.Rx << 1) & 0x00fe
            s[5] = ((self.Rx << 1) & 0xff00) >> 8
        s = bytes(s)
        if self.haslayer('ASDU'):
            s += self.payload.build()
        return s

    def extract_padding(self, s):
        if self.type == 0x00 and self.length > 4:
            return s[:self.length - 4], s[self.length - 4:]
        return None, s
    
    def do_dissect_payload(self, s):
        if s is not None:
            p = ASDU(s, _internal=1, _underlayer=self)
            self.add_payload(p)

class APDU(Packet):
    name = 'APDU'

    def __init__(self, _pkt: bytes = b"", post_transform: Any = None, _internal: int = 0, _underlayer: Optional[Packet] = None, **fields: Any) -> None:
        super().__init__(_pkt, post_transform, _internal, _underlayer, **fields)
    def dissect(self, s):
        s = self.pre_dissect(s)
        s = self.do_dissect(s)
        s = self.post_dissect(s)
        payl, pad = self.extract_padding(s) 
        self.do_dissect_payload(payl)
        if pad and conf.padding:
            if pad[0] in [0x68]:
                self.add_payload(APDU(pad, _internal=1, _underlayer=self))
            else:
                self.add_payload(Padding(pad))

    def do_dissect(self, s):
        apci = APCI(s, _internal=1, _underlayer=self)
        self.add_payload(apci)
