// SPDX-License-Identifier: AGPL-3.0-or-later
// SPDX-FileCopyrightText: 2026 Studio Inspirasi contributors

//! The launch screen's project categories, a Studio Inspirasi overlay.
//!
//! A category is a label, not a folder: projects stay wherever they are on
//! disk and the mapping lives in `project-categories.json` inside the app
//! config directory — a file this fork owns outright, so nothing upstream
//! touches it and project folders stay interchangeable with Clovercut.
//!
//! The file also remembers the recents list's view (grid or rows), since
//! there is no better owner for a launch-screen preference that is this
//! fork's own.

use std::collections::BTreeMap;
use std::path::Path;

use serde::{Deserialize, Serialize};

/// The store's file name inside the config directory.
const FILE: &str = "project-categories.json";

/// The projects grid, as posters.
pub const VIEW_GRID: i32 = 0;
/// The projects as rows, one line each — the view a hundred-project
/// category is readable in.
pub const VIEW_LIST: i32 = 1;

/// The category filter value meaning "no category": projects that were
/// never assigned. An empty filter means everything.
pub const FILTER_NONE: &str = "__none__";

/// One named category, in the order the sidebar shows it.
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct Category {
    /// The stable key the projects' mapping refers to: a slug of the name
    /// at creation, kept when the name itself is later edited.
    pub id: String,
    pub name: String,
}

/// The whole store: the named categories, which project carries which,
/// and the view the launch screen was left in.
#[derive(Serialize, Deserialize, Default, Debug)]
#[serde(default)]
pub struct Categories {
    pub categories: Vec<Category>,
    /// Project folder path → category id.
    pub projects: BTreeMap<String, String>,
    /// [`VIEW_GRID`] or [`VIEW_LIST`].
    pub view: i32,
}

impl Categories {
    /// Reads the store, starting empty when there is none or it does not
    /// parse — a damaged file loses the labels, never the launch screen.
    pub fn load(config: &Path) -> Self {
        let bytes = std::fs::read(config.join(FILE)).unwrap_or_default();
        serde_json::from_slice(&bytes).unwrap_or_default()
    }

    /// Writes the store back; failures are quiet — a label that did not
    /// save is lost next launch, which a toast would not fix.
    pub fn save(&self, config: &Path) {
        let Ok(encoded) = serde_json::to_vec_pretty(self) else {
            return;
        };
        let _ = std::fs::write(config.join(FILE), encoded);
    }

    /// The category one project path carries, following the folder across
    /// a rename or a move: an exact path miss falls back to the folder's
    /// own name among the stored keys, and a hit re-keys the mapping.
    pub fn of_project(&mut self, path: &str) -> Option<&Category> {
        if let Some(id) = self.projects.get(path).cloned() {
            return self.by_id(&id);
        }
        let base = Path::new(path).file_name()?.to_string_lossy().into_owned();
        let stale = self
            .projects
            .keys()
            .find(|key| {
                Path::new(key.as_str())
                    .file_name()
                    .is_some_and(|name| name == base.as_str())
            })
            .cloned();
        let id = stale.and_then(|key| self.projects.remove(&key))?;
        self.projects.insert(path.to_owned(), id.clone());
        self.by_id(&id)
    }

    /// A category by id, if that id still names one.
    pub fn by_id(&self, id: &str) -> Option<&Category> {
        self.categories.iter().find(|category| category.id == id)
    }

    /// Makes a category and returns its id: the name slugged, numbered if
    /// the slug is taken, so "Kajian Tafsir" and "kajian tafsir" cannot
    /// collide on disk.
    pub fn create(&mut self, name: &str) -> Option<String> {
        let base = slug(name);
        if base.is_empty() {
            return None;
        }
        let id = std::iter::once(base.clone())
            .chain((2..).map(|n| format!("{base}-{n}")))
            .find(|candidate| self.by_id(candidate).is_none())?;
        self.categories.push(Category {
            id: id.clone(),
            name: name.trim().to_owned(),
        });
        Some(id)
    }

    /// Points one project at a category — or takes it off any, on an
    /// empty id. A category the id does not name is refused.
    pub fn assign(&mut self, path: &str, id: &str) {
        if id.is_empty() {
            self.projects.remove(path);
        } else if self.by_id(id).is_some() {
            self.projects.insert(path.to_owned(), id.to_owned());
        }
    }

    /// The colour a category wears on the page: an index into the brand
    /// ladder by where the category stands, so the palette never needs a
    /// picker and two neighbours never share a colour.
    pub fn colour_of(&self, id: &str) -> [u8; 4] {
        const PALETTE: [[u8; 4]; 6] = [
            [0x5A, 0xC4, 0xCD, 255], // brand cyan
            [0x2C, 0xB1, 0xBC, 255], // brand teal
            [0x7A, 0xD9, 0xA0, 255],
            [0xE8, 0xC5, 0x6B, 255],
            [0xC9, 0x9A, 0xE8, 255],
            [0xE8, 0x8F, 0xA3, 255],
        ];
        let index = self
            .categories
            .iter()
            .position(|category| category.id == id)
            .unwrap_or(0);
        PALETTE[index % PALETTE.len()]
    }
}

/// Lowercases and dashes a name into a usable id, keeping letters and
/// digits from any script and dropping the rest to separators.
fn slug(name: &str) -> String {
    let mut slug = String::new();
    let mut dashed = true;
    for letter in name.trim().chars().flat_map(char::to_lowercase) {
        if letter.is_alphanumeric() {
            slug.push(letter);
            dashed = false;
        } else if !dashed {
            slug.push('-');
            dashed = true;
        }
    }
    slug.trim_end_matches('-').to_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn slugs_names_into_unique_ids() {
        let mut cats = Categories::default();
        assert_eq!(cats.create("Kajian Tafsir").as_deref(), Some("kajian-tafsir"));
        assert_eq!(cats.create("kajian tafsir").as_deref(), Some("kajian-tafsir-2"));
        assert_eq!(cats.create("  ").as_deref(), None);
    }

    #[test]
    fn assigning_and_unassigning_a_path() {
        let mut cats = Categories::default();
        let id = cats.create("Batch 3").unwrap();
        cats.assign("/a/b", &id);
        assert_eq!(cats.of_project("/a/b").unwrap().id, id);
        cats.assign("/a/b", "");
        assert!(cats.of_project("/a/b").is_none());
        cats.assign("/a/b", "not-a-category");
        assert!(cats.of_project("/a/b").is_none());
    }

    #[test]
    fn a_moved_folder_keeps_its_category_by_basename() {
        let mut cats = Categories::default();
        let id = cats.create("Kajian").unwrap();
        cats.assign("/old/place/derajat-kafir-001", &id);
        assert_eq!(cats.of_project("/new/spot/derajat-kafir-001").unwrap().id, id);
        assert_eq!(
            cats.projects.get("/new/spot/derajat-kafir-001").map(String::as_str),
            Some(id.as_str())
        );
        assert!(!cats.projects.contains_key("/old/place/derajat-kafir-001"));
    }

    #[test]
    fn a_broken_store_reads_as_empty() {
        let dir = std::env::temp_dir().join(format!("cats-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join(FILE), b"not json").unwrap();
        let cats = Categories::load(&dir);
        assert!(cats.categories.is_empty());
        let _ = std::fs::remove_dir_all(&dir);
    }
}
