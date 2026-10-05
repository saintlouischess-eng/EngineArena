"""Per-core utilization without holding Python's GIL in Windows counter reads.

NtQuerySystemInformation's processor performance records are documented at:
https://learn.microsoft.com/windows/win32/api/winternl/nf-winternl-ntquerysysteminformation
Calls use WinDLL (which releases the GIL), only from the hardware polling thread.
Unavailable or changed native layouts produce an unavailable reading.
"""
import ctypes
from functools import lru_cache
import os


class ProcessorTimes(ctypes.Structure):
    _fields_=[('idle',ctypes.c_int64),('kernel',ctypes.c_int64),('user',ctypes.c_int64),
              ('reserved',ctypes.c_int64*2),('reserved2',ctypes.c_uint32)]


@lru_cache(maxsize=1)
def query_function():
    try:query=ctypes.WinDLL('ntdll').NtQuerySystemInformation
    except (OSError,AttributeError) as exc:raise OSError('CPU performance counters unavailable') from exc
    query.argtypes=[ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(ctypes.c_uint32)]
    query.restype=ctypes.c_int32
    return query


def read_windows():
    query=query_function();size=ctypes.sizeof(ProcessorTimes);count=max(64,os.cpu_count() or 1)
    for _ in range(4):
        buffer=(ProcessorTimes*count)();returned=ctypes.c_uint32()
        status=query(8,buffer,ctypes.sizeof(buffer),ctypes.byref(returned))
        if status>=0:
            if not returned.value or returned.value>ctypes.sizeof(buffer) or returned.value%size:
                raise OSError('Invalid CPU performance counter layout')
            return [(row.idle,row.kernel,row.user) for row in buffer[:returned.value//size]]
        if status & 0xffffffff not in (0xc0000004,0xc0000023):
            raise OSError(f'CPU performance counters unavailable (0x{status & 0xffffffff:08x})')
        count=max(count*2,(returned.value+size-1)//size)
        if count*size>16*1024*1024:break
    raise OSError('CPU performance counter buffer changed repeatedly')


class CpuUsage:
    def __init__(self,reader=None):self.reader=reader;self.previous=None

    def sample(self):
        if self.reader is None and os.name!='nt':
            import psutil
            return psutil.cpu_percent(percpu=True)
        current=(self.reader or read_windows)();previous=self.previous;self.previous=current
        if previous is None or len(previous)!=len(current):return []
        result=[]
        for before,after in zip(previous,current):
            idle,kernel,user=(new-old for old,new in zip(before,after))
            if min(idle,kernel,user)<0:return []  # counter reset / CPU topology change
            total=kernel+user  # kernel includes idle time
            result.append(min(100.0,max(0.0,100*(total-idle)/total)) if total else 0.0)
        return result
