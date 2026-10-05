"""Keep installer identity aligned with the application delivered to users."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from arena import __version__

ROOT=Path(__file__).resolve().parents[1]


def test_release_versions_and_installer_output_agree():
    project=ET.parse(ROOT/'desktop/EngineArena.csproj')
    assert project.find('.//Version').text==__version__
    setup=(ROOT/'installer/EngineArena.iss').read_text(encoding='utf-8')
    assert re.search(r'^AppVersion=(.+)$',setup,re.M)[1]==__version__
    filename=f'EngineArenaSetup-{__version__}-win-x64'
    assert f'OutputBaseFilename={filename}\n' in setup
    assert filename+'.exe' in (ROOT/'scripts/build-installer.ps1').read_text(encoding='utf-8')
    assert __version__ in (ROOT/'ui/index.html').read_text(encoding='utf-8')
    assert __version__ in (ROOT/'desktop/Program.cs').read_text(encoding='utf-8')


def test_installer_guide_and_notice_are_shipped():
    setup=(ROOT/'installer/EngineArena.iss').read_text(encoding='utf-8')
    notice=re.search(r'^InfoBeforeFile=(.+)$',setup,re.M)[1]
    assert (ROOT/'installer'/notice).is_file()
    assert __version__ in (ROOT/'installer'/notice).read_text(encoding='utf-8')
    docs=(ROOT/'installer/public-docs.txt').read_text().splitlines()
    for name in ('USER_GUIDE.html','USER_GUIDE.md','V1_REVIEW.md'):
        assert name in docs and (ROOT/'docs'/name).is_file()
    assert r'\User guide"; Filename: "{app}\docs\USER_GUIDE.html"' in setup
