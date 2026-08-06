"""Unit tests for behavior pose and motion heuristics."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from security_ai_system.behavior.motion_analysis import (  # noqa: E402
    CentroidTrackMatcher,
    MotionAnalyzer,
)
from security_ai_system.behavior.pose_analysis import (  # noqa: E402
    LEFT_HIP,
    LEFT_SHOULDER,
    LEFT_WRIST,
    RIGHT_HIP,
    RIGHT_SHOULDER,
    Keypoint,
    PoseAnalyzer,
    PoseObservation,
)
from security_ai_system.detectors.behavior_detector import BehaviorDetector  # noqa: E402
from security_ai_system.utils.types import BoundingBox  # noqa: E402


def observation(
    track_id: str,
    bbox: BoundingBox,
    keypoints: dict[int, Keypoint] | None = None,
) -> PoseObservation:
    return PoseObservation(
        track_id=track_id,
        bbox=bbox,
        confidence=0.9,
        keypoints=keypoints or {},
    )


class PoseAnalyzerTests(unittest.TestCase):
    def test_wide_horizontal_bbox_is_fall_candidate(self) -> None:
        analyzer = PoseAnalyzer()
        obs = observation("p1", BoundingBox(10, 10, 180, 90))

        self.assertTrue(analyzer.is_fall_candidate(obs))
        self.assertEqual(analyzer.analyze_person(obs)[0].label, "FALL DETECTED")

    def test_torso_angle_is_fall_candidate(self) -> None:
        analyzer = PoseAnalyzer(fall_torso_angle_deg=45.0, fall_aspect_ratio_threshold=1.5)
        # Wide bbox (200w × 100h = ratio 2.0) combined with a steep torso angle
        obs = observation(
            "p1",
            BoundingBox(10, 10, 210, 110),
            {
                LEFT_SHOULDER: Keypoint(30, 40, 0.9),
                RIGHT_SHOULDER: Keypoint(40, 40, 0.9),
                LEFT_HIP: Keypoint(110, 80, 0.9),
                RIGHT_HIP: Keypoint(120, 80, 0.9),
            },
        )

        self.assertTrue(analyzer.is_fall_candidate(obs))

    def test_close_wrist_to_other_body_is_fight_candidate(self) -> None:
        analyzer = PoseAnalyzer(fight_distance_px=200.0, wrist_to_body_distance_px=40.0)
        first = observation(
            "p1",
            BoundingBox(10, 10, 80, 160),
            {LEFT_WRIST: Keypoint(120, 60, 0.9)},
        )
        second = observation(
            "p2",
            BoundingBox(100, 20, 170, 170),
            {
                LEFT_SHOULDER: Keypoint(125, 55, 0.9),
                RIGHT_SHOULDER: Keypoint(145, 55, 0.9),
                LEFT_HIP: Keypoint(125, 110, 0.9),
                RIGHT_HIP: Keypoint(145, 110, 0.9),
            },
        )

        self.assertTrue(analyzer.is_fight_candidate(first, second))
        findings = analyzer.analyze_interactions([first, second])
        self.assertEqual(findings["p1"][0].label, "FIGHT DETECTED")


class MotionAnalyzerTests(unittest.TestCase):
    def test_fast_motion_is_running(self) -> None:
        analyzer = MotionAnalyzer(running_speed_px_per_sec=100.0)
        first = observation("p1", BoundingBox(0, 0, 40, 80))
        second = observation("p1", BoundingBox(220, 0, 260, 80))

        analyzer.update([first], 10.0)
        findings = analyzer.update([second], 11.0)["p1"]

        self.assertIn("RUNNING", [finding.label for finding in findings])

    def test_stationary_person_becomes_suspicious_loitering(self) -> None:
        analyzer = MotionAnalyzer(
            running_speed_px_per_sec=9999.0,
            loitering_duration_sec=2.0,
            loitering_radius_px=20.0,
        )
        obs = observation("p1", BoundingBox(0, 0, 40, 80))

        analyzer.update([obs], 10.0)
        findings = analyzer.update([obs], 12.5)["p1"]

        self.assertIn("SUSPICIOUS MOVEMENT", [finding.label for finding in findings])

    def test_crowd_running_adds_suspicious_movement(self) -> None:
        analyzer = MotionAnalyzer(
            running_speed_px_per_sec=100.0,
            panic_min_people=3,
            panic_running_ratio=0.6,
        )
        start = [
            observation("p1", BoundingBox(0, 0, 40, 80)),
            observation("p2", BoundingBox(0, 100, 40, 180)),
            observation("p3", BoundingBox(0, 200, 40, 280)),
        ]
        moved = [
            observation("p1", BoundingBox(220, 0, 260, 80)),
            observation("p2", BoundingBox(220, 100, 260, 180)),
            observation("p3", BoundingBox(220, 200, 260, 280)),
        ]

        analyzer.update(start, 10.0)
        findings = analyzer.update(moved, 11.0)

        self.assertTrue(
            all(
                "SUSPICIOUS MOVEMENT" in [finding.label for finding in track_findings]
                for track_findings in findings.values()
            )
        )


class BehaviorDetectorHelperTests(unittest.TestCase):
    def test_official_pose_weights_name_can_auto_download(self) -> None:
        detector = BehaviorDetector(camera_id="cam-test")
        self.assertEqual(detector._resolve_pose_weights(Path("models/yolov8n-pose.pt")), "yolov8n-pose.pt")

    def test_centroid_matcher_reuses_nearby_track_id(self) -> None:
        matcher = CentroidTrackMatcher(max_distance_px=50.0)
        first_ids = matcher.assign([BoundingBox(0, 0, 40, 80)], 10.0)
        second_ids = matcher.assign([BoundingBox(5, 0, 45, 80)], 10.5)

        self.assertEqual(first_ids, second_ids)


if __name__ == "__main__":
    unittest.main()

