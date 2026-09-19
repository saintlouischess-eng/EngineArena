import asyncio
from pathlib import Path
import sys
from aiohttp.test_utils import TestClient,TestServer
from arena.server import create_app


def test_connection_preview_does_not_save_or_change_profile(tmp_path):
    async def run():
        app=await create_app(tmp_path,'profile-test')
        fixture=Path(__file__).with_name('fault_engine.py')
        profile={'name':'Unsaved engine','path':sys.executable,'args':[str(fixture)],'hash':16,'threads':1}
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'profile-test'}) as client:
            response=await client.post('/api/profiles/discover',json=profile)
            assert response.status==200
            discovered=await response.json()
            assert discovered['identity']['name']=='FaultFixture 1.0'
            assert discovered['advertised']
            assert (await (await client.get('/api/profiles')).json())['total']==0
            saved=await (await client.post('/api/profiles',json=discovered|{'discover':False})).json()
            assert saved['id']
            response=await client.post('/api/profiles/discover',json=saved|{'name':'Changed but cancelled'})
            assert response.status==200
            profiles=await (await client.get('/api/profiles')).json()
            assert profiles['total']==1
            assert profiles['items'][0]['name']=='Unsaved engine'
            from arena.pieces import FILES,sanitize_svg
            for group in await (await client.get('/api/pieces')).json():
                for name in FILES:
                    response=await client.get('/pieces/'+group['id']+'/'+name)
                    assert response.status==200
                    assert sanitize_svg(await response.text())
    asyncio.run(run())
