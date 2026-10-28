# Test suites and qualification

Run Rust commands from `src/` with the native dependencies configured as described
in [building](RELEASING.md). Run Python/Node commands from the repository root.
Use full commit SHAs for workflow `ref` inputs; checkout does not resolve an
abbreviated SHA as a commit.

## Ordinary validation

| Suite | Command | Requirements |
|---|---|---|
| Formatting | `cargo fmt --all --check` | Pinned toolchain |
| Workspace lint | `cargo clippy --workspace --all-targets -- -D warnings` | Native libraries; generated UI compilation |
| Workspace tests | `cargo nextest run --locked --workspace --profile ci --build-jobs 1` | Native libraries, FFmpeg/ffprobe; CI requires a usable GPU adapter |
| Locale rules | `python3 -m unittest discover -s scripts -p test_locales.py` | Python |
| Translations | `python3 scripts/locales.py --check --strict` | Python |
| Models | `python3 scripts/models.py --check` | Python; no model inference |
| Connector | `node src/crates/concat-host/audio-service/test/bridge.test.mjs` | Node 22+; no browser, account or network |
| Linux packages | `python3 -m unittest discover -s scripts -p test_linux_packaging.py -v` | Linux, dpkg-deb, RPM tools, makepkg/pacman; does not install on the host |

The Node suite must report its individual language cases. The Linux suite checks
real package payloads and mocked installer failure paths; it does not qualify
installation on every distribution. Release workflows require checks against
the selected source commit, not a previous successful branch run.

The small pure Enhance planning module can also be checked without the generated
UI or native libraries, from the repository root:

```sh
rustc --edition 2024 --test src/crates/concat/src/enhance_plan.rs -o /tmp/clovercut-enhance-plan-tests
/tmp/clovercut-enhance-plan-tests
```

This is a narrow policy check, not a substitute for compiling the application.

## Ignored tests: complete source inventory at 0.1.9

There are 28 ignored Rust test attributes in this baseline. Ignored tests are
compiled when their platform/features are enabled but are not executed by the
ordinary default test run. Each group below needs an explicit qualification run.

| Group | Cases | Prerequisites and execution policy |
|---|---:|---|
| `concat` phase-3 timeline | 5 | Isolated graphical session and GPU; transport case also needs FFmpeg. Run when editing cut timing, placement or geometry. |
| `concat` phase-4 sync, robustness, preview/export parity | 3 | Isolated Slint/GPU/audio session and FFmpeg. Run for transport, timing, rendering or audio changes and before qualifying a desktop release. |
| `concat` phase-6 performance/memory | 1 | Graphical/GPU/audio session and FFmpeg; labelled hardware baseline. Report samples separately from functional assertions. |
| `concat` source preview | 1 | Graphical session, FFmpeg and audio output. Run when changing library/timeline preview routing. |
| `concat` durability warning and running-work shutdown | 2 | Isolated graphical/audio session; shutdown case also needs FFmpeg/GPU. Run for lifecycle and recovery changes. |
| `concat` cross-project clipboard | 1 | Isolated graphical/audio session. Run when changing copying, ownership or destination track placement. |
| `concat-vision` CoreML Enhance probe | 1 | Downloaded model and supported CoreML environment. Performance probe, not generic CI coverage. |
| `concat-vision` stabilisation timing | 1 | Synthetic frame analysis benchmark; no stable cross-machine timing budget. Run when profiling tracking. |
| `concat-speech` file transcription | 2 | Downloaded speech model and explicit audio input. Run when changing speech/model integration. |
| `concat-render` upscale speed | 1 | Downloaded model and supported adapter; benchmark only. |
| `concat-media` MediaCodec comparison | 1 | Android device and `CONCAT_DEVICE_SAMPLE`; retain outside desktop qualification. |
| `concat-media` audio seek/decode timing | 1 | `CONCAT_AUDIO_PROBE` files; diagnostic measurement, not ordinary pass coverage. |
| `concat-host` split timing | 1 | `CONCAT_SPLIT_PROBE` long recording and optional cut position; diagnostic measurement. |
| `concat-host` real GPU Enhance comparison | 1 | `CLOVERCUT_ENHANCE_MODEL` and actual GPU. Verify parity and record timing. |
| `concat-host` GL catalogue/fixtures/rendering | 3 | One online download/cache case, one fixture-driven adaptation/validation case, one hardware rendering case. See [GL Transitions](GL_TRANSITIONS.md). |
| `concat-host` OpenGameArt | 1 | Internet; searches, downloads and reuses real provider content. |
| `concat-host` YouTube music/effects | 1 | Local Audio API and authenticated dedicated Studio session. |
| `concat-host` combined audio providers | 1 | Network, connected YouTube API and a Freesound key provided through the environment. |

Never run every ignored test indiscriminately. Some intentionally need private
inputs, several open graphical/audio sessions, and others measure performance
rather than assert a product contract.

For example, a specific graphical regression can be selected explicitly:

```sh
cargo test -p concat --lib studio::phase4_playback_robustness_tests::playback_robustness_and_recovery -- --exact --ignored --nocapture --test-threads=1
```

The separate screenshot driver is not an ignored test; it is opt-in development
tooling described in [the build guide](RELEASING.md#optional-graphical-walkthrough).

## Record results honestly

For each qualification, record the source SHA, platform/architecture, GPU/driver,
toolchain, suite/filter, environment prerequisites, result and relevant metrics.
Distinguish passed, failed, ignored and unavailable. No result recorded means
unqualified, not passed. Keep credentials, personal media and browser profiles
out of committed evidence and uploaded logs.

For performance comparisons, separate fixture setup, cold/warm compilation,
execution, decode, rendering and UI publication. Use repeated runs and report
p95/growth trends; do not compare arbitrary hardware as a regression budget.

Keep tests that protect saved data, existing output files, undo, ownership,
locks and preview/export agreement. Consolidation requires a named replacement
assertion and evidence that the same failure is still detected. The
[quality audit](audits/2026-10-28.md) records the current disposition decisions.
