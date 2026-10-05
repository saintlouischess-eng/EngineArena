import asyncio
import re
from pathlib import Path
from aiohttp.test_utils import TestClient,TestServer
from arena.pieces import sanitize_svg
from arena.server import create_app

ROOT=Path(__file__).resolve().parents[1]
COLLECTIONS=('regal','heirloom','porcelain','classic-sculpted','aurora','citadel','classic-refined','classic-bold','classic-heritage')

def test_original_artwork_uses_only_resolvable_static_vectors():
    for folder in [ROOT/'ui'/'textures',*[ROOT/'ui'/'pieces'/name for name in COLLECTIONS]]:
        for asset in folder.glob('*.svg'):
            text=asset.read_text(encoding='utf-8');assert sanitize_svg(text)
            ids=set(re.findall(r'id="([^"]+)"',text))
            assert set(re.findall(r'url\(#([^)]+)\)',text))<=ids
            assert '<image' not in text and '<filter' not in text

def test_bundled_artwork_routes_and_saved_choices(tmp_path):
    async def run():
        selected={'pieceSet':'classic-heritage','boardMaterials':{'light':'ash','dark':'ebony'}}
        app=await create_app(tmp_path,'artwork')
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'artwork'}) as client:
            for name in ('maple','ash','oak','walnut','rosewood','ebony'):
                response=await client.get(f'/textures/{name}.svg');assert response.status==200
                assert response.content_type=='image/svg+xml'
                assert (await response.text()).startswith('<svg')
                response=await client.get(f'/textures/{name}.png');assert response.status==200
                assert response.content_type=='image/png'
                data=await response.read();assert data[:8]==b'\x89PNG\r\n\x1a\n'
                import struct
                assert struct.unpack('>II',data[16:24])==(512,256)
            for path in ('/textures/unknown.svg','/textures/arena.sqlite3','/textures/%2e%2e%2fworker.py'):
                assert (await client.get(path)).status==404
            for name in COLLECTIONS:
                for side in 'wb':
                    for piece in 'KQRBNP':assert (await client.get(f'/pieces/{name}/{side}{piece}.svg')).status==200
            assert (await client.post('/api/preferences',json=selected)).status==200
        app=await create_app(tmp_path,'artwork')
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'artwork'}) as client:
            result=await (await client.get('/api/preferences')).json()
            assert result['pieceSet']==selected['pieceSet'] and result['boardMaterials']==selected['boardMaterials']
    asyncio.run(run())
