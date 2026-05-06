"""Unit tests for threat scoring and alert persistence."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from security_ai_system.alerts.alert_manager import (  # noqa: E402
    AlertManager,
    AlertManagerConfig,
)
from security_ai_system.alerts.threat_engine import (  # noqa: E402
    ThreatLevel,
    ThreatScoringEngine,
)
from security_ai_system.utils.types import Detection, Severity  # noqa: E402


TEST_OUTPUT = Path(__file__).resolve().parents[1] / "_test_outputs" / "alerts"


def make_detection(label: str, score: int = 0, confidence: float = 0.9) -> Detection:
    return Detection(
        label=label,
        confidence=confidence,
        severity=Severity.HIGH,
        threat_score=score,
    )


class ThreatScoringEngineTests(unittest.TestCase):
    def test_level_thresholds_match_project_requirement(self) -> None:
        self.assertEqual(ThreatScoringEngine.level_for_score(0), ThreatLevel.LOW)
        self.assertEqual(ThreatScoringEngine.level_for_score(40), ThreatLevel.MEDIUM)
        self.assertEqual(ThreatScoringEngine.level_for_score(80), ThreatLevel.HIGH)
        self.assertEqual(ThreatScoringEngine.level_for_score(100), ThreatLevel.HIGH)
        self.assertEqual(ThreatScoringEngine.level_for_score(101), ThreatLevel.CRITICAL)

    def test_fallback_score_map_is_used_when_detection_score_missing(self) -> None:
        engine = ThreatScoringEngine(active_window_sec=10.0)
        state = engine.update_from_detections(
            [make_detection("SUSPICIOUS BAG")],
            camera_id="cam-1",
            timestamp=10.0,
        )

        self.assertEqual(state.total_score, 40)
        self.assertEqual(state.level, ThreatLevel.MEDIUM)

    def test_active_window_expires_old_contributions(self) -> None:
        engine = ThreatScoringEngine(active_window_sec=2.0)
        engine.update_from_detections(
            [make_detection("GUNSHOT DETECTED")],
            camera_id="mic-1",
            timestamp=10.0,
        )
        state = engine.current_state(timestamp=13.0)

        self.assertEqual(state.total_score, 0)
        self.assertEqual(state.level, ThreatLevel.LOW)

    def test_multiple_alerts_escalate_to_critical(self) -> None:
        engine = ThreatScoringEngine(active_window_sec=10.0)
        state = engine.update_from_detections(
            [make_detection("KNIFE DETECTED"), make_detection("SCREAM DETECTED")],
            camera_id="cam-1",
            timestamp=10.0,
        )

        self.assertEqual(state.total_score, 140)
        self.assertEqual(state.level, ThreatLevel.CRITICAL)


class AlertManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        TEST_OUTPUT.mkdir(parents=True, exist_ok=True)
        for path in (TEST_OUTPUT / "logs").glob("*"):
            if path.is_file():
                path.unlink()

    def test_alert_manager_writes_jsonl_and_csv_events(self) -> None:
        manager = AlertManager(
            AlertManagerConfig(
                output_dir=TEST_OUTPUT,
                save_snapshots=False,
                event_cooldown_sec=0.0,
            )
        )
        events = manager.handle_alerts(
            [make_detection("GUNSHOT DETECTED")],
            camera_id="mic-1",
            timestamp=10.0,
            source="microphone",
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].threat_level, ThreatLevel.CRITICAL.value)
        self.assertTrue((TEST_OUTPUT / "logs" / "threat_events.jsonl").exists())
        self.assertTrue((TEST_OUTPUT / "logs" / "threat_events.csv").exists())

        line = (TEST_OUTPUT / "logs" / "threat_events.jsonl").read_text(
            encoding="utf-8"
        ).strip()
        payload = json.loads(line)
        self.assertEqual(payload["label"], "GUNSHOT DETECTED")
        self.assertEqual(payload["source"], "microphone")

    def test_event_cooldown_suppresses_duplicate_event_but_score_updates(self) -> None:
        manager = AlertManager(
            AlertManagerConfig(
                output_dir=TEST_OUTPUT,
                save_snapshots=False,
                event_cooldown_sec=5.0,
            )
        )
        first = manager.handle_alerts(
            [make_detection("SCREAM DETECTED")],
            camera_id="mic-1",
            timestamp=10.0,
        )
        second = manager.handle_alerts(
            [make_detection("SCREAM DETECTED")],
            camera_id="mic-1",
            timestamp=11.0,
        )

        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(manager.current_threat_state(timestamp=11.0).total_score, 120)

    def test_detection_snapshot_path_is_preserved(self) -> None:
        manager = AlertManager(
            AlertManagerConfig(
                output_dir=TEST_OUTPUT,
                save_snapshots=False,
                event_cooldown_sec=0.0,
            )
        )
        detection = make_detection("SUSPICIOUS BAG")
        detection.metadata["snapshot_path"] = "outputs/snapshots/bag.jpg"
        event = manager.handle_alerts([detection], camera_id="cam-1", timestamp=10.0)[0]

        self.assertEqual(event.snapshot_path, "outputs/snapshots/bag.jpg")


if __name__ == "__main__":
    unittest.main()
