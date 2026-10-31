#!/usr/bin/env python3
"""Verify a public H5 release archive before extracting it for Pages."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

def unpack(archive,checksums,output):
    archive=Path(archive);output=Path(output)
    expected={}
    for line in Path(checksums).read_text().splitlines():
        sha,name=line.split(maxsplit=1)
        if not re.fullmatch('[0-9a-f]{64}',sha) or Path(name).name!=name:raise ValueError('Invalid checksum entry')
        expected[name]=sha
    if expected.get(archive.name)!=hashlib.sha256(archive.read_bytes()).hexdigest():raise ValueError('Archive checksum mismatch')
    with zipfile.ZipFile(archive) as bundle:
        entries=bundle.infolist();names=set();total=0
        for item in entries:
            name=item.filename;path=PurePosixPath(name);total+=item.file_size
            if path.is_absolute() or '..' in path.parts or '\\' in name or stat.S_ISLNK(item.external_attr>>16):raise ValueError('Unsafe archive path')
            if item.is_dir():continue
            if name in names:raise ValueError('Duplicate archive file')
            names.add(name)
            if path.suffix.lower() not in {'.html','.css','.js','.png','.jpg','.svg','.webp','.ico','.txt','.wasm','.pck'} and name!='release.json':raise ValueError('Unexpected public artifact')
            if any(p in {'.git','sources','docs','tests','tools','domain','application','bootstrap'} for p in path.parts):raise ValueError('Development material in archive')
        if total>800*1024*1024:raise ValueError('Unexpected expanded archive size')
        required={'index.html','guide.html','spec/index.html','play/index.html','play/index.js','play/index.wasm','play/index.pck','release.json'}
        if not required<=names:raise ValueError('Required public files are missing')
        release=json.loads(bundle.read('release.json'))
        if set(release['files_sha256'])!=names-{'release.json'}:raise ValueError('Release manifest file set mismatch')
        for name,sha in release['files_sha256'].items():
            if hashlib.sha256(bundle.read(name)).hexdigest()!=sha:raise ValueError('Release content checksum mismatch')
        output.mkdir(parents=True,exist_ok=False)
        bundle.extractall(output)
    return release['version']

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path);parser.add_argument('--checksums',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print('Verified public preview:',unpack(args.archive,args.checksums,args.output))
