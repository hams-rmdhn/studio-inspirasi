// SPDX-License-Identifier: AGPL-3.0-or-later
// SPDX-FileCopyrightText: 2026 Clovercut contributors

//! The source interval and frame count shared by Enhance and its estimate.

pub(crate) struct Plan {
    pub span: Option<(f64, f64)>,
    pub frames: f64,
}

pub(crate) fn plan(
    still: bool,
    original_start: f64,
    covered: f64,
    media_duration: Option<f64>,
    frame_rate: f64,
) -> Plan {
    if still {
        return Plan {
            span: None,
            frames: 1.0,
        };
    }
    // Keep one source second either side for small trims after enhancement.
    let from = (original_start - 1.0).max(0.0);
    let to = (original_start + covered + 1.0).min(media_duration.unwrap_or(f64::MAX));
    let duration = (to - from).max(covered);
    Plan {
        span: Some((from, duration)),
        frames: duration * frame_rate,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn short_cut_of_a_long_recording_estimates_only_the_requested_span() {
        let work = plan(false, 100.0, 10.0, Some(3600.0), 30.0);
        assert_eq!(work.span, Some((99.0, 12.0)));
        assert_eq!(work.frames, 360.0);
        assert!(work.frames < 3600.0 * 30.0);
    }

    #[test]
    fn margins_respect_media_edges_and_an_unknown_end() {
        for (start, covered, length, expected) in [
            (0.0, 10.0, Some(100.0), (0.0, 11.0)),
            (95.0, 5.0, Some(100.0), (94.0, 6.0)),
            (0.0, 10.0, Some(10.0), (0.0, 10.0)),
            (100.0, 10.0, None, (99.0, 12.0)),
        ] {
            let work = plan(false, start, covered, length, 25.0);
            assert_eq!(work.span, Some(expected));
            assert_eq!(work.frames, expected.1 * 25.0);
        }
    }

    #[test]
    fn retimed_source_coverage_and_fractional_rate_drive_the_estimate() {
        // Ten timeline seconds at 2x consume twenty source seconds.
        let work = plan(false, 50.0, 10.0 * 2.0, Some(3600.0), 30000.0 / 1001.0);
        assert_eq!(work.span, Some((49.0, 22.0)));
        assert!((work.frames - 22.0 * 30000.0 / 1001.0).abs() < 1e-10);
    }

    #[test]
    fn original_offset_of_an_enhanced_copy_is_used_and_stills_are_one_frame() {
        let work = plan(false, 3.0 + 99.0, 10.0, Some(3600.0), 30.0);
        assert_eq!(work.span, Some((101.0, 12.0)));
        let still = plan(true, 0.0, 20.0, None, 30.0);
        assert_eq!(still.span, None);
        assert_eq!(still.frames, 1.0);
    }
}
