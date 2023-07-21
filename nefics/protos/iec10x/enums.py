#!/usr/bin/env python3
'''Various enumerations and flags defined in IEC-101 and IEC-104.'''

# ************ #
# Enumerations #
# ************ #

FUNCTION_CODES = {
    0x0: 'SEND/CONFIRM - Reset of remote link',
    0x1: 'SEND/CONFIRM - Reset of user process',
    0x2: 'SEND/CONFIRM - Reserved for balanced transmission procedure',
    0x3: 'SEND/CONFIRM - User data',
    0x4: 'SEND/NO REPLY - User data',
    0x5: 'Reserved',
    0x6: 'Reserved for special use by agreement',
    0x7: 'Reserved for special use by agreement',
    0x8: 'REQUEST for access demand',
    0x9: 'REQUEST/RESPONSE - Status of link',
    0xa: 'REQUEST/RESPONSE - User data class 1',
    0xb: 'REQUEST/RESPONSE - User data class 2',
    0xc: 'Reserved',
    0xd: 'Reserved',
    0xe: 'Reserved for special use by agreement',
    0xf: 'Reserved for special use by agreement',
}

TYPEID_ASDU = {
    0x01: 'M_SP_NA_1 (1)',
    0x02: 'M_SP_TA_1 (2)',
    0x03: 'M_DP_NA_1 (3)',
    0x04: 'M_DP_TA_1 (4)',
    0x05: 'M_ST_NA_1 (5)',
    0x06: 'M_ST_TA_1 (6)',
    0x07: 'M_BO_NA_1 (7)',
    0x08: 'M_BO_TA_1 (8)',
    0x09: 'M_ME_NA_1 (9)',
    0x0A: 'M_ME_TA_1 (10)',
    0x0B: 'M_ME_NB_1 (11)',
    0x0C: 'M_ME_TB_1 (12)',
    0x0D: 'M_ME_NC_1 (13)',
    0x0E: 'M_ME_TC_1 (14)',
    0x0F: 'M_IT_NA_1 (15)',
    0x10: 'M_IT_TA_1 (16)',
    0x11: 'M_EP_TA_1 (17)',
    0x12: 'M_EP_TB_1 (18)',
    0x13: 'M_EP_TC_1 (19)',
    0x14: 'M_PS_NA_1 (20)',
    0x15: 'M_ME_ND_1 (21)',
    0x1E: 'M_SP_TB_1 (30)',
    0x1F: 'M_DP_TB_1 (31)',
    0x20: 'M_ST_TB_1 (32)',
    0x21: 'M_BO_TB_1 (33)',
    0x22: 'M_ME_TD_1 (34)',
    0x23: 'M_ME_TE_1 (35)',
    0x24: 'M_ME_TF_1 (36)',
    0x25: 'M_IT_TB_1 (37)',
    0x26: 'M_EP_TD_1 (38)',
    0x27: 'M_EP_TE_1 (39)',
    0x28: 'M_EP_TF_1 (40)',
    0x2D: 'C_SC_NA_1 (45)',
    0x2E: 'C_DC_NA_1 (46)',
    0x2F: 'C_RC_NA_1 (47)',
    0x30: 'C_SE_NA_1 (48)',
    0x31: 'C_SE_NB_1 (49)',
    0x32: 'C_SE_NC_1 (50)',
    0x33: 'C_BO_NA_1 (51)',
    0x46: 'M_EI_NA_1 (70)',
    0x64: 'C_IC_NA_1 (100)',
    0x65: 'C_CI_NA_1 (101)',
    0x66: 'C_RD_NA_1 (102)',
    0x67: 'C_CS_NA_1 (103)',
    0x68: 'C_TS_NA_1 (104)',
    0x69: 'C_RP_NA_1 (105)',
    0x6A: 'C_CD_NA_1 (106)',
    0x6E: 'P_ME_NA_1 (110)',
    0x6F: 'P_ME_NB_1 (111)',
    0x70: 'P_ME_NC_1 (112)',
    0x71: 'P_AC_NA_1 (113)',
    0x78: 'F_FR_NA_1 (120)',
    0x79: 'F_SR_NA_1 (121)',
    0x7A: 'F_SC_NA_1 (122)',
    0x7B: 'F_LS_NA_1 (123)',
    0x7C: 'F_AF_NA_1 (124)',
    0x7D: 'F_SG_NA_1 (125)',
    0x7E: 'F_DR_TA_1 (126)',
}

CAUSE_OF_TX = {
    0: 'not used',
    1: 'per/cyc',
    2: 'back',
    3: 'spont',
    4: 'init',
    5: 'req',
    6: 'Act',
    7: 'ActCon',
    8: 'Deact',
    9: 'DeactCon',
    10: 'ActTerm',
    11: 'retrem',
    12: 'retloc',
    13: 'file',
    20: 'inrogen',
    21: 'inro1',
    22: 'inro2',
    23: 'inro3',
    24: 'inro4',
    25: 'inro5',
    26: 'inro6',
    27: 'inro7',
    28: 'inro8',
    29: 'inro9',
    30: 'inro10',
    31: 'inro11',
    32: 'inro12',
    33: 'inro13',
    34: 'inro14',
    35: 'inro15',
    36: 'inro16',
    37: 'reqcogen',
    38: 'reqco1',
    39: 'reqco2',
    40: 'reqco3',
    41: 'reqco4',
    44: 'unknown type identification',
    45: 'unknown cause of transmission',
    46: 'unknown common address of ASDU',
    47: 'unknown information object address'
}


''' Allowed cause of transmission for each type identification
    as defined in IEC 60870-5-101. Each bit represents a CoT,
    a '1' means it is used by the type identification, whereas
    a '0' means it is not used. The LSB is CoT 1, the MSB is
    CoT 47.

            44444444333333333322222222221111111111
            76543210987654321098765432109876543210987654321 '''
ALLOWED_COT = {
    0x01: 0b00000000000111111111111111110000000110000010110,
    0x02: 0b00000000000000000000000000000000000110000010100,
    0x03: 0b00000000000111111111111111110000000110000010110,
    0x04: 0b00000000000000000000000000000000000110000010100,
    0x05: 0b00000000000111111111111111110000000110000010110,
    0x06: 0b00000000000000000000000000000000000110000010100,
    0x07: 0b00000000000111111111111111110000000000000010110,
    0x08: 0b00000000000000000000000000000000000000000010100,
    0x09: 0b00000000000111111111111111110000000000000010111,
    0x0a: 0b00000000000000000000000000000000000000000010100,
    0x0b: 0b00000000000111111111111111110000000000000010111,
    0x0c: 0b00000000000000000000000000000000000000000010100,
    0x0d: 0b00000000000111111111111111110000000000000010111,
    0x0e: 0b00000000000000000000000000000000000000000010100,
    0x0f: 0b00000011111000000000000000000000000000000000100,
    0x10: 0b00000011111000000000000000000000000000000000100,
    0x11: 0b00000000000000000000000000000000000000000000100,
    0x12: 0b00000000000000000000000000000000000000000000100,
    0x13: 0b00000000000000000000000000000000000000000000100,
    0x14: 0b00000000000111111111111111110000000110000010110,
    0x15: 0b00000000000111111111111111110000000000000010111,
    0x1e: 0b00000000000000000000000000000000000110000010100,
    0x1f: 0b00000000000000000000000000000000000110000010100,
    0x20: 0b00000000000000000000000000000000000110000010100,
    0x21: 0b00000000000000000000000000000000000000000010100,
    0x22: 0b00000000000000000000000000000000000000000010100,
    0x23: 0b00000000000000000000000000000000000000000010100,
    0x24: 0b00000000000000000000000000000000000000000010100,
    0x25: 0b00000011111000000000000000000000000000000000100,
    0x26: 0b00000000000000000000000000000000000000000000100,
    0x27: 0b00000000000000000000000000000000000000000000100,
    0x28: 0b00000000000000000000000000000000000000000000100,
    0x2d: 0b11110000000000000000000000000000000001111100000,
    0x2e: 0b11110000000000000000000000000000000001111100000,
    0x2f: 0b11110000000000000000000000000000000001111100000,
    0x30: 0b11110000000000000000000000000000000001111100000,
    0x31: 0b11110000000000000000000000000000000001111100000,
    0x32: 0b11110000000000000000000000000000000001111100000,
    0x33: 0b11110000000000000000000000000000000001111100000,
    0x46: 0b00000000000000000000000000000000000000000001000,
    0x64: 0b11110000000000000000000000000000000001111100000,
    0x65: 0b11110000000000000000000000000000000001111100000,
    0x66: 0b11110000000000000000000000000000000000000010000,
    0x67: 0b11110000000000000000000000000000000000001100100,
    0x68: 0b11110000000000000000000000000000000000001100000,
    0x69: 0b11110000000000000000000000000000000000001100000,
    0x6a: 0b11110000000000000000000000000000000000001100100,
    0x6e: 0b11110000000111111111111111110000000000001100000,
    0x6f: 0b11110000000111111111111111110000000000001100000,
    0x70: 0b11110000000111111111111111110000000000001100000,
    0x71: 0b11110000000000000000000000000000000000111100000,
    0x78: 0b11110000000000000000000000000000001000000000000,
    0x79: 0b11110000000000000000000000000000001000000000000,
    0x7a: 0b11110000000000000000000000000000001000000010000,
    0x7b: 0b11110000000000000000000000000000001000000000000,
    0x7c: 0b11110000000000000000000000000000001000000000000,
    0x7d: 0b11110000000000000000000000000000001000000000000,
    0x7e: 0b00000000000000000000000000000000000000000010100,
}

IO_LEN = {
    0x01: 1,
    0x02: 4,
    0x03: 1,
    0x04: 4,
    0x05: 2,
    0x06: 5,
    0x07: 5,
    0x08: 5,
    0x09: 3,
    0x0a: 6,
    0x0b: 3,
    0x0c: 6,
    0x0d: 2,
    0x0e: 6,
    0x0f: 5,
    0x10: 8,
    0x11: 6,
    0x12: 7,
    0x13: 7,
    0x14: 5,
    0x15: 2,
    0x1e: 8,
    0x1f: 8,
    0x20: 9,
    0x21: 12,
    0x22: 10,
    0x23: 10,
    0x24: 12,
    0x25: 12,
    0x26: 10,
    0x27: 11,
    0x28: 11,
    0x2d: 1,
    0x2e: 1,
    0x2f: 1,
    0x30: 3,
    0x31: 3,
    0x32: 5,
    0x33: 4,
    0x46: 1,
    0x64: 1,
    0x65: 1,
    0x66: 0,
    0x67: 7,
    0x68: 2,
    0x69: 1,
    0x6a: 2,
    0x6e: 3,
    0x6f: 3,
    0x70: 5,
    0x71: 1,
    0x78: 6,
    0x79: 7,
    0x7a: 4,
    0x7b: 5,
    0x7c: 4,
    0x7e: 13,
}

SQ_ENUM = {
    0: 'Single',
    1: 'Sequence'
}

SC_ENUM = {
    0: 'OFF',
    1: 'ON'
}

DC_ENUM = {
    0: 'not permitted',
    1: 'OFF',
    2: 'ON',
    3: 'not permitted'
}

SE_ENUM = {
    0: 'Execute',
    1: 'Select'
}

DPI_ENUM = {
    0: 'Indeterminate/intermidiate',
    1: 'OFF',
    2: 'ON',
    3: 'Indeterminate'
}

ES_ENUM = {
    0: 'Indeterminate (0)',
    1: 'OFF',
    2: 'ON',
    3: 'Indeterminate (3)',
}

DOW_ENUM = {
    0: 'not used',
    1: 'Monday',
    2: 'Tuesday',
    3: 'Wednesday',
    4: 'Thursday',
    5: 'Friday',
    6: 'Saturday',
    7 :'Sunday',
}

RCS_ENUM = {
    0: 'not permitted',
    1: 'next step LOWER',
    2: 'next step HIGHER',
    3: 'not permitted',
}

COI_ENUM = {
    0: 'local power switch on',
    1: 'local manual reset',
    2: 'remote reset',
}
COI_ENUM.update({x: 'reserved (compatible)' for x in range(3,32)})
COI_ENUM.update({x: 'reserved (private)' for x in range(32,128)})

QOI_ENUM = {
    0 : 'not used',
    20 : 'Station interrogation (global)',
    21 : 'Interrogation of group 1',
    22 : 'Interrogation of group 2',
    23 : 'Interrogation of group 3',
    24 : 'Interrogation of group 4',
    25 : 'Interrogation of group 5',
    26 : 'Interrogation of group 6',
    27 : 'Interrogation of group 7',
    28 : 'Interrogation of group 8',
    29 : 'Interrogation of group 9',
    30 : 'Interrogation of group 10',
    31 : 'Interrogation of group 11',
    32 : 'Interrogation of group 12',
    33 : 'Interrogation of group 13',
    34 : 'Interrogation of group 14',
    35 : 'Interrogation of group 15',
    36 : 'Interrogation of group 16',
}
QOI_ENUM.update({x: 'Reserved (compatible range)' for x in range(1, 20)})
QOI_ENUM.update({x: 'Reserved (compatible range)' for x in range(37, 64)})
QOI_ENUM.update({x: 'Reserved (private)' for x in range(64, 256)})

RQT_ENUM = {
    0 : 'no counter requested (not used)',
    1 : 'request counter group 1',
    2 : 'request counter group 2',
    3 : 'request counter group 3',
    4 : 'request counter group 4',
    5 : 'general request counter',
}
RQT_ENUM.update({x: 'Reserved (compatible range)' for x in range(6, 32)})
RQT_ENUM.update({x: 'Reserved (private)' for x in range(32, 64)})

QRP_ENUM = {
    0: 'not used',
    1: 'general reset of process',
    2: 'reset of pending information with time tag of the event buffer'
}
QRP_ENUM.update({x: 'Reserved (compatible range)' for x in range(3, 128)})
QRP_ENUM.update({x: 'Reserved (private)' for x in range(128, 256)})

FRZ_ENUM = {
    0: 'read',
    1: 'counter freeze without reset',
    2: 'counter freeze with reset',
    3: 'counter reset'
}

KPA_ENUM = {
    0: 'not used',
    1: 'threshold value',
    2: 'smoothing factor',
    3: 'low limit',
    4: 'high limit'
}
KPA_ENUM.update({x: 'Reserved (compatible range)' for x in range(5, 32)})
KPA_ENUM.update({x: 'Reserved (private)' for x in range(32, 64)})

QPA_ENUM = {
    0: 'not used',
    1: 'previously loaded parameters',
    2: 'parameter of the addressed object',
    3: 'persistent cyclic or periodic transmission'
}
QPA_ENUM.update({x: 'Reserved (compatible range)' for x in range(4, 128)})
QPA_ENUM.update({x: 'Reserved (private)' for x in range(128, 256)})

FRQ_ENUM = {0: 'default'}
FRQ_ENUM.update({x: 'Reserved (compatible range)' for x in range(1, 64)})
FRQ_ENUM.update({x: 'Reserved (private)' for x in range(64, 128)})

SRQ_ENUM = FRQ_ENUM

SCQ_ENUM_A = {
    0: 'default',
    1: 'select file',
    2: 'request file',
    3: 'deactivate file',
    4: 'delete file',
    5: 'select section',
    6: 'request section',
    7: 'deactivate section'
}
SCQ_ENUM_A.update({x: 'Reserved (compatible range)' for x in range(8, 11)})
SCQ_ENUM_A.update({x: 'Reserved (private)' for x in range(11, 16)})

SCQ_ENUM_B = {
    0: 'default',
    1: 'requested memory space not available',
    2: 'checksum failed',
    3: 'unexpected communication service',
    4: 'unexpected name of file',
    5: 'unexpected name of section'
}
SCQ_ENUM_B.update({x: 'Reserved (compatible range)' for x in range(6, 11)})
SCQ_ENUM_B.update({x: 'Reserved (private)' for x in range(11, 16)})

LSQ_ENUM = {
    0: 'not used',
    1: 'file transfer without deactivation',
    2: 'file transfer with deactivation',
    3: 'section transfer without deactivation',
    4: 'section transfer with deactivation'
}
LSQ_ENUM.update({x: 'Reserved (compatible range)' for x in range(5, 128)})
LSQ_ENUM.update({x: 'Reserved (private)' for x in range(128, 256)})

AFQ_ENUM_A = {
    0: 'not used',
    1: 'positive acknowledge of file transfer',
    2: 'negative acknowledge of file transfer',
    3: 'positive acknowledge of section transfer',
    4: 'negative acknowledge of section transfer'
}
AFQ_ENUM_A.update({x: 'Reserved (compatible range)' for x in range(5, 11)})
AFQ_ENUM_A.update({x: 'Reserved (private)' for x in range(11, 16)})

AFQ_ENUM_B = SCQ_ENUM_B

SOF_ENUM = {0: 'default'}
SOF_ENUM.update({x: 'Reserved (compatible range)' for x in range(1, 16)})
SOF_ENUM.update({x: 'Reserved (compatible range)' for x in range(16, 32)})

# IEC-104 exclusive

APCI_TYPE = {
    0x00: 'I (0x00)',
    0x01: 'S (0x01)',
    0x03: 'U (0x03)'
}

UNNUMBERED_CONTROL_FIELD = {
    0x01: 'STARTDT act',
    0x02: 'STARTDT con',
    0x04: 'STOPDT act',
    0x08: 'STOPDT con',
    0x10: 'TESTFR act',
    0x20: 'TESTFR con',
}

# ************ #
#    flags     #
# ************ #

CAUSE_OF_TX_FLAGS = {
    1: 'Negative',
    2: 'Test'
}

CONTROL_FLAGS = {
    1: 'FCV',
    2: 'FCB',
    4: 'PRM',
    8: 'RES'
}

SIQ_FLAGS = {
    1:'SPI',
    16:'BL',
    32:'SB',
    64:'NT',
    128:'IV'
}

DIQ_FLAGS = {
    4:'BL',
    8:'SB',
    16:'NT',
    32:'IV'
}

QDS_FLAGS = {
    1: 'OV',
    16: 'BL',
    32: 'SB',
    64: 'NT',
    128: 'IV',
}

BCR_FLAGS = {
    1: 'CY',
    2: 'CA',
    4: 'IV',
}

SEP_FLAGS = {
    1: 'EI',
    2: 'BL',
    4: 'SB',
    8: 'NT',
    16: 'IV',
}

SPE_FLAGS = {
    1: 'GS',
    2: 'SL1',
    4: 'SL2',
    8: 'SL3',
    16: 'SIE',
    32: 'SRD',
}

QDP_FLAGS = {
    8: 'EI',
    16: 'BL',
    32: 'SB',
    64: 'NT',
    128: 'IV',
}

OCI_FLAGS = {
    1: 'GC',
    2: 'CL1',
    4: 'CL2',
    8: 'CL3',
}

LPCPOP_FLAGS = {
    1: 'LPC',
    2: 'POP'
}

SOF_FLAGS = {
    1: 'LFD',
    2: 'FOR',
    4: 'FA'
}
