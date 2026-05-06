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
    args = parser.parse_args(argv)

    ensure_output_dirs()
    configure_logging(PROJECT_ROOT / "outputs/logs")
    logger = get_logger(__name__)

    if args.dashboard:
        from security_ai_system.ui.dashboard import build_basic_camera_manager, run_dashboard

        manager = build_basic_camera_manager(args.source)
        return run_dashboard(manager)

    logger.info("AI Smart Surveillance foundation is ready.")
    print("AI Smart Surveillance foundation is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
