"""DeepSORT tracking adapter.

The adapter hides the third-party tracker API behind small project dataclasses.
This keeps detectors easier to test and makes replacing the tracker possible
without rewriting detector business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from security_ai_system.utils.types import BoundingBox


@dataclass(frozen=True)
class TrackerDetection:
    """Detection input passed into the tracker."""

    bbox: BoundingBox
    confidence: float
    label: str


@dataclass(frozen=True)
class TrackedObject:
    """Confirmed tracked object returned by the tracker."""

    track_id: str
    label: str
    bbox: BoundingBox
    confidence: float
    global_id: str | None = None


class DeepSortTracker:
    """Thin wrapper around `deep-sort-realtime`."""

    def __init__(
        self,
        max_age: int = 30,
        n_init: int = 2,
        max_cosine_distance: float = 0.4,
        reid_manager: Any | None = None,
    ) -> None:
        self.max_age = max_age
        self.n_init = n_init
        self.max_cosine_distance = max_cosine_distance
        self.reid_manager = reid_manager
        self._tracker: Any | None = None

    def load(self) -> None:
        """Initialize the DeepSORT implementation."""

        try:
            from deep_sort_realtime.deepsort_tracker import DeepSort
        except ImportError as exc:
            raise ImportError(
                "deep-sort-realtime is required for tracking. "
                "Install it with `pip install deep-sort-realtime`."
            ) from exc

        self._tracker = DeepSort(
            max_age=self.max_age,
            n_init=self.n_init,
            max_cosine_distance=self.max_cosine_distance,
        )

    @property
    def is_loaded(self) -> bool:
        return self._tracker is not None

    def update(self, detections: list[TrackerDetection], frame: Any) -> list[TrackedObject]:
        """Update tracks from current frame detections."""

        if self._tracker is None:
            raise RuntimeError("DeepSortTracker.load() must be called before update().")

        ds_detections = [
            (
                [
                    det.bbox.x1,
                    det.bbox.y1,
                    det.bbox.width,
                    det.bbox.height,
                ],
                float(det.confidence),
                det.label,
            )
            for det in detections
        ]

        tracks = self._tracker.update_tracks(ds_detections, frame=frame)
        confirmed: list[TrackedObject] = []
        
        import numpy as np

        for track in tracks:
            if not track.is_confirmed() or track.time_since_update > 0:
                continue

            left, top, right, bottom = track.to_ltrb()
            label = track.get_det_class() or "object"
            confidence = track.get_det_conf()
            if confidence is None:
                confidence = 0.0
                
            global_id = None
            if self.reid_manager is not None and len(track.features) > 0:
                features_array = np.array(track.features)
                global_id = self.reid_manager.assign_global_id(features_array)

            confirmed.append(
                TrackedObject(
                    track_id=str(track.track_id),
                    label=str(label),
                    bbox=BoundingBox(
                        int(left),
                        int(top),
                        int(right),
                        int(bottom),
                    ),
                    confidence=float(confidence),
                    global_id=global_id,
                )
            )

        return confirmed

