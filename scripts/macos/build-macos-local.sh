#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Build Studio Inspirasi.app and DMG locally on macOS Monterey 12.x (x86_64)
# with full Broadwell CPU optimizations (AVX2, FMA, F16C, BMI2), Metal GPU,
# and the macOS 12 libc++ / Accelerate / VideoToolbox compatibility shim.
#
# The brand overlay is re-applied before compiling, so a build right after
# `git merge upstream/main` still carries the Studio Inspirasi identity.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# Create a space-free symlink in /tmp so RUSTFLAGS and CMake paths work even when
# the checkout lives under "/Users/.../Local Sites/...".
WS_LINK="/tmp/clovercut-ws"
ln -sfn "$ROOT" "$WS_LINK"

export PATH="$HOME/.cargo/bin:$WS_LINK/vendor/cmake/CMake.app/Contents/bin:$WS_LINK/vendor/node/bin:/usr/local/bin:$PATH"
export MACOSX_DEPLOYMENT_TARGET="12.0"
export LIBCLANG_PATH="/Library/Developer/CommandLineTools/usr/lib"

VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' src/Cargo.toml | head -1)
TARGET="x86_64-apple-darwin"

echo "==> [1/6] Building macOS 12 compatibility shim (libc++ / Accelerate / VideoToolbox)"
SHIM_DIR="$WS_LINK/target/monterey-shim"
mkdir -p "$SHIM_DIR"

clang++ -std=c++20 -O2 -mmacosx-version-min=12.0 -fPIC \
  -c "$WS_LINK/scripts/macos/libc++_monterey_shim.cpp" \
  -o "$SHIM_DIR/libc++_monterey_shim.o"

ar rcs "$SHIM_DIR/libmonterey_cxx_compat.a" "$SHIM_DIR/libc++_monterey_shim.o"

clang++ -std=c++20 -O2 -mmacosx-version-min=12.0 -dynamiclib \
  "$SHIM_DIR/libc++_monterey_shim.o" \
  -Wl,-reexport_library,/usr/lib/libc++.1.dylib \
  -Wl,-reexport_framework,Accelerate \
  -Wl,-reexport_framework,VideoToolbox \
  -framework CoreFoundation -framework Accelerate -framework VideoToolbox \
  -install_name "@loader_path/libc++_monterey_shim.dylib" \
  -o "$SHIM_DIR/libc++_monterey_shim.dylib"

echo "==> [2/6] Preparing native dependencies in vendor/"
SHERPA_VERSION=$(grep -A1 'name = "sherpa-onnx-sys"' src/Cargo.lock | sed -n 's/^version = "\(.*\)"/\1/p')
SHERPA_STEM="sherpa-onnx-v${SHERPA_VERSION}-osx-x64-static-lib"
export SHERPA_ONNX_LIB_DIR="$WS_LINK/vendor/sherpa/$SHERPA_STEM/lib"
export FFMPEG_DIR="$WS_LINK/vendor/ffmpeg-dev"
export ORT_MAC_DYLIB="$WS_LINK/vendor/onnxruntime-osx-x86_64-1.23.2/lib/libonnxruntime.1.23.2.dylib"

test -d "$SHERPA_ONNX_LIB_DIR" || { echo "Missing SHERPA_ONNX_LIB_DIR: $SHERPA_ONNX_LIB_DIR" >&2; exit 1; }
test -d "$FFMPEG_DIR/include" || { echo "Missing FFMPEG_DIR/include: $FFMPEG_DIR/include" >&2; exit 1; }
test -f "$ORT_MAC_DYLIB" || { echo "Missing ORT_MAC_DYLIB: $ORT_MAC_DYLIB" >&2; exit 1; }

# Enable AVX2, FMA, F16C, BMI2 for Intel Core i7-5557U (Broadwell)
export GGML_NATIVE="OFF"
export GGML_AVX2="ON"
export GGML_FMA="ON"
export GGML_F16C="ON"
export GGML_BMI2="ON"
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}"

CLANG_RT=$(xcrun clang --print-file-name=libclang_rt.osx.a)
export RUSTFLAGS="-C link-arg=${CLANG_RT} -L native=${SHIM_DIR} -l static=monterey_cxx_compat"

echo "==> [3/6] Applying the Studio Inspirasi brand overlay, then compiling ${VERSION} (${TARGET})"
if command -v python3 >/dev/null 2>&1; then
  python3 "$WS_LINK/scripts/branding/apply-brand.py" >"$ROOT/target/apply-brand.log" 2>&1 || {
    cat "$ROOT/target/apply-brand.log" >&2
    exit 1
  }
else
  echo "warning: python3 not found - skipping apply-brand.py" >&2
fi
(
  cd "$WS_LINK/src"
  cargo build --locked --profile app -p concat --bin clovercut --target "$TARGET" \
    --config 'profile.app.lto=false' \
    --config 'profile.app.package.concat.opt-level=0' \
    --config 'profile.app.package.concat.codegen-units=16'
)

echo "==> [4/6] Assembling Studio Inspirasi.app bundle"
APP="$ROOT/Studio Inspirasi.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" "$APP/Contents/Frameworks"

cp LICENSE THIRD_PARTY_NOTICES.md "$APP/Contents/Resources/"
cp "src/target/$TARGET/app/clovercut" "$APP/Contents/MacOS/studio-inspirasi"

ICONSET="$ROOT/target/Studio-Inspirasi.iconset"
rm -rf "$ICONSET"
mkdir -p "$ICONSET"
ICONS="$ROOT/assets/icons"
cp "$ICONS/clovercut_16.png"  "$ICONSET/icon_16x16.png"
cp "$ICONS/clovercut_32.png"  "$ICONSET/icon_16x16@2x.png"
cp "$ICONS/clovercut_32.png"  "$ICONSET/icon_32x32.png"
cp "$ICONS/clovercut_64.png"  "$ICONSET/icon_32x32@2x.png"
cp "$ICONS/clovercut_128.png" "$ICONSET/icon_128x128.png"
cp "$ICONS/clovercut_256.png" "$ICONSET/icon_128x128@2x.png"
cp "$ICONS/clovercut_256.png" "$ICONSET/icon_256x256.png"
cp "$ICONS/clovercut_512.png" "$ICONSET/icon_256x256@2x.png"
cp "$ICONS/clovercut_512.png" "$ICONSET/icon_512x512.png"
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/Studio Inspirasi.icns"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Studio Inspirasi</string>
  <key>CFBundleDisplayName</key><string>Studio Inspirasi</string>
  <key>CFBundleIdentifier</key><string>io.github.hams-rmdhn.studio-inspirasi</string>
  <key>CFBundleVersion</key><string>${VERSION}</string>
  <key>CFBundleShortVersionString</key><string>${VERSION}</string>
  <key>CFBundleExecutable</key><string>studio-inspirasi</string>
  <key>CFBundleIconFile</key><string>Studio Inspirasi</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>${MACOSX_DEPLOYMENT_TARGET}</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSSupportsAutomaticGraphicsSwitching</key><true/>
  <key>LSApplicationCategoryType</key><string>public.app-category.video</string>
  <key>NSHumanReadableCopyright</key><string>AGPL-3.0-or-later. Based on Clovercut and Concat. See THIRD_PARTY_NOTICES.md.</string>
  <key>NSMicrophoneUsageDescription</key><string>Studio Inspirasi records voiceovers from your microphone.</string>
</dict>
</plist>
PLIST

# Copy runtime dylibs and Monterey shim into Contents/Frameworks
for dylib in "$FFMPEG_DIR/lib/"*.dylib; do
  [ -L "$dylib" ] && continue
  cp -f "$dylib" "$APP/Contents/Frameworks/"
done
cp -f "$ORT_MAC_DYLIB" "$APP/Contents/Frameworks/libonnxruntime.dylib"
cp -f "$SHIM_DIR/libc++_monterey_shim.dylib" "$APP/Contents/Frameworks/libc++_monterey_shim.dylib"

# Apply Monterey compatibility patches to Frameworks dylibs
install_name_tool -change /usr/lib/libc++.1.dylib "@loader_path/libc++_monterey_shim.dylib" \
  "$APP/Contents/Frameworks/libonnxruntime.dylib"
if [ -f "$APP/Contents/Frameworks/libplacebo.360.dylib" ]; then
  install_name_tool -change /usr/lib/libc++.1.dylib "@loader_path/libc++_monterey_shim.dylib" \
    "$APP/Contents/Frameworks/libplacebo.360.dylib"
fi
for avf in "$APP/Contents/Frameworks"/libavfilter*.dylib; do
  if [ -f "$avf" ]; then
    install_name_tool -change /System/Library/Frameworks/VideoToolbox.framework/Versions/A/VideoToolbox \
      "@loader_path/libc++_monterey_shim.dylib" "$avf"
  fi
done
install_name_tool -change /System/Library/Frameworks/Accelerate.framework/Versions/A/Accelerate \
  "@executable_path/../Frameworks/libc++_monterey_shim.dylib" "$APP/Contents/MacOS/studio-inspirasi"

for f in "$APP/Contents/Frameworks/"*.dylib; do
  chmod u+w "$f"
  vtool -set-build-version macos 12.0 13.1 -replace -output "$f" "$f" 2>/dev/null
done
vtool -set-build-version macos 12.0 13.1 -replace \
  -output "$APP/Contents/MacOS/studio-inspirasi" "$APP/Contents/MacOS/studio-inspirasi" 2>/dev/null

echo "==> [5/6] Verifying macOS 12.0 minimum OS floor and ad-hoc signing"
"$ROOT/scripts/ci/check-min-os.sh" "$APP" "$MACOSX_DEPLOYMENT_TARGET" --enforce
codesign --force --deep -s - "$APP"

DMG="$ROOT/Studio-Inspirasi-${VERSION}-macos-x86_64.dmg"
rm -f "$DMG"
for attempt in 1 2 3 4; do
  if hdiutil create -volname "Studio Inspirasi" -srcfolder "$APP" -ov -format UDZO "$DMG" > "$ROOT/target/dmg-create.log" 2>&1; then
    break
  else
    status=$?
    if ! grep -qi 'Resource busy' "$ROOT/target/dmg-create.log" || [ "$attempt" -eq 4 ]; then
      cat "$ROOT/target/dmg-create.log" >&2
      exit "$status"
    fi
    sleep 5
  fi
done
test -s "$DMG"

echo "==> [6/6] Running smoke-macos.sh verification"
"$ROOT/scripts/ci/smoke-macos.sh" "$APP"
echo "==> Build complete: $APP and $DMG"
