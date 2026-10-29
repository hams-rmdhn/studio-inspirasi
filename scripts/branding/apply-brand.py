#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Applies the Studio Inspirasi brand over a Clovercut tree.
#
# This is the whole difference between upstream tulcoturo/clovercut and
# this distribution, as a pure function of the tree: run it once, run it
# after every `git merge upstream/main`, run it twice - the second run
# changes nothing. Files and strings that are functional, not display -
# crate names, the cargo binary, shortcut profile ids, SPDX copyright
# headers - are deliberately left alone so merges stay small.
#
#   python3 scripts/branding/apply-brand.py
#
# Needs branding/logo-source.png (the brand's source art) and sips for
# the icon sizes; make-brand-assets.py is invoked first when the derived
# PNGs are missing.

import base64
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRAND = ROOT / "branding"

NAME = "Studio Inspirasi"
SLUG = "studio-inspirasi"
IDENTIFIER = "io.github.hams-rmdhn.studio-inspirasi"
REPO = "hams-rmdhn/studio-inspirasi"
REPO_URL = f"https://github.com/{REPO}"
ACCENT = (0x5A, 0xC4, 0xCD)  # leaf cyan

# ── display-string replacements ─────────────────────────────────────
# (path, [(old, new), ...]) applied to the file's whole text. Old strings
# are upstream's; once replaced they are absent, so a second run is a
# no-op and an upstream merge that restores them is corrected again.

EXPLICIT = {
    "src/crates/concat/ui/app.slint": [
        ('title: "Clovercut";', f'title: "{NAME}";'),
    ],
    "src/crates/concat/ui/start.slint": [
        ('"Clovercut " + root.version', f'"{NAME} " + root.version'),
        ("applogo.svg", "applogo.png"),
        ("typography.svg", "typography.png"),
    ],
    "src/crates/concat/ui/title-bar.slint": [
        ("applogo.svg", "applogo.png"),
        ("typography.svg", "typography.png"),
    ],
    "src/crates/concat/ui/dialogs/settings.slint": [
        ("applogo.svg", "applogo.png"),
        ("typography.svg", "typography.png"),
    ],
    "src/crates/concat/ui/dialogs/export.slint": [
        ("applogo.svg", "applogo.png"),
    ],
    "src/crates/concat/src/lib.rs": [
        ("0x24, 0xd4, 0x7a", "0x5a, 0xc4, 0xcd"),
    ],
    "src/crates/concat/src/launch.rs": [
        ("usage: clovercut", f"usage: {SLUG}"),
    ],
    "src/crates/concat/src/panes/start.rs": [
        ("https://github.com/tulcoturo/clovercut", REPO_URL),
    ],
    "src/crates/concat/src/platform.rs": [
        ("io.github.tulcoturo.clovercut", IDENTIFIER),
    ],
    "src/crates/concat-host/src/dirs.rs": [
        ('pub const IDENTIFIER: &str = "io.github.tulcoturo.clovercut";',
         f'pub const IDENTIFIER: &str = "{IDENTIFIER}";'),
    ],
    "src/crates/concat-host/src/updates.rs": [
        ("tulcoturo/clovercut", REPO),
        ("clovercut.list", f"{SLUG}.list"),
        ('"clovercut-"', f'"{SLUG}-"'),
        ('-q", "clovercut"', f'-q", "{SLUG}"'),
    ],
    "site/index.html": [
        ("https://github.com/tulcoturo/clovercut", REPO_URL),
        ("tulcoturo.github.io/clovercut", "hams-rmdhn.github.io/studio-inspirasi"),
    ],
    ".github/workflows/build-app.yml": [
        ("app=Clovercut.app", f'app="{NAME}.app"'),
        ('"$app/Contents/MacOS/clovercut"', f'"$app/Contents/MacOS/{SLUG}"'),
        ("io.github.tulcoturo.clovercut", IDENTIFIER),
        ("<key>CFBundleExecutable</key><string>clovercut</string>",
         f"<key>CFBundleExecutable</key><string>{SLUG}</string>"),
        ("Clovercut.icns", f"{NAME}.icns"),
        ("-volname Clovercut", f'-volname "{NAME}"'),
        ('dmg="Clovercut-', f'dmg="Studio-Inspirasi-'),
        ("name: Clovercut-macos-", "name: Studio-Inspirasi-macos-"),
        ("smoke-macos.sh Clovercut.app", f'smoke-macos.sh "{NAME}.app"'),
    ],
    "assets/linux/io.github.hams-rmdhn.studio-inspirasi.desktop": [
        ("Name=Clovercut", f"Name={NAME}"),
        ("Exec=clovercut", f"Exec={SLUG}"),
        ("Icon=clovercut", f"Icon={SLUG}"),
        ("io.github.tulcoturo.clovercut", IDENTIFIER),
    ],
    "assets/linux/studio-inspirasi": [
        ("exec /opt/clovercut/clovercut", f"exec /opt/{SLUG}/{SLUG}"),
    ],
    "assets/linux/nfpm.yaml": [
        ("name: clovercut", f"name: {SLUG}"),
        ("maintainer: Clovercut contributors <tulcoturo@users.noreply.github.com>",
         "maintainer: Studio Inspirasi contributors <66541242+hams-rmdhn@users.noreply.github.com>"),
        ("vendor: Clovercut contributors", "vendor: Studio Inspirasi contributors"),
        ("homepage: https://github.com/tulcoturo/clovercut", f"homepage: {REPO_URL}"),
        ("dst: /opt/clovercut/clovercut", f"dst: /opt/{SLUG}/{SLUG}"),
        ("dst: /opt/clovercut/lib/", f"dst: /opt/{SLUG}/lib/"),
        ("${CLOVERCUT_REPO}/assets/linux/clovercut",
         "${CLOVERCUT_REPO}/assets/linux/studio-inspirasi"),
        ("dst: /usr/bin/clovercut", f"dst: /usr/bin/{SLUG}"),
        ("src: io.github.tulcoturo.clovercut.desktop",
         "src: io.github.hams-rmdhn.studio-inspirasi.desktop"),
        ("dst: /usr/share/applications/io.github.tulcoturo.clovercut.desktop",
         f"dst: /usr/share/applications/{IDENTIFIER}.desktop"),
        ("apps/clovercut.png", f"apps/{SLUG}.png"),
        ("dst: /usr/share/doc/clovercut/", f"dst: /usr/share/doc/{SLUG}/"),
    ],
}

# Files where every remaining "Clovercut" display string becomes the
# brand name - lines carrying the SPDX copyright attribution are kept
# verbatim, and keymap.rs's profile id and the crates' names are not
# display strings at all.
GENERIC = [
    "src/crates/concat/src/main.rs",
    "src/crates/concat/src/sysinfo.rs",
    "src/crates/concat/src/platform.rs",
    "src/crates/concat/src/panes/start.rs",
    "src/crates/concat/src/phase5_ui_walkthrough.rs",
    "src/crates/concat/build.rs",
    "src/crates/concat-host/src/freesound.rs",
    "src/crates/concat-host/src/lock.rs",
    "src/crates/concat-host/src/machine.rs",
    "src/crates/concat-host/src/net.rs",
    "src/crates/concat-host/src/opengameart.rs",
    "src/crates/concat-host/src/projects.rs",
    "src/crates/concat-host/src/record.rs",
    "src/crates/concat-host/src/route.rs",
    "src/crates/concat-host/src/session.rs",
    "src/crates/concat-host/src/updates.rs",
    "site/index.html",
    "site/app.js",
]

# Strings where the word must stay one token: user agents and other
# protocol words, applied before the generic pass so the space never
# reaches them.
TOKEN = [
    ("Clovercut/", "Studio-Inspirasi/"),
    ('wide("Clovercut")', 'wide("Studio-Inspirasi")'),
]

SPDX = "SPDX-FileCopyrightText"

# Files renamed for the brand, applied before the text rules so the new
# path is what the rules then edit.
RENAMES = [
    ("assets/linux/io.github.tulcoturo.clovercut.desktop",
     f"assets/linux/{IDENTIFIER}.desktop"),
    ("assets/linux/clovercut", "assets/linux/studio-inspirasi"),
]

# ── the data-home migration, injected into dirs.rs ───────────────────

MIGRATE_CALL_ANCHOR = 'Ok(apple(&home()?, cfg!(target_os = "ios")))'
MIGRATE_CALL = '''let home = home()?;
            migrate_legacy(&home);
            Ok(apple(&home, cfg!(target_os = "ios")))'''
MIGRATE_ANCHOR = "/// Which platform's rule names the directories."
MIGRATE_CODE = '''/// The identifier an earlier release of this app used. Its data folder
/// moves across once, below, rather than stranding gigabytes of models.
const LEGACY_IDENTIFIER: &str = "io.github.tulcoturo.clovercut";

/// Moves the whole data home from the legacy identifier to this app's,
/// once: a folder already at the new name is left alone, and nothing
/// happens on machines that never ran the earlier app. A rename, so
/// gigabytes of downloaded models move instantly on the same volume.
fn migrate_legacy(home: &Path) {
    let support = home.join("Library").join("Application Support");
    let (old, new) = (
        support.join(LEGACY_IDENTIFIER),
        support.join(IDENTIFIER),
    );
    if old.is_dir() && !new.exists() {
        let _ = std::fs::rename(&old, &new);
    }
}

'''


def apply_file(path, replacements):
    text = path.read_text()
    original = text
    for old, new in replacements:
        text = text.replace(old, new)
    if text != original:
        path.write_text(text)
        return True
    return False


def apply_generic(path):
    lines = path.read_text().splitlines(keepends=True)
    out = []
    changed = False
    for line in lines:
        if SPDX in line:
            out.append(line)
            continue
        new = line
        for old, repl in TOKEN:
            new = new.replace(old, repl)
        new = new.replace("Clovercut", NAME)
        if new != line:
            changed = True
        out.append(new)
    if changed:
        path.write_text("".join(out))
    return changed


def apply_en_json(path):
    """'Clovercut' inside values only: i18n keys must never be renamed."""
    lines = path.read_text().splitlines(keepends=True)
    out = []
    changed = False
    for line in lines:
        key_end = line.find('":')
        if key_end != -1:
            head, tail = line[:key_end + 2], line[key_end + 2:]
            new_tail = tail.replace("Clovercut", NAME)
            if new_tail != tail:
                changed = True
            out.append(head + new_tail)
        else:
            out.append(line)
    if changed:
        path.write_text("".join(out))
    return changed


def apply_dirs_migration(path):
    text = path.read_text()
    changed = False
    if "migrate_legacy" not in text:
        text = text.replace(MIGRATE_ANCHOR, MIGRATE_CODE + MIGRATE_ANCHOR, 1)
        changed = "migrate_legacy" in text
    if MIGRATE_CALL_ANCHOR in text:
        text = text.replace(MIGRATE_CALL_ANCHOR, MIGRATE_CALL, 1)
        changed = True
    if changed:
        path.write_text(text)
    elif "migrate_legacy(&home)" not in text:
        print(f"  ! {path.relative_to(ROOT)}: migration anchors not found - "
              "reconcile by hand", file=sys.stderr)
    return changed


def svg_of(png, width, height, title):
    b64 = base64.b64encode(png.read_bytes()).decode()
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'viewBox="0 0 {width} {height}">\n'
            f'  <title>{title}</title>\n'
            f'  <image x="0" y="0" width="{width}" height="{height}" '
            f'xlink:href="data:image/png;base64,{b64}"/>\n'
            f'</svg>\n')


def ensure_brand_assets():
    if all((BRAND / name).is_file()
           for name in ("leaf.png", "wordmark.png", "icon-1024.png")):
        return
    script = ROOT / "scripts/branding/make-brand-assets.py"
    subprocess.run([sys.executable, str(script)], check=True)


def apply_assets():
    brand = json.loads((BRAND / "brand.json").read_text())
    icon = BRAND / "icon-1024.png"
    wordmark = BRAND / "wordmark.png"

    # Raster assets: the app icon square and the wordmark. Names are kept
    # so references - and upstream's icon generation script - need none.
    (ROOT / "assets/applogo.png").write_bytes(icon.read_bytes())
    (ROOT / "assets/typography.png").write_bytes(wordmark.read_bytes())
    for size in (16, 32, 64, 128, 256, 512):
        subprocess.run(
            ["sips", "-z", str(size), str(size), str(icon),
             "--out", str(ROOT / f"assets/icons/clovercut_{size}.png")],
            check=True, capture_output=True)
    (ROOT / "assets/clovercut_512.png").write_bytes(
        (ROOT / "assets/icons/clovercut_512.png").read_bytes())

    # Vector wrappers for the consumers that ask for .svg (the docs site,
    # the README): the brand PNG carried inside the SVG.
    (ROOT / "assets/applogo.svg").write_text(svg_of(icon, 1024, 1024, NAME))
    (ROOT / "assets/typography.svg").write_text(
        svg_of(wordmark, 493, 69, NAME))
    (ROOT / "assets/logo.svg").write_text(svg_of(icon, 1024, 1024, NAME))
    site_assets = ROOT / "site/site_assets"
    if site_assets.is_dir():
        (site_assets / "applogo.svg").write_text(
            svg_of(icon, 1024, 1024, NAME))
        (site_assets / "typography.svg").write_text(
            svg_of(wordmark, 493, 69, NAME))

    # logo.jpg is the icon's flat-card version: white ground, no alpha.
    spec = importlib.util.spec_from_file_location(
        "make_brand_assets", ROOT / "scripts/branding/make-brand-assets.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    w, h, px = mod.decode_png(icon)
    for i in range(0, len(px), 4):
        a = px[i + 3] / 255.0
        px[i] = int(px[i] * a + 255 * (1 - a))
        px[i + 1] = int(px[i + 1] * a + 255 * (1 - a))
        px[i + 2] = int(px[i + 2] * a + 255 * (1 - a))
        px[i + 3] = 255
    flat = BRAND / "icon-flat.png"
    flat.write_bytes(mod.encode_png(w, h, px))
    subprocess.run(["sips", "-s", "format", "jpeg", str(flat),
                    "--out", str(ROOT / "assets/logo.jpg")],
                   check=True, capture_output=True)
    flat.unlink()


def main():
    ensure_brand_assets()
    changed = []
    for old_rel, new_rel in RENAMES:
        old, new = ROOT / old_rel, ROOT / new_rel
        if old.is_file() and not new.exists():
            old.rename(new)
            changed.append(f"{old_rel} -> {new_rel}")
    for rel, replacements in EXPLICIT.items():
        path = ROOT / rel
        if path.is_file() and apply_file(path, replacements):
            changed.append(rel)
    for rel in GENERIC:
        path = ROOT / rel
        if path.is_file() and apply_generic(path):
            changed.append(rel)
    en_json = ROOT / "src/crates/concat/locales/en.json"
    if apply_en_json(en_json):
        changed.append(str(en_json.relative_to(ROOT)))
    if apply_dirs_migration(ROOT / "src/crates/concat-host/src/dirs.rs"):
        changed.append("src/crates/concat-host/src/dirs.rs (migration)")
    apply_assets()
    changed.append("assets/ (icon, wordmark, svg, site_assets)")

    for rel in changed:
        print(f"  branded {rel}")
    print(f"{NAME} brand applied.")


if __name__ == "__main__":
    main()
