# 2026-11-26 — Upstream gap scan (investigation only, no code changes)

## What was done

- Fetched `upstream` (tulcoturo/clovercut): `main` advanced to `fd6f1743`,
  tags v0.2.0–v0.2.7 received. Local merge-base: `6dbf74e8` (post-v0.1.9);
  upstream is 292 commits ahead.
- Diffed `src/crates/concat-effects/packages/` between merge-base and
  upstream: 27 new `kind = "effect"` packages, 0 new filters/transitions/
  audio, 0 deletions; `swirl`, `whip-pan`, `zoom-transition`,
  `zoom-blur-transition` shaders updated.
- Compared entrance/exit animation systems:
  - Ours: `CaptionMotion` numeric presets 0–3 (none/fade/slide/pop).
  - Upstream: new `ClipMotion` (`concat_core::motion`): 14 named
    entrance/exit moves + 9 loops, applies to clips/pictures/titles/
    captions/shapes, unified Animate inspector (`7877d294`).
- Inventoried other upstream features from commit log + CHANGELOG +
  release notes 0.2.0–0.2.7: multi-mask stack, editable shapes,
  transitions-as-clips (document format 2), CapCut draft import
  (+AES-256-GCM in 0.2.7), voice isolation/audio stems, time-range
  export, 3-point editing, SlipClip, multi-clip detach audio, portable
  bundler, caption batch style/shift, 21 new text presets, 27 new card
  images, `az` locale (26 total), `concat-log` crate.
- Verified locally absent: ClipMotion, SlipClip, capcut importer, stems,
  multi-mask (`mask: Option<ClipMask>` single), time-range export,
  fade handles, workspace-layout pref, playhead colours, concat-log.
- Noted overlaps already in our fork: dashboard grid/list, pagination,
  rename/trash, templates library, scrolling tabs equivalent work; and
  upstream 0.2.0 now targets macOS 12 itself (unconfirmed on real HW).

## Output

- New doc: `docs/UPSTREAM_GAP.md` — grouped per-feature candidates with
  adoption-effort notes and a compatibility watch-list, for deciding
  what Studio Inspirasi takes next.

## Follow-ups suggested

- Decide adoption order; pure-WGSL effect packages (13) are the cheapest
  win; ClipMotion port is the headline feature; face/subject effects
  need the person-mask pipeline first.
- Verify whether the 0.2.0 "preserve generated media on cache clear"
  bug exists in this tree and patch independently if so.
