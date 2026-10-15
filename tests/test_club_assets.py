"""Offline cast provenance, distinct models, addon integrity and legal scenery."""
import hashlib,json,re,struct
from pathlib import Path
import chess
ROOT=Path(__file__).resolve().parents[1]
def test_distinct_clothed_cast_and_source_hashes():
    folder=ROOT/'vendor/MakeHuman/club-cast'
    for record in json.loads((folder/'provenance.json').read_text()):
        data=(folder/record['file']).read_bytes()
        assert len(data)==record['bytes']
        assert hashlib.sha256(data).hexdigest()==record['sha256']
    cast=json.loads((folder/'derived.json').read_text())['cast']
    assert len({c['id'] for c in cast})==len({c['sha256'] for c in cast})==12
    cameos=[c for c in cast if c.get('cameo')]
    assert len(cameos)==6 and all(c.get('standing') for c in cameos)
    assert len({json.dumps(c['face']) for c in cameos})==6
    players=cast[:4]
    assert len({c['macro'] for c in players})==len({c['hair'] for c in players})==4
    assert len({c['clothes'] for c in players})==4
    for c in cast:
        data=(ROOT/'ui'/('club-'+c['file'])).read_bytes();assert hashlib.sha256(data).hexdigest()==c['sha256']
        assert data[:4]==b'glTF';length=struct.unpack_from('<I',data,12)[0];gltf=json.loads(data[20:20+length]);names={n.get('name') for n in gltf['nodes']}
        assert {'Skin','Eyes','Complete outfit'}<=names
        assert 'Footwear '+c['footwear'] in names
        assert any(n and n.startswith('Hair') for n in names)
        assert gltf.get('skins') and len(gltf.get('animations',[]))==1
        assert gltf['animations'][0]['name']==('Standing rest' if c.get('standing') else 'Seated rest')
        assert all('uri' not in image for image in gltf['images'])
        if c.get('cameo'):assert any('portrait bake' in image.get('name','') for image in gltf['images'])
        if c['id'] in ('hikaru','levy'):
            assert {'Beard opaque fitted volume','Beard fine growth'}<=names
            for material in gltf['materials']:
                if material.get('name','').startswith('Beard'):assert material.get('alphaMode','OPAQUE')=='OPAQUE'
    assert len({c['footwear'] for c in cast})>=8

def test_addons_are_pinned_and_use_only_local_imports():
    record=json.loads((ROOT/'vendor/Three/club-addons.json').read_text())
    assert record['license']=='MIT' and record['version']=='0.186.1'
    for item in record['files']:
        file=ROOT/'ui'/item['file'];assert hashlib.sha256(file.read_bytes()).hexdigest()==item['sha256']
        for link in re.findall(r"from ['\"]([^'\"]+)['\"]",file.read_text(encoding='utf-8')):assert link.startswith('./') and (file.parent/link).exists()

def test_illustrative_games_are_legal_and_isolated():
    source=(ROOT/'ui/board3d-club-motion.js').read_text(encoding='utf-8');line=re.search(r'const clubMoves=\[(.*?)\]',source)[1];moves=re.findall(r"'([a-h][1-8][a-h][1-8])'",line)
    board=chess.Board();castles=0
    for uci in moves:
        move=board.parse_uci(uci);castles+=board.is_castling(move);board.push(move)
    assert len(moves)==16 and castles==2
    assert '/api/' not in source and 'room-head' not in source
