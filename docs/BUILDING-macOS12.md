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

### Fork feature touch points

Beyond branding and Monterey compatibility, this fork carries these
interface additions. Each one uses existing `concat-host` APIs, or a
small addition to them, with minimal wiring in upstream files:

1. **Launch-screen Grid / List view toggle**
   - Persisted in `prefs.json` (`dashboardView: 0 | 1`).
   - Upstream touch points: `src/crates/concat/ui/icons.slint`
     (`Glyph.layout-grid`), `src/crates/concat/ui/start.slint`
     (`ViewToggle`, `ProjectsList`, `ProjectRow` actions),
     `src/crates/concat/src/panes/start.rs` (`StartMsg::ViewMode`,
     `VIEW_GRID`/`VIEW_LIST`), `src/crates/concat/src/prefs.rs`
     (`dashboard_view`).
2. **Launch-screen pagination (18 projects per page)**
   - Upstream touch points: `src/crates/concat/src/panes/start.rs`
     (`PAGE_SIZE`, `StartPane.page`, `StartMsg::Page`),
     `src/crates/concat/src/studio.rs` (filtered recents are sliced at
     publish), `src/crates/concat/ui/start.slint` (`PageSlot`,
     `PaginationBar`), `src/crates/concat/ui/app.slint`
     (`start-page-changed` wiring).
3. **Saved-templates gallery and slot-fill sheet**
   - Upstream touch points: `src/crates/concat/src/studio.rs`
     (`templates_library`, `template_fill`, `use_template`,
     `delete_template`, `template_fill_*`), `src/crates/concat/ui/
     workspace/media-pane.slint` (`TemplateGallery`, fill sheet),
     `src/crates/concat/ui/editor.slint` and `workspace/seat.slint`
     (`Editor.library-templates`, `template-*` callbacks).
4. **Rename and Move-to-Trash for recent projects (0.1.11)**
   - Rename writes the manifest `name` and the recents entry only; the
     folder keeps its name. Remove asks through `ConfirmDialog` and, on
     macOS, moves the folder to the Trash via `NSFileManager`.
   - Upstream touch points: `src/crates/concat-host/src/projects.rs`
     (`rename` + test), `src/crates/concat/src/panes/start.rs`
     (`StartMsg::RenameRecent/RenameEdited/RenameConfirm/RenameCancel`,
     `ForgetRecent` now asks), `src/crates/concat/src/studio.rs`
     (`Confirm::TrashProject`, `trash_project`, `is_open_project`),
     `src/crates/concat/src/platform.rs` (`CAN_TRASH`, `trash`),
     `src/crates/concat/Cargo.toml` (macOS `objc2-foundation` features),
     `src/crates/concat/ui/dialogs/rename.slint` (new),
     `src/crates/concat/ui/primitives/modal.slint` (`Field.accepted`,
     `Field.focus-all()`), `src/crates/concat/ui/start.slint`
     (`RowAction`, `ProjectRow`, `PosterCard` actions, rename wiring),
     `src/crates/concat/ui/icons.slint` (`Glyph.pencil`).
5. **Title bar: full-screen inset and menu-bar behaviour (0.1.11)**
   - `platform::is_fullscreen` reads winit's own state (it tracks the
     green button) on every resize; the strip drops its 80px traffic-light
     inset in full screen. No `objc2` window poking.
   - The File/Edit/View sheet is a `ContextMenu { held: true }`: drawn in
     the window's tree (popups swallow every event outside them), closed
     by a page-covering press in `app.slint`, by its label, the strip's
     ground or Escape; hovering another label with a menu open switches.
   - Upstream touch points: `src/crates/concat/src/platform.rs`,
     `src/crates/concat/src/lib.rs` (`on_window_resized`,
     `on_menu_dismissed`), `src/crates/concat/ui/title-bar.slint`
     (`fullscreen`, `menu-closed`, `MenuLabel.hovered`),
     `src/crates/concat/ui/primitives/context-menu.slint` (`MenuSheet`,
     `held`, `dismiss()`), `src/crates/concat/ui/app.slint`.
   - `assets/applogo-mark.png` is `applogo.png` cropped to its ink
     (`sips --cropToHeightWidth 802 412 --cropOffset 111 306`); regenerate
     it if the app icon changes. Used by the title bar and the launch
     screen's greeting so they align with the page.

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
