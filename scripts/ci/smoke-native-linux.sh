#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Clovercut contributors
# Install/reinstall/remove a native package in a disposable container only.
set -euo pipefail

fail() { echo "native package smoke: $*" >&2; exit 1; }

if [[ ${1:-} == --container ]]; then
  [[ $# == 4 ]] || fail 'usage: --container IMAGE PACKAGE VERSION'
  image=$2
  package=$(realpath "$3")
  version=$4
  [[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail 'invalid version'
  [[ -s $package ]] || fail 'missing package'
  case "$package" in *.deb) suffix=deb;; *.rpm) suffix=rpm;; *) fail 'expected .deb or .rpm';; esac
  script=$(realpath "${BASH_SOURCE[0]}")
  exec docker run --rm --cpus=2 --memory=4g --memory-swap=6g \
    -v "$script:/native-smoke.sh:ro" -v "$package:/pkg/clovercut.$suffix:ro" \
    "$image" bash /native-smoke.sh --inside "/pkg/clovercut.$suffix" "$version"
fi

[[ ${1:-} == --inside && $# == 3 && -f /.dockerenv ]] || fail 'installation is permitted only inside the disposable Docker container'
package=$2
version=$3
unset LD_LIBRARY_PATH
export DEBIAN_FRONTEND=noninteractive
case "$package" in
  *.deb)
    apt-get update -qq
    apt-get install -y --no-install-recommends "$package"
    ;;
  *.rpm) dnf -y --setopt=install_weak_deps=False install "$package";;
  *) fail 'expected .deb or .rpm';;
esac

# Check dependency resolution before adding the graphical test harness.
ldd /opt/clovercut/clovercut > /tmp/native-libraries.txt
if grep 'not found' /tmp/native-libraries.txt; then fail 'unresolved installed dependency'; fi
test -x /usr/bin/clovercut
test -s /usr/share/applications/io.github.tulcoturo.clovercut.desktop
test -s /usr/share/icons/hicolor/256x256/apps/clovercut.png
[[ $(timeout 60 clovercut --version) == "Clovercut $version" ]] || fail 'wrong installed version'

case "$package" in
  *.deb) apt-get install -y --no-install-recommends xvfb xauth libgl1-mesa-dri mesa-vulkan-drivers fonts-dejavu-core;;
  *.rpm) dnf -y --setopt=install_weak_deps=False install xorg-x11-server-Xvfb xorg-x11-xauth mesa-dri-drivers mesa-vulkan-drivers dejavu-sans-fonts;;
esac
export HOME=/tmp/native-smoke-home
mkdir -p "$HOME/.local/share/io.github.tulcoturo.clovercut"
marker="$HOME/.local/share/io.github.tulcoturo.clovercut/keep-user-data"
printf 'project preferences survive package maintenance\n' > "$marker"
LIBGL_ALWAYS_SOFTWARE=1 timeout --kill-after=10 240 \
  xvfb-run -a -s '-screen 0 1920x1080x24' clovercut --smoke

case "$package" in
  *.deb) apt-get install -y --reinstall "$package";;
  *.rpm) dnf -y --setopt=install_weak_deps=False reinstall "$package";;
esac
[[ $(timeout 60 clovercut --version) == "Clovercut $version" ]] || fail 'reinstallation broke launch'
case "$package" in
  *.deb) apt-get remove -y clovercut;;
  *.rpm) dnf -y remove clovercut;;
esac
[[ ! -e /usr/bin/clovercut && ! -e /opt/clovercut/clovercut ]] || fail 'package removal left executable behind'
grep -Fx 'project preferences survive package maintenance' "$marker"
echo "Native package install, startup, reinstall and removal passed: $package"
