import os
import pytest
from arena.fingerprints import capture,verify

def test_binary_and_network_change_detection(tmp_path):
    exe=tmp_path/'engine.exe';net=tmp_path/'network.nnue';exe.write_bytes(b'original executable');net.write_bytes(b'original network')
    profile={'path':str(exe),'advertised':{'EvalFile':{'type':'string','default':'network.nnue'}},'options':{}}
    profile['fingerprints']=capture(profile);verify(profile)
    assert profile['fingerprints']['networks'][0]['path']==str(net.resolve())
    net.write_bytes(b'modified network!')
    with pytest.raises(ValueError,match='changed'):verify(profile)
    profile['fingerprints']=capture(profile);exe.write_bytes(b'new binary version')
    with pytest.raises(ValueError,match='changed'):verify(profile)
