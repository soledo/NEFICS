# Helper functions

from datetime import datetime
from nefics.protos.iec10x.packets import CP24Time2a, CP56Time2a

def time24() -> CP24Time2a:
    now = datetime.now()
    return CP24Time2a(
        Milliseconds = now.second*1000 + int(now.microsecond//1000),
        IV = 0,
        GEN = 0,
        minute = now.minute
    )

def time56() -> CP56Time2a:
    now = datetime.now()
    return CP56Time2a(
        milliseconds = now.second*1000 + int(now.microsecond//1000),
        IV = 0,
        GEN = 0,
        minute = now.minute,
        SU = 0,
        hour = now.hour,
        DOW = now.today().weekday() + 1,
        day = now.day,
        month = now.month,
        year = now.year - 2000
    )
    
