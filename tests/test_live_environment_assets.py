"""Validate shipped scenery sources and the legality of the illustrative chess line."""
import hashlib,json,re,struct
from pathlib import Path
import chess
ROOT=Path(__file__).resolve().parents[1]
def test_cc0_asset_provenance_and_compact_model():
    folder=ROOT/'vendor/MakeHuman'
    for item in json.loads((folder/'provenance.json').read_text()):
        data=(folder/item['file']).read_bytes()
        assert len(data)==item['bytes']
        assert hashlib.sha256(data).hexdigest()==item['sha256']
    assert 'CC0' in (folder/'LICENSE.txt').read_text()
    data=(ROOT/'ui/room-head.glb').read_bytes()
    assert data[:4]==b'glTF' and len(data)<3_000_000
    length,kind=struct.unpack_from('<II',data,12)
    gltf=json.loads(data[20:20+length])
    names={node.get('name') for node in gltf['nodes']}
    assert {'head','hair','scalp'}<=names
    assert not gltf.get('animations')
    assert all('uri' not in image for image in gltf['images']) # offline, self-contained

def test_background_opening_is_legal_and_castling_is_reached():
    source=(ROOT/'ui/board3d-life.js').read_text(encoding='utf-8')
    line=re.search(r"const line=\[(.*?)\]",source)[1]
    moves=re.findall(r"'([a-h][1-8][a-h][1-8])'",line)
    board=chess.Board();castles=0
    for uci in moves:
        move=board.parse_uci(uci);castles+=board.is_castling(move);board.push(move)
    assert len(moves)>=20 and castles==2 and board.is_valid()
