import ctypes
import pytest
from arena.cpu_usage import CpuUsage,ProcessorTimes,read_windows


def test_cpu_deltas_warmup_peak_idle_reset_and_topology():
    samples=iter([
        [(100,150,50),(200,200,0)],
        [(140,200,100),(300,300,0)],  # 60%, 0%; kernel already includes idle
        [(140,200,100),(300,300,0)],  # no new tick
        [(1,1,1),(1,1,1)],          # reset
        [(2,2,2)],                  # topology changed
        [(2,3,3)]])                 # fully busy
    cpu=CpuUsage(lambda:next(samples))
    assert cpu.sample()==[]
    assert cpu.sample()==[60.0,0.0]
    assert cpu.sample()==[0.0,0.0]
    assert cpu.sample()==[]
    assert cpu.sample()==[]
    assert cpu.sample()==[100.0]


def test_native_reader_resizes_and_checks_returned_layout(monkeypatch):
    calls=[]
    def query(kind,buffer,length,out):
        calls.append(length);returned=ctypes.cast(out,ctypes.POINTER(ctypes.c_uint32))
        if len(calls)==1:returned[0]=length*2;return -1073741820
        returned[0]=ctypes.sizeof(ProcessorTimes)
        buffer[0].idle=4;buffer[0].kernel=8;buffer[0].user=2
        return 0
    monkeypatch.setattr('arena.cpu_usage.query_function',lambda:query)
    assert read_windows()==[(4,8,2)] and calls[1]==calls[0]*2
    def invalid(kind,buffer,length,out):
        ctypes.cast(out,ctypes.POINTER(ctypes.c_uint32))[0]=1;return 0
    monkeypatch.setattr('arena.cpu_usage.query_function',lambda:invalid)
    with pytest.raises(OSError,match='layout'):read_windows()


def test_counter_failure_is_explicit(monkeypatch):
    monkeypatch.setattr('arena.cpu_usage.query_function',lambda:lambda *args:-1)
    with pytest.raises(OSError,match='unavailable'):read_windows()
