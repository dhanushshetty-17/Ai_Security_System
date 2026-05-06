"""Dashboard user interface."""

from security_ai_system.ui.dashboard import (
    DashboardUnavailableError,
    GridPosition,
    build_basic_camera_manager,
    compute_grid_positions,
    event_row,
    format_fps,
    run_dashboard,
    threat_level_color,
)

__all__ = [
    "DashboardUnavailableError",
    "GridPosition",
    "build_basic_camera_manager",
    "compute_grid_positions",
    "event_row",
    "format_fps",
    "run_dashboard",
    "threat_level_color",
]
