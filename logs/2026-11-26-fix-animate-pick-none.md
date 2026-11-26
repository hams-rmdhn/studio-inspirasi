# Fix: pilihan Animate (In/Out/Loop) selalu kembali ke None

Tanggal: 2026-11-26
Terkait: `logs/2026-11-26-clipmotion-port.md`

## Gejala
Di build pertama hasil port ClipMotion, kartu entrance/exit/loop mana pun
yang diklik tidak tersimpan; pilihan aktif selalu None.

## Akar masalah
Inspector menulis ke *echo* (salinan klip) lewat `clip_set`, lalu
`clip_commit` mengubah selisih echo vs dokumen menjadi `ClipPatch` di
`clip_commands()` (`src/crates/concat/src/studio.rs`). Fungsi diff itu
membandingkan field satu per satu, dan port awal **tidak menambahkan
`motion`** ke dalamnya — jadi `clip.motion` di echo dibuang saat commit,
dokumen tidak berubah, `SelectedClipData.motion-in` tetap -1 (None).
Ini satu titik sentuh upstream (studio.rs ~1986) yang terlewat saat port.

## Perbaikan
- `clip_commands()`: diff `motion` → `patch.motion`, dan `visual_motion` →
  `patch.visual_motion` (supaya reset preset legacy ke 0 saat move baru
  dipilih ikut tersimpan, dalam satu UpdateClip = satu undo). Sama persis
  dengan upstream.
- Test regresi upstream di-port: `a_motion_picked_in_the_inspector_is_committed`,
  `replacing_legacy_motion_commits_both_formats_in_one_patch`.

## Re-check
- Seluruh pemakaian `.motion` di studio.rs/concat-project/concat-export/
  concat-host kini cocok dengan upstream (kecuali `transition_layers.rs`,
  fitur yang memang belum di-port).
- `caption_style_targets` meneruskan seleksi apa adanya untuk klip
  non-caption → klip video/gambar/shape ikut ter-target.

## Rilis

- Commit `77aadfa0` di `main`, tag pre-release `v0.1.11-animate.1`
  (versi tetap 0.1.11 agar cocok dengan DMG lokal yang sudah dibuat;
  kenaikan ke 0.1.12 dibatalkan untuk menghindari rebuild ~1,5 jam).
- Push tag memicu workflow "Studio Inspirasi release" (#7) → rilis GitHub
  ditandai prerelease. Body rilis diambil dari `docs/releases/0.1.11.md`
  (workflow memakai versi Cargo); `docs/releases/0.1.12.md` berisi catatan
  Animate untuk ditempel manual / dipakai di rilis 0.1.12 nanti.
- DMG Monterey (`Studio-Inspirasi-0.1.11-macos-x86_64.dmg`, SHA-256
  `04c4da17108e75bd5a928b8359c287833c858e16191507511bb0008a36235cc4`)
  diunggah manual — `gh` tidak terpasang di mesin ini.
- Test regresi `a_motion_picked_in_the_inspector_is_committed` dan
  `replacing_legacy_motion_commits_both_formats_in_one_patch` belum
  dijalankan lokal (build test crate `concat` dihentikan); CI "Headless
  quality checks" berjalan pada commit ini.
