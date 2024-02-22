"""
Basic Scapy Definitions for COTP (ISO 8327/X.225 - Connection-Oriented Transport Protocol)

Source documents for these definitions:
    -   https://www.itu.int/rec/T-REC-X.225-199511-I/en
    -   https://www.fit.vut.cz/research/publication-file/11832/TR-61850.pdf

Limited Support for:
    - Data (DT)
    - Connection Requests (CR)
    - Connection Responses (CC)
"""


from scapy.packet import Packet
from scapy.fields import BitField, BitEnumField, ByteField, XByteField, ByteEnumField, XByteEnumField, \
                         LenField, ShortField, XShortField, XStrLenField, PacketListField, \
                         FieldLenField, FieldListField, FlagsField, ThreeBytesField, \
                         X3BytesField, XLongField, MultipleTypeField, ConditionalField, XIntField, IntField

from struct import pack, unpack

from iec61850_mms.cotp.enums import *
from iec61850_mms.iso8327_1.packets import ISO_8327_1_Session, SPDU_PAYLOADS


class COTP_Parameter(Packet):
    name = "COTP Parameter"
    fields_desc = [
        XByteEnumField("code", None, COTP_PARAMETER_CODES),
        FieldLenField("length", None, fmt="B", length_of="value"),
        MultipleTypeField(
            [
                (XStrLenField("value", None, length_from=lambda x: x.length), lambda pkt: pkt.code in [0xc1, 0xc2, 0xc5, 0xc7, 0xe0]),
                (ByteEnumField("value", 0x07, TPDU_SIZE), lambda pkt: pkt.code == 0xc0),
                (XByteField("value", 0x01), lambda pkt: pkt.code == 0xc4),
                (FlagsField("value", 0x01, 8, TPDU_AOS_FLAGS), lambda pkt: pkt.code == 0xc6),
                (ShortField("value", 0x0000), lambda pkt: pkt.code in [0x85, 0x87, 0x8a, 0x8b, 0xc3]),
                (FieldListField("value", [], ThreeBytesField('', 0), count_from=lambda pkt: pkt.length // 3), lambda pkt: pkt.code == 0x89),
                (X3BytesField("value", 0), lambda pkt: pkt == 0x86),
                (XLongField("value", 0), lambda pkt: pkt.code in [0x88, 0x8c])
            ],
            XStrLenField("value", None, length_from=lambda x: x.length)
        )
    ]

    def extract_padding(self, s):
        return '', s

class COTP_Connection_Parameter(Packet):
    name = "COTP Parameter"
    fields_desc = [
        ByteEnumField("code", None, COTP_PARAMETER_CODES)
    ]

class COTP_CR(Packet):
    '''
    Connection Request (CR) TPDU

    As defined by RFC905, section 13.3
    '''
    name = "COTP Connection Request (CR)"
    fields_desc = [
        LenField("length", None, fmt="!B", adjust=lambda x: x + 5),
        BitEnumField("TPDU", 0b1110, 4, TPDU_CODE_TYPES),
        BitField("CDT", 0b0000, 4),
        XShortField("destination_reference", None),
        XShortField("source_reference", None),
        BitField("class", 0, 4),
        BitField("reserved", 0, 2),
        BitField("extended_format", 0, 1),
        BitField("explicit", 0, 1),
        PacketListField("parameters", None, COTP_Parameter)
    ]

class COTP_CC(Packet):
    name = 'COTP Connection Confirm (CC)'
    fields_desc = COTP_CR.fields_desc


class COTP_DT(Packet):
    name = "COTP Data (DT)"
    fields_desc = [
        ByteField("length", 2),
        XByteField("TPDU", 0xf0),
        ConditionalField(XShortField("destination_reference", None), lambda pkt: pkt.length in [4, 7, 8, 11]),
        ByteField("EOT", 1),
        MultipleTypeField(
            [
                (ByteField("TPDU_NR", 0), lambda pkt: pkt.length in [4, 8]),
                (IntField("TPDU_NR", 0), lambda pkt: pkt.length in [7, 11])
            ],
            ByteField("TPDU_NR", 0)
        ),
        ConditionalField(XShortField("checksum", 0x0000), lambda pkt: pkt.length in [8, 11])
    ]

    def do_dissect(self, s):
        self.length = s[0]
        self.TPDU = s[1]
        if s[1] in [4, 7, 8, 11]:
            self.destination_reference = unpack('H', s[2:3])
            if s[1] in [4, 8]:
                self.EOT = s[4] >> 7
                self.TPDU_NR = s[4] & 0x7f
            else:
                self.EOT = s[8] >> 7
                self.TPDU_NR = unpack('<I', s[4:8]) & 0x7fffffff
        else:
            self.EOT = s[2] >> 7
            self.TPDU_NR = s[2] & 0x7f
        if s[1] in [80, 11]:
            ck = s[5:7] if s[1] == 7 else s[8:10]
            self.checksum = unpack('H', ck)
        return s[(self.length + 1):]
    
    def do_build(self):
        s = b''
        s += pack('BB', self.length, self.TPDU)
        if self.length in [4, 7, 8, 11]:
            s += pack('H', self.destination_reference)
            if self.length in [4, 8]:
                s += pack('B', ((self.EOT & 0x01) << 7) | (self.TPDU_NR & 0x7f) )
            else:
                s += pack('<I', ((self.EOT & 0x01) << 31) | (self.TPDU_NR & 0x7fffffff) )
            if self.length in [8, 11]:
                s += pack('H', self.checksum)
        else:
            s += pack('B', ((self.EOT & 0x01) << 7) | (self.TPDU_NR & 0x7f))
        return s
    
    def do_dissect_payload(self, s: bytes):
        if s is not None and int(s[0]) in SPDU_PAYLOADS.keys():
            p = ISO_8327_1_Session(s, _internal=1, _underlayer=self)
            self.add_payload(p)
    
    # def guess_payload_class(self, payload: bytes):
    #     try:
    #         if len(payload) > 0:
    #             spdu_type = int(payload[0])
    #             if spdu_type in SPDU_PAYLOADS.keys():
    #                 return ISO_8327_1_Session
    #         return self.default_payload_class(payload)
    #     except TypeError:
    #         return self.default_payload_class(payload)



COTP_TPDU_PAYLOADS = {
    # 0x10: 'ED Expedited Data',
    # 0x20: 'EA Expedited Data Acknowledgement',
    # 0x50: 'RJ Reject',
    # 0x60: 'AK Data Acknowledgment',
    # 0x70: 'ER TDPU Error',
    # 0x80: 'DR Disconnect Request',
    # 0xc0: 'DC Disconnect Confirm',
    0xd0: COTP_CC,
    0xe0: COTP_CR,
    0xf0: COTP_DT
}

class COTP(Packet):
    name = 'COTP Connection-Oriented Transport Protocol'

    def guess_payload_class(self, payload):
        ln = len(payload)
        
        if ln < 2:
            return self.default_payload_class(payload)
        
        tpdu_code = int(payload[1]) & 0xf0
        
        if tpdu_code in COTP_TPDU_PAYLOADS:
            return COTP_TPDU_PAYLOADS[tpdu_code]
        
        return self.default_payload_class(payload)


