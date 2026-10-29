# Building Studio Inspirasi on macOS Monterey 12.x (Intel)

Studio Inspirasi is a fork of [Clovercut](https://github.com/tulcoturo/clovercut)
(which itself builds on [Concat](https://github.com/jub0t/Concat)) kept
working on **macOS Monterey 12.x, x86_64**, with the full AI feature set
(cutout, smart brushes, enhance, Whisper captions, Chatterbox TTS) enabled.

It is developed on an Intel Core i7-5557U (Broadwell) and compiled with
`AVX2`, `FMA`, `F16C` and `BMI2` enabled, Metal for the GPU and
VideoToolbox for video decode.

## Why upstream packages do not run on Monterey

The upstream macOS package is built on a much newer SDK:

- its bundled FFmpeg libraries call `VTPixelRotationSession*`, which does
  not exist before macOS 13;
- `libonnxruntime.dylib` and `libplacebo` call the floating-point
  `std::__1::to_chars` symbols that Apple only added to
  `/usr/lib/libc++.1.dylib` in macOS 13.3, and declare `minos 13.4`;
- sherpa-onnx's static library calls `cblas_sgemm$NEWLAPACK$ILP64`,
  a symbol `Accelerate.framework` only gained in macOS 13.3.

This tree carries a compatibility shim —
`scripts/macos/libc++_monterey_shim.cpp` — that provides all three: the
`to_chars` overloads, a bridge from the `NEWLAPACK$ILP64` entry point to
macOS 12's `cblas_sgemm`, and inert fallbacks for the VideoToolbox
rotation API. It is linked into the executable as a static archive and
into the bundle as `libc++_monterey_shim.dylib`, a re-exporting shim the
patched dylibs are pointed at instead of the system paths.

## Build

Requirements: the Rust toolchain in `src/rust-toolchain.toml`, Xcode
Command Line Tools, CMake, Node, and the vendored native dependencies the
CI also uses (`vendor/sherpa`, `vendor/ffmpeg-dev`,
`vendor/onnxruntime-osx-x86_64-*` — see `scripts/ci/fetch.sh` and
`scripts/ci/deps.lock`).

```sh
scripts/macos/build-macos-local.sh
```

The script applies the brand overlay, compiles with
`MACOSX_DEPLOYMENT_TARGET=12.0`, assembles `Studio Inspirasi.app`,
patches every bundled dylib for Monterey, verifies the result with
`scripts/ci/check-min-os.sh --enforce`, ad-hoc signs the bundle, builds
`Studio-Inspirasi-<version>-macos-x86_64.dmg`, and finishes with
`scripts/ci/smoke-macos.sh` (signature, zero external library loads,
`--version`, `--smoke` through the first window frame).

Install with:

```sh
ditto "Studio Inspirasi.app" "/Applications/Studio Inspirasi.app"
xattr -cr "/Applications/Studio Inspirasi.app"
codesign --force --deep -s - "/Applications/Studio Inspirasi.app"
```

The build is ad-hoc signed: the first launch needs *right-click → Open*
(or approval in System Settings → Privacy & Security).

## Following upstream Clovercut

Two remotes:

- `origin` — `hams-rmdhn/studio-inspirasi` (this fork)
- `upstream` — `tulcoturo/clovercut` (what we track)

```sh
git remote add upstream https://github.com/tulcoturo/clovercut.git
scripts/macos/sync-upstream.sh
```

The sync script fetches upstream, merges `upstream/main`, re-applies the
brand overlay and rebuilds. The design keeps that almost always clean:

- everything user-visible that says *Studio Inspirasi* is produced by
  `scripts/branding/apply-brand.py` — an idempotent overlay over the
  upstream strings, not a divergent edit;
- everything Monterey-specific lives in files upstream does not have
  (`scripts/macos/`, `scripts/branding/`, `branding/`, this document);
- functional identifiers upstream relies on — the `concat` crate names,
  the `clovercut` cargo binary, the `"clovercut"` shortcut profile id —
  are left untouched.

On conflicts: take upstream's side of any conflicting hunk (the overlay
restores our strings), `git add -A && git merge --continue`, then
`scripts/macos/sync-upstream.sh --no-build` and rebuild.

### What the brand overlay owns

`scripts/branding/apply-brand.py` derives all brand artefacts from
`branding/logo-source.png` and then rewrites, every run:

- the app icon, wordmark and SVG wrappers in `assets/` and
  `site/site_assets/`;
- the default accent colour (`#5AC4CD`) in `concat/src/lib.rs`;
- the display name in the window title, launch screen, About box, CLI
  `--version`, English locale values and user-facing error strings;
- the bundle identifier (`io.github.hams-rmdhn.studio-inspirasi`), which
  also names `~/Library/Application Support/…` — data under the previous
  `io.github.tulcoturo.clovercut` folder is migrated once by
  `migrate_legacy()` in `concat-host/src/dirs.rs`, so downloaded AI
  models and settings carry over;
- the updater's release feed (`concat-host/src/updates.rs`) and the
  launch screen's repository link, both now pointing at this repository;
- the Linux packaging assets and the macOS bundle metadata in
  `.github/workflows/build-app.yml` and
  `scripts/macos/build-macos-local.sh`.

Attribution is kept as required by AGPL-3.0 and `TRADEMARK.md`:
`LICENSE`, `THIRD_PARTY_NOTICES.md`, and the
`SPDX-FileCopyrightText` headers are never rewritten.

## Signing and releases

Local builds are ad-hoc signed. To publish a DMG others can install
without warnings, configure an Apple Developer ID plus notarisation in
the GitHub secrets the `Sign and notarise` step of
`.github/workflows/build-app.yml` already consumes
(`APPLE_CERTIFICATE_P12`, `APPLE_SIGNING_IDENTITY`, `APPLE_ID`,
`APPLE_TEAM_ID`, `APPLE_APP_PASSWORD`), or ship ad-hoc builds with the
install note above.

A release the in-app updater understands is a GitHub release carrying:

- `Studio-Inspirasi-<version>-macos-x86_64.dmg`
- `manifest.json` — `{"binaries": {"macos": {"x86_64": {"dmg": {"file",
  "url", "bytes", "sha256"}}}}}`
- `SHA256SUMS` for the DMG

The CI workflow's macOS leg still runs on newer runners and is kept
aligned for arm64-style packages; the Monterey-verified DMG is produced
by `build-macos-local.sh` on a macOS 12 machine and uploaded manually.
