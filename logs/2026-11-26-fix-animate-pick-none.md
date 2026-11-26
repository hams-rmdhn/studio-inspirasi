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
