# AGENTS.md — Studio Inspirasi (Clovercut fork)

## Build / check / test (macOS 12, Intel)

The checkout path has a space, so work through the symlink the build script
makes: `ln -sfn "$PWD" /tmp/clovercut-ws`. Native deps live in `vendor/`.

```sh
export FFMPEG_DIR=/tmp/clovercut-ws/vendor/ffmpeg-dev
export SHERPA_ONNX_LIB_DIR=/tmp/clovercut-ws/vendor/sherpa/sherpa-onnx-v1.13.7-osx-x64-static-lib/lib
export ORT_MAC_DYLIB=/tmp/clovercut-ws/vendor/onnxruntime-osx-x86_64-1.23.2/lib/libonnxruntime.1.23.2.dylib
export LIBCLANG_PATH=/Library/Developer/CommandLineTools/usr/lib
export MACOSX_DEPLOYMENT_TARGET=12.0
# test binaries link @executable_path/../Frameworks/libav*.dylib:
export DYLD_FALLBACK_LIBRARY_PATH=/tmp/clovercut-ws/vendor/ffmpeg-dev/lib
cd /tmp/clovercut-ws/src
cargo check -p concat                     # full app incl. Slint (~1h cold)
cargo test -p concat-core -p concat-project -p concat-export --no-fail-fast
```

- Release DMG: `scripts/macos/build-macos-local.sh`.
- Known pre-existing failure: `concat-export`
  `an_alpha_export_writes_its_own_container_with_its_sound` (VP9 alpha decode
  in vendored FFmpeg) — fails on a clean HEAD too.
- Don't share `target/` with a second worktree: it confuses fingerprints;
  `touch` the changed `.rs` files if that happens.

## Conventions
- Port upstream features surgically; keep fork-only code in files upstream
  does not own. Gap list: `docs/UPSTREAM_GAP.md`.
- Write a summary to `logs/` after every feature or fix.
