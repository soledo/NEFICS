"""
Basic Scapy Definitions for TPKT
(RFC 1006 - ISO Transport Service on top of the TCP Version: 3)

Source documents for these definitions:
    -   https://tools.ietf.org/html/rfc1006

Payload dissection is fixed as COTP
(ISO 8327/X.225 - Connection-Oriented Transport Protocol)
as per the common usage in IEC-61850
"""

from scapy.packet import Packet, Raw
from scapy.fields import ByteField, LenField
from .cotp.packets import COTP

TPKT_ISO_TSAP_PORT = 102
TPKT_VERSION = 0x03


class TPKT(Packet):
    """
    A TPKT consists of two parts: a packet-header and a TPDU. The
    format of the header is constant regardless of the type of packet.
    The format of the packet-header is as follows:

     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |      vrsn     |    reserved   |          packet length        |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    
    where:
    
    vrsn                        8 bits
    
    This field is always 3 for the version of the protocol described in
    this memo.

    packet length               16 bits (min=7, max=65535)

    This field contains the length of entire packet in octets,
    including packet-header. This permits a maximum TPDU size of
    65531 octets. Based on the size of the data transfer (DT) TPDU,
    this permits a maximum TSDU size of 65524 octets.
    
    The format of the TPDU is defined in [ISO8073]. Note that only
    TPDUs formatted for transport class 0 are exchanged (different
    transport classes may use slightly different formats).
    """
    name = "TPKT"
    fields_desc = [ByteField("version", TPKT_VERSION),
                   ByteField("reserved", 0x00),
                   LenField("length", None, fmt="!H", adjust=lambda x: x + 4)]
    
    def extract_padding(self, s: bytes):
        return s[:self.getfieldval('length')-4], s[self.getfieldval('length')-4:]
    
    def do_dissect_payload(self, s: bytes):
        if s is not None:
            p = COTP(s, _internal=1, _underlayer=self)
            self.add_payload(p)


