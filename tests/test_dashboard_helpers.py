"""Unit tests for dashboard helpers that do not require PyQt5."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from security_ai_system.alerts import AlertEvent, ThreatLevel  # noqa: E402
from security_ai_system.ui.dashboard import (  # noqa: E402
    build_basic_camera_manager,
    compute_grid_positions,
    event_row,
    format_fps,
    threat_level_color,
)
from security_ai_system.utils.types import Severity  # noqa: E402


class DashboardHelperTests(unittest.TestCase):
    def test_compute_grid_positions_balances_camera_tiles(self) -> None:
        positions = compute_grid_positions(5)

        self.assertEqual(len(positions), 5)
        self.assertEqual((positions[0].row, positions[0].column), (0, 0))
        self.assertEqual((positions[3].row, positions[3].column), (1, 0))

    def test_compute_grid_positions_handles_empty_grid(self) -> None:
        self.assertEqual(compute_grid_positions(0), [])

    def test_format_fps(self) -> None:
        self.assertEqual(format_fps(0), "0.0 FPS")
        self.assertEqual(format_fps(12.345), "12.3 FPS")

    def test_threat_level_color_accepts_enum_and_string(self) -> None:
        self.assertEqual(threat_level_color(ThreatLevel.CRITICAL), "#7f0000")
        self.assertEqual(threat_level_color("medium"), "#a66f00")

    def test_event_row_formats_alert_event(self) -> None:
        event = AlertEvent(
            event_id="evt-1",
            timestamp=10.0,
            iso_time="2026-05-06T10:00:00",
            camera_id="cam-1",
            label="GUN DETECTED",
            severity=Severity.CRITICAL,
            confidence=0.9,
            threat_score=100,
            total_score=140,
            threat_level="CRITICAL",
        )

        self.assertEqual(
            event_row(event),
            ("2026-05-06T10:00:00", "cam-1", "GUN DETECTED", "CRITICAL", "100"),
        )

    def test_build_basic_camera_manager_infers_sources_without_starting(self) -> None:
        manager = build_basic_camera_manager(["0", "demo.mp4", "rtsp://host/live"])
        statuses = manager.statuses()

        self.assertEqual(len(statuses), 3)
        self.assertFalse(any(status.running for status in statuses))
        self.assertEqual(statuses[0].camera_id, "camera-1")


if __name__ == "__main__":
    unittest.main()

