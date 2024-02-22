"""
Enumerations needed as defined in RFC905
"""

'''
4.2 Types of transport protocol data units
    CR      TPDU Connection request TPDU
    CC      TPDU Connection confirm TPDU
    DR      TPDU Disconnect request TPDU
    DC      TPDU Disconnect confirm TPDU
    DT      TPDU Data TPDU
    ED      TPDU Expedited data TPDU
    AK      TPDU Data acknowledge TPDU
    EA      TPDU Expedited acknowledge TPDU
    RJ      TPDU Reject TPDU
    ER      TPDU Error TPDU
'''
TPDU_CODE_TYPES = {
    0x1: 'ED Expedited Data',
    0x2: 'EA Expedited Data Acknowledgement',
    0x5: 'RJ Reject',
    0x6: 'AK Data Acknowledgment',
    0x7: 'ER TDPU Error',
    0x8: 'DR Disconnect Request',
    0xc: 'DC Disconnect Confirm',
    0xd: 'CC Connection Confirm',
    0xe: 'CR Connection Request',
    0xf: 'DT Data'
}

"""
COTP variable part parameters as defined in the variable
part subsections of section 13 of the RFC905
"""
COTP_PARAMETER_CODES = {
    0x85: "Acknowledge time",
    0x86: "Residual error rate",
    0x87: "Priority",
    0x88: "Transit delay",
    0x89: "Throughput",
    0x8a: "Sequence number",                    # Only in AK
    0x8b: "Assignment time",
    0x8c: "Flow control confirmation",          # Only in AK
    0xc0: "TPDU Size",
    0xc1: "Calling TSAP-ID",                    # Only in CR/CC
    0xc2: "Called TSAP-ID",
    0xc3: "Checksum",
    0xc4: "Version number",
    0xc5: "Security parameters",
    0xc6: "Additional option selection",
    0xc7: "Alternative protocol class(es)",
    0xe0: "Connection clearing information",    # Only in DR
}

"""
TPDU Size parameter as defined in section 13.3.4 (b)
"""
TPDU_SIZE = {
    0x07: 128,
    0x08: 256,
    0x09: 512,
    0x0a: 1024,
    0x0b: 2048,
    0x0c: 4096,
    0x0d: 8192
}

TPDU_AOS_FLAGS = [
    'Transport expedited data transfer service',
    'Use checksum',
    'Explicit AK variant (0) / Receipt confirmation (1)',
    'Network expedited',
    '*', '*', '*', '*'
]