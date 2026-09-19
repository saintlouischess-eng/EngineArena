import pytest
from pathlib import Path
from arena.pieces import sanitize_svg,import_set,list_sets,FILES


def test_every_advertised_builtin_has_twelve_safe_distinct_pieces(tmp_path):
    root=Path(__file__).resolve().parents[1]/'ui'/'pieces'
    sets=list_sets(tmp_path)
    assert len(sets)==6
    signatures=[]
    for entry in sets:
        assets=[(root/entry['id']/name).read_text(encoding='utf-8') for name in FILES]
        assert len(set(assets))==12
        for svg in assets:assert sanitize_svg(svg)
        signatures.append(tuple(assets))
    assert len(set(signatures))==6

def test_import_rejects_executable_external_and_entity_svg():
    for bad in ['<svg><script>alert(1)</script></svg>','<svg onload="bad()"/>','<svg><use href="https://example.test/x.svg"/></svg>','<!DOCTYPE svg [<!ENTITY x "x">]><svg/>','<svg><path fill="url(http://example.test/x)"/></svg>']:
        with pytest.raises(ValueError):sanitize_svg(bad)

def test_custom_piece_sets_are_complete_and_survive_restart(tmp_path):
    source=tmp_path/'source';source.mkdir();data=tmp_path/'data'
    for name in FILES:(source/name).write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 45 45"><circle cx="22" cy="22" r="10" fill="white"/></svg>')
    result=import_set(data,source,'Test set');assert result in list_sets(data);assert all((data/'pieces'/result['id']/f).exists() for f in FILES)
