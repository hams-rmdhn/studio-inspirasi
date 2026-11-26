# Port ClipMotion (Animate panel) dari upstream Clovercut

Tanggal: 2026-11-26
Sumber: `upstream/main` (fd6f1743, ~v0.2.7); fitur dirilis upstream di 0.2.6
Gaya: surgical cherry-pick — bukan merge penuh.

## Apa yang di-port

Sistem animasi `ClipMotion` upstream menggantikan panel preset lama
(entrance/exit 0–3: none/fade/slide/pop):

- **14 moves** (In & Out): fade, slide-left/right/up/down, zoom-in/out,
  pop, drop, rise, spin, flip, swing, squash
- **9 loops**: pulse, heartbeat, float, wiggle, sway, jitter, spin,
  flicker, breathe
- Berlaku untuk video, image, title/caption, shape — dikomposisi di atas
  keyframe transform/opacity (bukan menggantikannya).

## File yang diubah

### Engine
- `src/crates/concat-core/src/motion.rs` — **baru**, disalin utuh dari
  upstream (583 baris: `Move`, `Cycle`, `Pose`, `Motion::pose_at`, tests).
- `src/crates/concat-core/src/lib.rs` — `pub mod motion;`
- `src/crates/concat-core/src/timeline.rs` — field `Clip::motion`,
  `pose_at()`, komposisi pose di `transform_at()`/`opacity_at()`.
  (multi-mask upstream *tidak* ikut — kita tetap `mask: Option<ShapeMask>`)

### Project model
- `concat-project/src/model.rs` — `ClipMotion`/`ClipMove`/`ClipLoop`
  (serde `in`/`out`/`loop`), `tidy()` (0.05–10s moves, 0.1–20s laps,
  amount 0–2), `engine()`; `Clip::motion: Option<ClipMotion>`.
- `concat-project/src/commands/mod.rs` — `ClipPatch.motion` (double_option).
- `concat-project/src/commands/properties.rs` — apply patch + tidy.

### Export / preview
- `concat-export/src/lib.rs` — `ExportClip.motion` + `blank()`.
- `concat-export/src/flatten.rs` — `motion: clip.motion.clone()`.
- `concat-export/src/resolve.rs` — `engine_clip.motion = m.engine()`.
- `concat-host/src/titles.rs` — title/caption/shape membawa `clip.motion`
  (tanpa ini Animate tidak jalan di text clips).

### App / studio
- `src/crates/concat/src/motion_tiles.rs` — **baru**, feeder MotionTiles
  (sample pose engine per 1/30 detik untuk kartu preview).
- `src/crates/concat/src/studio.rs` — `motion_place()` helper; arm
  `ClipField::MotionIn..MotionLoopAmount` di `clip_set` (mengisi
  `clip.motion` dan me-reset preset legacy `visual_motion`/
  `caption_motion` — perilaku upstream); field `motion_*` di
  `SelectedClipData`; 7 field motion masuk daftar `caption_style_targets`
  (apply-to-all captions); hapus `visual_motion()`/`caption_motion()` +
  sync `VideoMotion`.
- `src/crates/concat/src/lib.rs` — `mod motion_tiles`, install() call,
  hapus wiring `VideoMotion.on_set` & `CaptionsLibrary.on_motion`.

### UI (Slint)
- `ui/inspector/motion-picker.slint` — **baru** (MotionTiles global +
  MotionPicker/MotionCard; kartu memainkan move asli saat hover/selected).
- `ui/assets/motion-still.jpg` — **baru** (gambar kartu preview).
- `ui/inspector/clip-inspector.slint` — `AnimatePanel` (In/Out/Loop
  SegmentedControl + picker + Param length/lap/amount).
- `ui/workspace/config-pane.slint` — section `"Animation"` → `"Animate"`
  di tab Video (termasuk shape); tab `"CaptionEffects"` dihapus — Animate
  kini section di tab Text; panel-panel lama dihapus.
- `ui/timeline/model.slint` — `ClipField.motion-*` (7 varian) +
  `SelectedClipData.motion-*` (7 field).
- `ui/app.slint` — `VideoMotion` diganti `MotionPose/MotionTile/MotionTiles`.
- **Dihapus**: `ui/inspector/video-motion-panel.slint`,
  `ui/inspector/caption-motion-panel.slint`.
- `CaptionsLibrary.entrance/exit/duration/motion` di captions-panel.slint
  dibiarkan (upstream juga membiarkannya; prop global tak terpakai).

### Locales
- 30 key `motion.*` disalin dari upstream ke seluruh 25 locale
  (terjemahan asli, bukan fallback en — id: "Animasi", ja: "アニメーション").
- Locale `az` upstream tidak ditambah (di luar scope port ini).

## Kompatibilitas

- `visual_motion`/`caption_motion` (preset 0–3) tetap di model & flatten —
  proyek lama tetap terbaca dan ter-render. Saat user memilih move baru,
  preset legacy di-reset ke 0 (perilaku upstream).
- `ClipMotion` additive: proyek tanpa `motion` = tidak ada animasi.

## Verifikasi

- `cargo check -p concat` (env vendor lengkap: FFMPEG_DIR, SHERPA_ONNX_LIB_DIR,
  ORT_MAC_DYLIB, LIBCLANG_PATH, MACOSX_DEPLOYMENT_TARGET=12.0) — **bersih,
  0 error** (Slint codegen ikut lolos → semua .slint valid).
- `cargo test -p concat-core -p concat-project -p concat-export`:
  concat-core 72/72, concat-project 194/194 + integration tests (canvas,
  clipboard, linkage, styled_captions, ...) semua lulus; concat-export
  48/49 — satu gagal: `an_alpha_export_writes_its_own_container_with_its_sound`
  (VP9 alpha: corner alpha 255). **Terbukti pre-existing**: gagal identik di
  worktree baseline HEAD tanpa perubahan ini → masalah decoder VP9-alpha di
  FFmpeg `vendor/ffmpeg-dev`, bukan regresi.
- Test harus dijalankan dengan `DYLD_FALLBACK_LIBRARY_PATH=vendor/ffmpeg-dev/lib`
  (binary test me-link `@executable_path/../Frameworks/libavutil*.dylib`).
- Test `concat` (app crate) belum dijalankan — crate besar (~1 jam di mesin
  ini); verifikasi UI dilakukan lewat build app + uji manual.
- Konflik dengan rencana hide-5-pages (media-pane.slint): nol irisan file.

## Catatan merge upstream berikutnya

- `transition_layers.rs` upstream (transisi-as-klip) juga membaca
  `clip.motion` — saat fitur itu di-port nanti, motion sudah siap.
- `docs/UPSTREAM_GAP.md` — update: ClipMotion/Animate = DONE.

## Build DMG

- `scripts/macos/build-macos-local.sh` → EXIT 0 (semua 6 langkah, termasuk
  check-min-os macOS 12.0 dan smoke test `studio-inspirasi --smoke: ok`
  di macOS 12.7.6 / MacBookPro12,1).
- Output: `Studio-Inspirasi-0.1.11-macos-x86_64.dmg` (~159 MB),
  SHA-256 `b2cfea54204072810e4c4dffa323506d7420086c8f2570302c8bff513bc68219`
  (`SHA256SUMS-monterey.txt` diperbarui).
- `apply-brand.py` tidak mengubah status git.
- Ad-hoc signed, belum notarised → Gatekeeper akan memberi peringatan.
