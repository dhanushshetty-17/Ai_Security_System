"""Motion-history behavior heuristics for tracked people."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from security_ai_system.behavior.pose_analysis import PoseObservation
from security_ai_system.utils.types import BoundingBox


@dataclass(frozen=True)
class MotionFinding:
    """Motion-derived suspicious behavior finding."""

    label: str
    score: int
    reason: str


@dataclass
class MotionState:
    """Recent motion history for one tracked person."""

    track_id: str
    points: deque[tuple[float, tuple[int, int]]] = field(default_factory=lambda: deque(maxlen=90))
    bboxes: deque[BoundingBox] = field(default_factory=lambda: deque(maxlen=90))
    last_seen: float = 0.0


class CentroidTrackMatcher:
    """Simple centroid matcher for pose detections without external tracking."""

    def __init__(self, max_distance_px: float = 120.0, stale_after_sec: float = 2.0) -> None:
        self.max_distance_px = max_distance_px
        self.stale_after_sec = stale_after_sec
        self._next_id = 1
        self._tracks: dict[str, tuple[float, tuple[int, int]]] = {}

    def assign(self, boxes: list[BoundingBox], timestamp: float) -> list[str]:
        """Assign stable-enough IDs to current bounding boxes."""

        self._drop_stale(timestamp)
        assigned_ids: list[str] = []
        used_track_ids: set[str] = set()

        for box in boxes:
            center = box.center
            match_id = self._nearest_available_track(center, used_track_ids)
            if match_id is None:
                match_id = f"pose-{self._next_id}"
                self._next_id += 1

            self._tracks[match_id] = (timestamp, center)
            used_track_ids.add(match_id)
            assigned_ids.append(match_id)

        return assigned_ids

    def _nearest_available_track(
        self,
        center: tuple[int, int],
        used_track_ids: set[str],
    ) -> str | None:
        best_id: str | None = None
        best_distance = math.inf
        for track_id, (_, previous_center) in self._tracks.items():
            if track_id in used_track_ids:
                continue
            distance = math.dist(center, previous_center)
            if distance < best_distance and distance <= self.max_distance_px:
                best_id = track_id
                best_distance = distance
        return best_id

    def _drop_stale(self, timestamp: float) -> None:
        stale_ids = [
            track_id
            for track_id, (last_seen, _) in self._tracks.items()
            if timestamp - last_seen > self.stale_after_sec
        ]
        for track_id in stale_ids:
            del self._tracks[track_id]


class MotionAnalyzer:
    """Analyze tracked person motion for running, loitering, panic, and anomalies."""

    def __init__(
        self,
        running_speed_px_per_sec: float = 260.0,
        loitering_radius_px: float = 70.0,
        loitering_duration_sec: float = 30.0,
        suspicious_direction_changes: int = 4,
        panic_min_people: int = 3,
        panic_running_ratio: float = 0.6,
        stale_after_sec: float = 5.0,
    ) -> None:
        self.running_speed_px_per_sec = running_speed_px_per_sec
        self.loitering_radius_px = loitering_radius_px
        self.loitering_duration_sec = loitering_duration_sec
        self.suspicious_direction_changes = suspicious_direction_changes
        self.panic_min_people = panic_min_people
        self.panic_running_ratio = panic_running_ratio
        self.stale_after_sec = stale_after_sec
        self._states: dict[str, MotionState] = {}

    def update(
        self,
        observations: list[PoseObservation],
        timestamp: float,
    ) -> dict[str, list[MotionFinding]]:
        """Update motion histories and return findings by track ID."""

        findings_by_track: dict[str, list[MotionFinding]] = {}
        running_track_ids: set[str] = set()

        for observation in observations:
            state = self._states.setdefault(
                observation.track_id,
                MotionState(track_id=observation.track_id),
            )
            state.points.append((timestamp, observation.center))
            state.bboxes.append(observation.bbox)
            state.last_seen = timestamp

            findings = self._analyze_state(state)
            findings_by_track[observation.track_id] = findings
            if any(finding.label == "RUNNING" for finding in findings):
                running_track_ids.add(observation.track_id)

        if self._is_crowd_panic(len(observations), len(running_track_ids)):
            for observation in observations:
                findings_by_track.setdefault(observation.track_id, []).append(
                    MotionFinding(
                        label="SUSPICIOUS MOVEMENT",
                        score=30,
                        reason="multiple people moving quickly in the same interval",
                    )
                )

        self._drop_stale(timestamp)
        return findings_by_track

    def _analyze_state(self, state: MotionState) -> list[MotionFinding]:
        findings: list[MotionFinding] = []

        speed = self._recent_speed(state)
        if speed >= self.running_speed_px_per_sec:
            findings.append(
                MotionFinding(
                    label="RUNNING",
                    score=20,
                    reason=f"speed {speed:.1f}px/s exceeds threshold",
                )
            )

        if self._is_loitering(state):
            findings.append(
                MotionFinding(
                    label="SUSPICIOUS MOVEMENT",
                    score=20,
                    reason="person remained within a small area for too long",
                )
            )

        if self._direction_change_count(state) >= self.suspicious_direction_changes:
            findings.append(
                MotionFinding(
                    label="SUSPICIOUS MOVEMENT",
                    score=20,
                    reason="repeated abrupt direction changes",
                )
            )

        return findings

    def _recent_speed(self, state: MotionState, window_sec: float = 1.5) -> float:
        if len(state.points) < 2:
            return 0.0

        latest_t, latest_point = state.points[-1]
        earliest_t, earliest_point = state.points[0]
        for item in reversed(state.points):
            if latest_t - item[0] >= window_sec:
                earliest_t, earliest_point = item
                break

        dt = latest_t - earliest_t
        if dt <= 0:
            return 0.0
        return math.dist(latest_point, earliest_point) / dt

    def _is_loitering(self, state: MotionState) -> bool:
        if len(state.points) < 2:
            return False

        first_t, first_point = state.points[0]
        last_t, _ = state.points[-1]
        if last_t - first_t < self.loitering_duration_sec:
            return False

        return all(
            math.dist(first_point, point) <= self.loitering_radius_px
            for _, point in state.points
        )

    def _direction_change_count(self, state: MotionState) -> int:
        if len(state.points) < 4:
            return 0

        count = 0
        previous_dx = 0
        previous_dy = 0
        points = [point for _, point in state.points]
        for prev, current in zip(points, points[1:]):
            dx = current[0] - prev[0]
            dy = current[1] - prev[1]
            if abs(dx) + abs(dy) < 12:
                continue
            if previous_dx and dx and (dx > 0) != (previous_dx > 0):
                count += 1
            if previous_dy and dy and (dy > 0) != (previous_dy > 0):
                count += 1
            previous_dx = dx or previous_dx
            previous_dy = dy or previous_dy
        return count

    def _is_crowd_panic(self, people_count: int, running_count: int) -> bool:
        if people_count < self.panic_min_people:
            return False
        return running_count / people_count >= self.panic_running_ratio

    def _drop_stale(self, timestamp: float) -> None:
        stale_ids = [
            track_id
            for track_id, state in self._states.items()
            if timestamp - state.last_seen > self.stale_after_sec
        ]
        for track_id in stale_ids:
            del self._states[track_id]

