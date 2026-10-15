"""Create a smaller extract-and-run ZIP from a verified installer payload.

No runtime files are rebuilt or altered. Matching application source must be
offered at the same public release tag; dependency notices/sources stay bundled.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--payload',type=Path,required=True)
    parser.add_argument('--public-source',type=Path,required=True)
    parser.add_argument('--version',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    assert all(c.isdigit() or c=='.' for c in args.version)
    payload=args.payload.resolve();public=args.public_source.resolve()
    manifest=json.loads((payload/'package-manifest.json').read_text(encoding='utf-8-sig'))
    assert not args.output.exists(),'Choose a new output file; do not replace a published ZIP'
    prefix='EngineArena-'+args.version
    source_url=f'https://github.com/saintlouischess-eng/EngineArena/tree/v{args.version}'
    entries=[];runtime_count=0
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        def add(name,data):
            assert not name.startswith('/') and '..' not in Path(name).parts
            archive.writestr(prefix+'/'+name,data)
            entries.append({'path':name,'bytes':len(data),'sha256':digest(data)})
        for item in manifest:
            relative=item['path'].replace('\\','/')
            if relative.startswith('Source/') or relative=='package-manifest.json':continue
            path=(payload/relative).resolve();assert path.is_relative_to(payload)
            data=path.read_bytes();assert len(data)==item['bytes'] and digest(data)==item['sha256'],relative
            if relative=='README.md' or relative.startswith('docs/'):
                override=public/relative
                if override.exists():data=override.read_bytes()
            elif relative=='NOTICE':
                data=data.decode('utf-8').replace('\r\n','\n').replace(
                    'Application source is included in the installed Source directory and the\nEngineArena GitHub repository.',
                    'Application source is included in the full installer Source directory and\nthe EngineArena GitHub repository. This smaller ZIP omits that duplicate\nfolder; matching source is available at '+source_url+'.').encode('utf-8')
                assert b'This smaller ZIP' in data,'Missing ZIP source instructions'
            else:runtime_count+=1
            add(relative,data)
        for name in ('CREDITS.md','docs/RELEASE_1_9_7.md'):
            if not any(x['path']==name for x in entries):add(name,(public/name).read_bytes())
        instructions=f'''Engine Arena {args.version} - extract-and-run ZIP

Designed by Mark Young. Coding and implementation by OpenAI Codex.

1. Extract the ENTIRE archive into a new folder. Do not launch inside the ZIP.
2. Close any other Engine Arena copy using your saved data.
3. Open EngineArena.exe.

Windows 11 x64 (Intel/AMD). Python and .NET are included. Microsoft WebView2
Runtime must already be installed. If the app reports it missing, use the full
Engine Arena installer from the same release; it includes offline WebView2 setup.

All boards, rooms, piece sets and features are included. The smaller ZIP leaves
out the offline WebView2 installer and the duplicate application-source folder.
No shortcuts, installation registration or uninstaller are created.

Saved data defaults to %LOCALAPPDATA%\\EngineArena\\Data, the SAME location used
by the installed application. Only one copy can open it at a time. To use a
different local workspace:
  EngineArena.exe --data "D:\\Engine Tests\\Arena"
Do not delete your data folder when removing the application folder.

For updates, pause/drain games and close the old app, then extract into a fresh
folder. Keep the old folder until the new copy works. Intermediate updates are
not required. Existing games, profiles, events and ratings are retained.

Application source: GPL-3.0-or-later. Corresponding source for this exact release:
  {source_url}
  https://github.com/saintlouischess-eng/EngineArena/archive/refs/tags/v{args.version}.zip
Dependency notices and applicable dependency-source archives remain in ThirdParty.
The full installer includes application source locally in its Source directory.

Optional CPU sensors require supported hardware and the elevated reader.
Optional/PawnIO_setup.exe is provided but is not run automatically by this ZIP.
Add your own engines and opening books. Engine Arena itself is unsigned.

See docs/USER_GUIDE.html, docs/RELEASE_1_9_7.md, NOTICE and LICENSE.
'''
        add('START-HERE.txt',instructions.encode('utf-8'))
        archive.writestr(prefix+'/package-manifest.json',json.dumps(entries,indent=2).encode('utf-8'))
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None
        for entry in entries:
            data=archive.read(prefix+'/'+entry['path'])
            assert len(data)==entry['bytes'] and digest(data)==entry['sha256']
    with args.output.open('rb') as file:sha=hashlib.file_digest(file,'sha256').hexdigest()
    Path(str(args.output)+'.sha256').write_text(sha+'  '+args.output.name+'\n',encoding='ascii')
    print(json.dumps({'zip':args.output.name,'bytes':args.output.stat().st_size,'sha256':sha,
                     'files_verified':len(entries)+1,'unchanged_runtime_files':runtime_count},indent=2))


if __name__=='__main__':main()
