"""Unit tests for unattended bag ownership timing logic."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from security_ai_system.detectors.bag_detector import (
    BagDetectorConfig,
    SuspiciousBagDetector,
)
from security_ai_system.trackers.tracker import TrackedObject
from security_ai_system.utils.types import BoundingBox


class SuspiciousBagDetectorStateTests(unittest.TestCase):
    def test_bag_becomes_suspicious_after_owner_leaves_timeout(self) -> None:
        detector = SuspiciousBagDetector(
            camera_id="cam-test",
            config=BagDetectorConfig(unattended_timeout_sec=2.0),
        )
        bag = TrackedObject("bag-1", "backpack", BoundingBox(80, 50, 120, 100), 0.9)
        owner_near = TrackedObject("person-1", "person", BoundingBox(0, 0, 50, 100), 0.95)
        owner_far = TrackedObject("person-1", "person", BoundingBox(900, 0, 950, 100), 0.95)

        first_status = detector._update_bag_states([bag], [owner_near], 100.0)["bag-1"]
        self.assertEqual(first_status.owner.track_id, "person-1")
        self.assertFalse(first_status.is_suspicious)

        separated_status = detector._update_bag_states([bag], [owner_far], 101.0)["bag-1"]
        self.assertFalse(separated_status.is_suspicious)

        suspicious_status = detector._update_bag_states([bag], [owner_far], 103.1)["bag-1"]
        self.assertTrue(suspicious_status.is_suspicious)
        self.assertGreaterEqual(suspicious_status.unattended_seconds, 2.0)

    def test_owner_return_resets_unattended_timer(self) -> None:
        detector = SuspiciousBagDetector(
            camera_id="cam-test",
            config=BagDetectorConfig(unattended_timeout_sec=2.0),
        )
        bag = TrackedObject("bag-1", "handbag", BoundingBox(80, 50, 120, 100), 0.9)
        owner_near = TrackedObject("person-1", "person", BoundingBox(0, 0, 50, 100), 0.95)
        owner_far = TrackedObject("person-1", "person", BoundingBox(900, 0, 950, 100), 0.95)

        detector._update_bag_states([bag], [owner_near], 100.0)
        detector._update_bag_states([bag], [owner_far], 101.0)
        returned_status = detector._update_bag_states([bag], [owner_near], 101.5)["bag-1"]

        self.assertFalse(returned_status.is_suspicious)
        self.assertEqual(returned_status.unattended_seconds, 0.0)

    def test_nearby_passerby_does_not_replace_existing_owner(self) -> None:
        detector = SuspiciousBagDetector(
            camera_id="cam-test",
            config=BagDetectorConfig(unattended_timeout_sec=2.0),
        )
        bag = TrackedObject("bag-1", "suitcase", BoundingBox(80, 50, 120, 100), 0.9)
        owner_near = TrackedObject("person-1", "person", BoundingBox(0, 0, 50, 100), 0.95)
        passerby_near = TrackedObject("person-2", "person", BoundingBox(70, 0, 120, 100), 0.95)

        detector._update_bag_states([bag], [owner_near], 100.0)
        status = detector._update_bag_states([bag], [passerby_near], 101.0)["bag-1"]

        self.assertEqual(status.owner, None)
        self.assertEqual(detector._bag_states["bag-1"].owner_track_id, "person-1")
        self.assertGreaterEqual(status.unattended_seconds, 0.0)


if __name__ == "__main__":
    unittest.main()
