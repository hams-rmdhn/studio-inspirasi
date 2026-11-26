# Upstream Clovercut feature gap

Snapshot: 26 November 2026.

- This tree: Studio Inspirasi 0.1.11, last synced at upstream `6dbf74e8`
  (16 commits after upstream v0.1.9).
- Upstream: `fd6f1743`, released as **v0.2.7** (17 November 2026) —
  292 commits ahead. Releases since our sync point: v0.1.10, v0.1.11,
  v0.2.0–v0.2.4, v0.2.6 and v0.2.7 (the 0.2.5 draft folded into 0.2.6).

Everything below is in upstream and **not** in this tree, grouped by
adoption effort. Per-feature candidates are marked so we can pick
individually — upstream merges need not be taken whole.

## 1. Entrance / exit animations — the headline gap — **PORTED 2026-11-26**

> Full upstream replacement landed (surgical cherry-pick, not a merge):
> `concat-core/src/motion.rs`, `ClipMotion` on `Clip`, export/resolve
> plumbing, `AnimatePanel` + `motion-picker.slint`, `motion_tiles.rs`,
> `ClipField.motion-*`, and `motion.*` keys in all 25 locales. The two
> legacy panels (`video-motion-panel.slint`, `caption-motion-panel.slint`)
> were removed; `CaptionMotion` stays in the model for project-file compat.
> See `logs/2026-11-26-clipmotion-port.md` for the touch-point list.

| | This tree | Upstream 0.2.6+ |

| | This tree | Upstream 0.2.6+ |
|---|---|---|
| Model | `CaptionMotion` — numeric presets 0–3 | `ClipMotion` — named moves |
| Entrance choices | none, fade, slide, pop (4) | **14**: fade, slide-left/right/up/down, zoom-in/out, pop, drop, rise, spin, flip, swing, squash |
| Exit choices | same 4 | same 14 |
| Loop choices | — none — | **9**: pulse, heartbeat, float, wiggle, sway, jitter, spin, flicker, breathe |
| Timing | one duration, 0.05–5 s | per-phase seconds 0.05–10 s, loop `amount` 0–2 |
| Applies to | captions + visual clips | video, pictures, titles, captions, shapes |
| Inspector | separate caption/video motion panels | one unified **Animate** inspector; the two smaller menus removed |

Key upstream pieces (`commit 7877d294`):

- `src/crates/concat-core/src/motion.rs` — new file (~583 lines). Pure
  functions of clip time: `Move::pose(s)` maps −1 (arriving) → 0 (rest) →
  +1 (gone), so entrance and exit are the same motion mirrored. No state,
  no engine dependencies — the most portable part of the whole feature.
- `ClipMotion`/`ClipMove`/`ClipLoop` in `concat-project/src/model.rs`
  (~lines 1516–1613 upstream), `Clip::motion` field (~line 2959).
  Serializes as `"in"`, `"out"`, `"loop"` — additive fields, so old
  projects load cleanly and unknown names are kept-but-ignored.
- `ClipMotion::engine()` converts names to `concat_core::motion` enums.
- Animate inspector UI + commands; upstream keeps numeric
  `CaptionMotion` for caption collections alongside the new system.

Adoption note: this is cleanly additive. The `u8` `CaptionMotion` model
can stay for captions while `ClipMotion` lands for clips, or we can take
the full upstream replacement. Names persist as strings, so a partially
ported build degrades gracefully (unknown name = ignored, not refused).

## 2. New effect packages — 27 (no new filters or transitions)

Package counts, ours vs upstream: audio 25/25, filter 57/57,
transition 35/35, effect **23/50**. No packages were deleted upstream;
`swirl`, `whip-pan`, `zoom-transition` and `zoom-blur-transition` WGSL
were updated.

### 2a. Trivially portable — pure WGSL packages (13)

Copy the `packages/<id>/` folder (manifest + shader + fixtures) and the
matching `cards/<id>.jpg` preview. No engine or UI work.

| Category | Packages |
|---|---|
| Shake | `concat.shake`, `concat.beat-shake`, `concat.impact`, `concat.prism-shake` |
| Distort | `concat.digital-glitch`, `concat.camera-shake` |
| Stylize | `concat.kaleidoscope`, `concat.neon-edges` |
| Blur | `concat.tilt-shift` |
| Retro | `concat.vhs-tape`, `concat.old-film`, `concat.scanlines` |
| Light | `concat.light-leak` |

Caveat: the four Shake effects ride on upstream's `clip_time` relative
timing for layer clips (`638f8dee`); check the shader contract before
assuming drop-in.

### 2b. Cutout-adjacent (2)

- `concat.remove-black` — blends away black backgrounds (with glow
  composition, `85344615`).
- `concat.chroma-key-advanced` — automatic green/blue detection,
  eyedropper, matte view (`ce46db39`). The package needs the inspector
  eyedropper/matte UI and engine plumbing, not just the folder.

### 2c. Person-mask dependent (11) — heaviest

Face (`big-head`, `face-alien`, `face-dog`, `face-funhouse`,
`face-laser-eyes`, `face-sunglasses`) and Subject (`subject-neon`,
`subject-electric`, `subject-clone-trail`, `subject-cyber-aura`,
`subject-disintegration`, `subject-edge-runner`) effects compute against
cached **person/face masks** (`165ccf44`, `8dde2da1`, `131a7d3a`,
`843fbd1e`). They are WGSL packages only on the surface; underneath they
need `concat-vision`'s person-mask inference and the render path feeding
the mask into the effect chain. Take these only with that pipeline.

## 3. Editing features upstream added

| Feature | Commit | Notes |
|---|---|---|
| Animate inspector (14+9 motions) | `7877d294` | see §1 |
| **Multi-mask stack** | `5ab9a913` | `mask: Option<ClipMask>` → `masks: Vec<Mask>`, per-mask keyframes and modes, GPU path |
| **Editable shapes++** | `ab49019f` | width/height, corner radius, polygon sides, star points/inner radius, gradients, stroke align/dash, line heads, trim, shadow. Ours has only kind/size/fill/stroke |
| **Transitions as movable clips** | `2aeb7450` | place/trim/duplicate transitions like clips; per-cut transitions kept. Saves as **document format 2 — older builds refuse to open it** |
| **Full-screen + held preview** | `ab49019f` | monitor button / F11, Esc to leave; Shift holds a hover preview frame |
| **CapCut draft import** | `9b86a56c`, `94742601` | native `draft_content.json` decoder; 0.2.7 adds AES-256-GCM decryption for modern CapCut Desktop drafts |
| **Voice isolation / audio stems** | `5e79d091` | speech-vs-noise or vocal-vs-accompaniment split with independent levels; plus calibrated gain fader, stem mutes, waveform fade handles and optional quadratic fades |
| **Export selected time range** | `8d3ab395`, `9d9651ef` | export whole timeline or selection/In-Out, live duration+size estimate |
| **3-point editing** | `1ff83f5f` | monitor Insert and Overwrite placement |
| **Slip clip** | `3e6a147f` | `Command::SlipClip` with detached-audio sync awareness |
| **Multi-clip detach/reattach audio** | `9d9651ef` | one atomic undo step across a selection |
| **Portable project bundler** | `8e9553a5` | package a project with its media |
| **Caption workflows** | `8e9553a5`, `1ade4952`, `44a44b25` | subtitle timing shift, apply style to caption collection, `ProjectTemplate` slots |
| **Aspect ratio labels + timeline stats** | `b5cdf757` | summary readout |
| **Animated effect previews** | `4e9a01ab` | hover-animated thumbnails + bundled card images (`cards/`, 27 new) |
| **concat-log crate** | `843fbd1e` | structured logging of edits, export stages, GPU diagnostics |
| **Face/text perf** | `698e91ce`, `9ffef9d1` | titles paint on background workers, emoji/layered colour font caching, full-range white fix, captions editor padding/wrap fix |
| **Interactive preview isolation** | `2e7ceaf6` | keeps interactive frames off the background media queue |
| **Missing-media relink** | `6fdaa60f`, `26944224` | locate renamed files, sibling relinking, cancellable search, removal with undo |
| **Speech work** | `b267365f`, `97a9dc3f`, `748c3079` | speech-reel transcription with source timing, remembered language, VAD resilience |
| **GPU recovery** | 0.2.5 notes | bounded retries then CPU-preview fallback with notice |
| **Inspector batch editing** | `cd964043` | edit compatible selected clips together, peer-aware undo |
| **Timeline/UI prefs** | `8044a072`, `4305da9b` | workspace layout persistence, named playhead colours |

## 4. Content and metadata additions

- **Text presets**: +21 (`concat/text-presets/`). 8 curated
  `clovercut.*` (Cinema, Classic, Chapter, Editorial, Quote,
  Breaking News, Lower Third, Neon) + 13 script presets (Arabic,
  Bengali, Chinese ×2, Greek, Hindi, Korean, Persian, Russian, Thai,
  Ukrainian, Urdu, Vietnamese). We have 32; upstream has 53.
- **Cards**: +27 preview images matching the new effects (142 vs our 115).
- **Locale**: `az.json` added — upstream ships 26 locales, we ship 25.

## 5. Fixes worth taking regardless

- **Preserve generated media on cache clear** (0.2.0) — in 0.1.9,
  *Clear project cache* could delete generated project media. Verify
  whether our tree carries this bug; if so, fix it independently of any
  larger sync.
- Obsolete-result rejection for pickers/captions/speech/previews (0.2.0).
- Running exports survive the export panel closing/reopening (0.2.2).
- Clips touching between frames meet on the frame grid; consolidation
  keeps fractional frames; stills held between frames (0.2.5).
- FFmpeg decimal-comma locale guard; export-resolution title
  rasterization; f64 multi-clip drag precision (0.2.7).
- Full colour range for painted shapes/titles; captions editor padding
  and word wrap (0.2.7, issues #61/#63).

## 6. What upstream took that we already built

Convergent features — do not re-add, but expect merge overlaps:

- Grid/list dashboard toggle and pagination (their 24/page; ours 18/page
  in `panes/start.rs`), >40 recents.
- Project rename (theirs is a top-bar title click; ours is a row action
  + dialog) and template library management (theirs is more complete:
  update/delete bundle, independent project copies).
- Scrolling timeline tabs, optional split button.
- **macOS 12 targeting**: upstream 0.2.0 now builds FFmpeg and codec
  deps for Monterey and fixed `VTPixelRotationSessionCreate` — the gap
  this fork exists for is closing, but upstream says actual Monterey
  launch "remains unconfirmed" (no macOS 12 machine). Our shim-verified
  build remains the safer Monterey artefact for now.

## 7. Compatibility watch-list

- **Document format 2**: any tree that saves transitions-as-clips writes
  a format older builds refuse. If we adopt features piecemeal, keep
  upstream's format gate so we never emit a document we cannot read.
- Face/subject effects silently degrade without the person-mask
  pipeline — decide mask support before shipping those packages.
- Sync mechanics: all new packages/cards/presets live in dedicated
  folders, so `sync-upstream.sh` merges them cleanly; the motion model
  fields are additive. The risky hunks are `Clip::motion` vs our
  `Clip::visual_motion` and the replaced inspector panels.
