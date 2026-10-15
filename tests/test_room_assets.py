"""Offline room integrity/provenance; no network or production data access."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]

def test_all_room_assets_have_verified_local_provenance():
    records=json.loads((ROOT/'vendor/PolyHaven/provenance.json').read_text())
    paths={p.name for p in (ROOT/'ui/scene-assets').iterdir() if p.is_file()}
    assert paths=={r['file'] for r in records} and len(paths)==22
    for r in records:
        p=ROOT/'ui/scene-assets'/r['file']
        assert p.stat().st_size==r['bytes']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
        assert r['license']=='CC0-1.0' and r['authors']
        assert r['source'].startswith('https://polyhaven.com/a/')
    assert sum(r['bytes'] for r in records)<60_000_000

def test_four_distinct_panorama_sources_and_resolution_tiers():
    records=json.loads((ROOT/'vendor/PolyHaven/provenance.json').read_text())
    panoramas=[r for r in records if r['file'].endswith('-8192.jpg')]
    assert len({r['asset'] for r in panoramas})==4
    for room in ('club','hall','study','studio'):
        assert all((ROOT/f'ui/scene-assets/{room}-{size}.jpg').is_file() for size in (2048,4096,8192))
        assert (ROOT/f'ui/scene-assets/{room}-light.hdr').is_file()
