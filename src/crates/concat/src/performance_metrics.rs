// SPDX-License-Identifier: AGPL-3.0-or-later
// SPDX-FileCopyrightText: 2026 Clovercut contributors

//! Measurement helpers testable without compiling the graphical UI.
use std::path::Path;

/// Linux process counters; absent or malformed values stay unknown.
#[derive(Debug, Default, PartialEq)]
pub struct ProcessMemory {
    /// Resident set size of this process.
    pub rss_bytes: Option<u64>,
    /// Peak resident set size reported for this process.
    pub high_water_bytes: Option<u64>,
}

/// Parse kB counters without inventing zero on unsupported platforms.
pub fn process_memory(status: &str) -> ProcessMemory {
    let counter = |key: &str| {
        status.lines().find_map(|line| {
            let mut parts = line.strip_prefix(key)?.split_whitespace();
            let value = parts.next()?.parse::<u64>().ok()?;
            (parts.next()? == "kB").then_some(())?;
            value.checked_mul(1024)
        })
    };
    ProcessMemory {
        rss_bytes: counter("VmRSS:"),
        high_water_bytes: counter("VmHWM:"),
    }
}

/// Device-wide counters, not process allocations or necessarily our adapter.
/// An empty list means unavailable; a reported zero remains zero.
pub fn drm_device_vram(root: &Path) -> Vec<(String, u64)> {
    let Ok(entries) = std::fs::read_dir(root) else {
        return Vec::new();
    };
    let mut counters = Vec::new();
    for entry in entries.flatten() {
        let name = entry.file_name().to_string_lossy().into_owned();
        if !name.strip_prefix("card").is_some_and(|suffix| {
            !suffix.is_empty() && suffix.bytes().all(|byte| byte.is_ascii_digit())
        }) {
            continue;
        }
        if let Ok(text) = std::fs::read_to_string(entry.path().join("device/mem_info_vram_used"))
            && let Ok(bytes) = text.trim().parse::<u64>()
        {
            counters.push((name, bytes));
        }
    }
    counters.sort_by(|left, right| left.0.cmp(&right.0));
    counters
}

/// Mean, nearest-rank p95 and maximum for finite nonnegative millisecond samples.
pub fn stats_summary(samples: &[f64]) -> Option<(f64, f64, f64)> {
    if samples.is_empty()
        || samples
            .iter()
            .any(|value| !value.is_finite() || *value < 0.0)
    {
        return None;
    }
    let mut sorted = samples.to_vec();
    sorted.sort_by(f64::total_cmp);
    let mean = sorted.iter().map(|value| value / sorted.len() as f64).sum();
    let p95 = ((sorted.len() as f64 * 0.95).ceil() as usize).saturating_sub(1);
    Some((mean, sorted[p95], *sorted.last()?))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn invalid_process_counters_are_not_zero() {
        for text in [
            "",
            "VmRSS: broken kB",
            "VmRSS: 2 MB",
            "VmRSS: 18446744073709551615 kB",
        ] {
            assert_eq!(process_memory(text), ProcessMemory::default());
        }
        assert_eq!(
            process_memory("Name: test\nVmRSS:\t0 kB\nVmHWM: 27 kB\n"),
            ProcessMemory {
                rss_bytes: Some(0),
                high_water_bytes: Some(27 * 1024)
            }
        );
        assert_eq!(process_memory("VmRSS: 10 kB").high_water_bytes, None);
    }

    #[test]
    fn vram_counters_preserve_zero_and_device_identity() {
        let root = std::env::temp_dir().join(format!("clovercut-metrics-{}", std::process::id()));
        std::fs::create_dir(&root).unwrap();
        for (name, text) in [
            ("card0", "0\n"),
            ("card7", "1024\n"),
            ("card1", "unavailable"),
            ("card0-DP-1", "999"),
        ] {
            let device = root.join(name).join("device");
            std::fs::create_dir_all(&device).unwrap();
            std::fs::write(device.join("mem_info_vram_used"), text).unwrap();
        }
        assert_eq!(
            drm_device_vram(&root),
            vec![("card0".into(), 0), ("card7".into(), 1024)]
        );
        assert!(drm_device_vram(&root.join("missing")).is_empty());
        std::fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn nearest_rank_p95_keeps_outliers() {
        let mut samples: Vec<f64> = (1..=20).rev().map(f64::from).collect();
        samples[0] = 1000.0;
        assert_eq!(stats_summary(&samples), Some((59.5, 19.0, 1000.0)));
        assert_eq!(stats_summary(&[0.0]), Some((0.0, 0.0, 0.0)));
        assert_eq!(stats_summary(&[1e308, 1e308]), Some((1e308, 1e308, 1e308)));
    }

    #[test]
    fn invalid_or_empty_timings_are_not_successful_zero_samples() {
        for samples in [&[][..], &[f64::NAN], &[f64::INFINITY], &[-1.0]] {
            assert_eq!(stats_summary(samples), None);
        }
    }
}
