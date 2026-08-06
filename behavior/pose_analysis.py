"""Pose-based behavior heuristics.

YOLOv8 pose uses the COCO 17-keypoint layout:

0 nose, 1 left eye, 2 right eye, 3 left ear, 4 right ear,
5 left shoulder, 6 right shoulder, 7 left elbow, 8 right elbow,
9 left wrist, 10 right wrist, 11 left hip, 12 right hip,
13 left knee, 14 right knee, 15 left ankle, 16 right ankle.

The rules here are deliberately conservative. They flag visual patterns that are
useful for surveillance triage, but final interpretation should stay with a
human operator.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from security_ai_system.utils.types import BoundingBox


NOSE = 0
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_WRIST = 9
RIGHT_WRIST = 10
LEFT_HIP = 11
RIGHT_HIP = 12
LEFT_ANKLE = 15
RIGHT_ANKLE = 16


@dataclass(frozen=True)
class Keypoint:
    """One pose keypoint in image coordinates."""

    x: float
    y: float
    confidence: float = 1.0


@dataclass
class PoseObservation:
    """Pose observation for one person in one frame."""

    track_id: str
    bbox: BoundingBox
    confidence: float
    keypoints: dict[int, Keypoint] = field(default_factory=dict)

    @property
    def center(self) -> tuple[int, int]:
        return self.bbox.center


@dataclass(frozen=True)
class PoseFinding:
    """Pose-derived suspicious behavior finding."""

    label: str
    score: int
    reason: str


class PoseAnalyzer:
    """Analyze body keypoints for fall and aggression cues."""

    def __init__(
        self,
        min_keypoint_confidence: float = 0.25,
        fall_aspect_ratio_threshold: float = 1.6,
        fall_torso_angle_deg: float = 55.0,
        fight_distance_px: float = 280.0,
        wrist_to_body_distance_px: float = 120.0,
    ) -> None:
        self.min_keypoint_confidence = min_keypoint_confidence
        self.fall_aspect_ratio_threshold = fall_aspect_ratio_threshold
        self.fall_torso_angle_deg = fall_torso_angle_deg
        self.fight_distance_px = fight_distance_px
        self.wrist_to_body_distance_px = wrist_to_body_distance_px

    def analyze_person(self, observation: PoseObservation) -> list[PoseFinding]:
        """Return pose findings for one person."""

        findings: list[PoseFinding] = []
        if self.is_fall_candidate(observation):
            findings.append(
                PoseFinding(
                    label="FALL DETECTED",
                    score=50,
                    reason="horizontal body posture or fall-like torso angle",
                )
            )
        return findings

    def analyze_interactions(
        self,
        observations: list[PoseObservation],
    ) -> dict[str, list[PoseFinding]]:
        """Detect close-person aggression/fight cues."""

        findings_by_track: dict[str, list[PoseFinding]] = {
            obs.track_id: [] for obs in observations
        }
        for idx, first in enumerate(observations):
            for second in observations[idx + 1 :]:
                if self.is_fight_candidate(first, second):
                    finding = PoseFinding(
                        label="FIGHT DETECTED",
                        score=50,
                        reason="close persons with wrists near another upper body",
                    )
                    findings_by_track[first.track_id].append(finding)
                    findings_by_track[second.track_id].append(finding)
        return findings_by_track

    def is_fall_candidate(self, observation: PoseObservation) -> bool:
        """Return True when posture is strongly fall-like.

        Both a wide bounding-box aspect ratio AND a steep torso angle
        must be present to reduce false positives from sitting or
        bending poses.
        """

        bbox = observation.bbox
        wide_bbox = bbox.height > 0 and bbox.width / bbox.height >= self.fall_aspect_ratio_threshold

        shoulder = self._midpoint(observation, LEFT_SHOULDER, RIGHT_SHOULDER)
        hip = self._midpoint(observation, LEFT_HIP, RIGHT_HIP)
        if shoulder is None or hip is None:
            # Without keypoints we can only use the bbox — require a very
            # extreme ratio (2.0+) to fire on bbox alone.
            return wide_bbox and bbox.height > 0 and bbox.width / bbox.height >= 2.0

        dx = abs(shoulder[0] - hip[0])
        dy = abs(shoulder[1] - hip[1])
        if dx == 0 and dy == 0:
            return False

        angle_from_vertical = math.degrees(math.atan2(dx, dy))
        steep_torso = angle_from_vertical >= self.fall_torso_angle_deg

        # Require both signals to fire together
        return wide_bbox and steep_torso

    def is_fight_candidate(self, first: PoseObservation, second: PoseObservation) -> bool:
        """Return True when two poses show close aggressive-contact cues."""

        if self._distance(first.center, second.center) > self.fight_distance_px:
            return False

        first_reaches_second = self._wrist_near_body(first, second)
        second_reaches_first = self._wrist_near_body(second, first)
        return first_reaches_second or second_reaches_first

    def _wrist_near_body(self, actor: PoseObservation, target: PoseObservation) -> bool:
        target_points = [
            point
            for point in (
                target.keypoints.get(LEFT_SHOULDER),
                target.keypoints.get(RIGHT_SHOULDER),
                target.keypoints.get(LEFT_HIP),
                target.keypoints.get(RIGHT_HIP),
            )
            if self._valid(point)
        ]
        actor_wrists = [
            point
            for point in (
                actor.keypoints.get(LEFT_WRIST),
                actor.keypoints.get(RIGHT_WRIST),
            )
            if self._valid(point)
        ]
        if not target_points or not actor_wrists:
            return False

        for wrist in actor_wrists:
            for body_point in target_points:
                if self._distance((wrist.x, wrist.y), (body_point.x, body_point.y)) <= (
                    self.wrist_to_body_distance_px
                ):
                    return True
        return False

    def _midpoint(
        self,
        observation: PoseObservation,
        first_idx: int,
        second_idx: int,
    ) -> tuple[float, float] | None:
        first = observation.keypoints.get(first_idx)
        second = observation.keypoints.get(second_idx)
        if not self._valid(first) or not self._valid(second):
            return None
        return ((first.x + second.x) / 2, (first.y + second.y) / 2)

    def _valid(self, point: Keypoint | None) -> bool:
        return bool(point and point.confidence >= self.min_keypoint_confidence)

    @staticmethod
    def _distance(first: tuple[float, float], second: tuple[float, float]) -> float:
        return math.dist(first, second)

