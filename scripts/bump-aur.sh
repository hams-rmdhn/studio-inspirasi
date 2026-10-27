#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Update PKGBUILD and .SRCINFO only after validating both candidate files.
set -euo pipefail
if [[ $# -lt 1 || $# -gt 2 || ( $# == 2 && $2 != --check ) ]]; then
 echo "usage: $0 VERSION [--check]" >&2; exit 2
fi
ver=${1#v}
[[ $ver =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'expected a stable X.Y.Z version' >&2; exit 2; }
command -v makepkg >/dev/null || { echo 'makepkg is required' >&2; exit 1; }
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
curl -fsSL "https://github.com/tulcoturo/clovercut/releases/download/v$ver/SHA256SUMS" > "$work/SHA256SUMS"
cp "$repo/assets/arch/PKGBUILD" "$work/PKGBUILD"
python3 - "$work" "$ver" <<'PY'
from pathlib import Path
import re,sys
root=Path(sys.argv[1]);version=sys.argv[2]
lines=[line.split() for line in (root/'SHA256SUMS').read_text().splitlines()]
hashes={}
for arch in ['x86_64','aarch64']:
 name=f'Clovercut-{version}-{arch}.AppImage'
 matches=[row[0] for row in lines if len(row)==2 and row[1].lstrip('*')==name]
 if len(matches)!=1 or not re.fullmatch(r'[0-9a-fA-F]{64}',matches[0]):
  raise SystemExit(f'Missing/invalid AppImage checksum: {name}')
 hashes[arch]=matches[0]
p=root/'PKGBUILD';s=p.read_text()
old=re.search(r'^pkgver=(.+)$',s,re.M).group(1)
s,n=re.subn(r'^pkgver=.+$',f'pkgver={version}',s,count=1,flags=re.M);assert n==1
if old!=version:s,n=re.subn(r'^pkgrel=.+$','pkgrel=1',s,count=1,flags=re.M);assert n==1
for arch,value in hashes.items():
 s,n=re.subn(r"^sha256sums_"+arch+r"=\('[^']*'\)$",f"sha256sums_{arch}=('{value}')",s,count=1,flags=re.M)
 assert n==1,arch
p.write_text(s)
PY
(cd "$work" && makepkg --printsrcinfo > .SRCINFO)
if [[ ${2:-} == --check ]]; then
 cmp "$work/PKGBUILD" "$repo/assets/arch/PKGBUILD"
 cmp "$work/.SRCINFO" "$repo/assets/arch/.SRCINFO"
 echo "AUR files match $ver and its published checksums"
else
 # Generate both files successfully before replacing either repository file.
 cp "$work/PKGBUILD" "$repo/assets/arch/PKGBUILD"
 cp "$work/.SRCINFO" "$repo/assets/arch/.SRCINFO"
 echo "Updated AUR files to $ver"
fi
