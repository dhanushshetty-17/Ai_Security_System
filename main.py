"""Application entry point.

Full camera workers, detectors, alerting, and dashboard startup are added in
later modules. This starter entry point verifies the package imports and paths.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from security_ai_system.utils.logger import configure_logging, get_logger


PROJECT_ROOT = Path(__file__).resolve().parent


def ensure_output_dirs() -> None:
    """Create output folders required by alerts and evidence saving."""

    for path in (
        PROJECT_ROOT / "outputs/logs",
        PROJECT_ROOT / "outputs/snapshots",
        PROJECT_ROOT / "models",
    ):
        path.mkdir(parents=True, exist_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AI Smart Surveillance and Threat Detection System"
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch the PyQt5 dashboard.",
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Dashboard camera source. Repeat for multiple sources.",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Launch the Web dashboard.",
    )
    args = parser.parse_args(argv)

    ensure_output_dirs()
    configure_logging(PROJECT_ROOT / "outputs/logs")
    logger = get_logger(__name__)

    if args.dashboard:
        from security_ai_system.ui.dashboard import build_basic_camera_manager, run_dashboard

        manager = build_basic_camera_manager(args.source)
        return run_dashboard(manager)

    if args.web:
        import uvicorn
        import threading
        import time
        from security_ai_system.ui.dashboard import build_basic_camera_manager
        from security_ai_system.web.app import app
        from security_ai_system.alerts.alert_manager import AlertManager, AlertManagerConfig
        from security_ai_system.detectors.audio_detector import AudioThreatDetector, AudioThreatDetectorConfig
        from security_ai_system.audio.yamnet_classifier import YamNetClassifierConfig
        from security_ai_system.run_demo import run_audio_capture

        manager = build_basic_camera_manager(args.source)
        alert_manager = AlertManager(config=AlertManagerConfig(alarm_enabled=False))
        alert_manager._audio_event_queue = []
        
        # Audio thread
        audio_config = AudioThreatDetectorConfig(
            classifier_config=YamNetClassifierConfig(confidence_threshold=0.35)
        )
        audio_detector = AudioThreatDetector(camera_id="microphone-1", config=audio_config)
        audio_detector.load()
        
        audio_thread = threading.Thread(
            target=run_audio_capture,
            args=(audio_detector, alert_manager),
            daemon=True
        )
        audio_thread.start()

        # Video Alert polling thread for Web
        def poll_video_alerts():
            while True:
                for worker in manager.workers():
                    while True:
                        result = worker.read_result(timeout=0.0)
                        if result is None:
                            break
                        # Handle camera alerts
                        events = alert_manager.handle_camera_result(result)
                        # Drain audio alerts
                        if app.state.settings.get("audio_enabled", True):
                            if alert_manager._audio_event_queue:
                                events.extend(alert_manager._audio_event_queue)
                                alert_manager._audio_event_queue.clear()
                        else:
                            alert_manager._audio_event_queue.clear()
                time.sleep(0.1)

        polling_thread = threading.Thread(target=poll_video_alerts, daemon=True)
        polling_thread.start()

        manager.start_all()
        app.state.camera_manager = manager
        app.state.alert_manager = alert_manager
        app.state.audio_detector = audio_detector
        app.state.project_root = str(PROJECT_ROOT)

        logger.info("Starting web dashboard on http://127.0.0.1:8000")
        uvicorn.run(app, host="127.0.0.1", port=8000)
        manager.stop_all()
        return 0

    logger.info("AI Smart Surveillance foundation is ready.")
    print("AI Smart Surveillance foundation is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
