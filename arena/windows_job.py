"""Kill engine descendants when the worker exits, including forced termination."""
import os
import ctypes
from ctypes import wintypes

class Job:
    def __init__(self):
        self.handle=None
        if os.name!='nt':return
        class Basic(ctypes.Structure):
            _fields_=[('process_time',ctypes.c_int64),('job_time',ctypes.c_int64),('flags',wintypes.DWORD),('minimum',ctypes.c_size_t),('maximum',ctypes.c_size_t),('active',wintypes.DWORD),('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
        class IO(ctypes.Structure):_fields_=[(x,ctypes.c_uint64) for x in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
        class Extended(ctypes.Structure):_fields_=[('basic',Basic),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
        self.k=ctypes.WinDLL('kernel32',use_last_error=True)
        self.k.CreateJobObjectW.restype=wintypes.HANDLE;self.k.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR]
        self.k.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        self.k.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
        self.k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];self.k.OpenProcess.restype=wintypes.HANDLE
        self.k.CloseHandle.argtypes=[wintypes.HANDLE]
        self.handle=self.k.CreateJobObjectW(None,None);info=Extended();info.basic.flags=0x2000
        if not self.handle or not self.k.SetInformationJobObject(self.handle,9,ctypes.byref(info),ctypes.sizeof(info)):raise ctypes.WinError(ctypes.get_last_error())

    def assign(self,pid):
        if self.handle:
            handle=self.k.OpenProcess(0x0100|0x0001,False,pid)
            try:
                if not handle or not self.k.AssignProcessToJobObject(self.handle,handle):raise ctypes.WinError(ctypes.get_last_error())
            finally:
                if handle:self.k.CloseHandle(handle)

    def close(self):
        if self.handle:self.k.CloseHandle(self.handle);self.handle=None
