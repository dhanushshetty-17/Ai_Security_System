"""Base classes for all surveillance detectors.

Each concrete detector will implement this interface:
- load() initializes heavyweight resources such as YOLO, DeepSORT, or YAMNet.
- predict() processes one input item and returns a DetectorResult.
- close() releases optional resources.

Keeping this contract small makes each module independently testable.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from security_ai_system.utils.types import DetectorKind, DetectorResult, RuntimeConfig


class DetectorNotLoadedError(RuntimeError):
    """Raised when predict() is called before load()."""


@dataclass(frozen=True)
class DetectorMetadata:
    """Human-readable detector information for logs and UI panels."""

    name: str
    kind: DetectorKind
    description: str


class BaseDetector(ABC):
    """Abstract base class for detector implementations."""

    metadata: DetectorMetadata

    def __init__(self, camera_id: str, runtime: RuntimeConfig | None = None) -> None:
        self.camera_id = camera_id
        self.runtime = runtime or RuntimeConfig()
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @abstractmethod
    def load(self) -> None:
        """Load model weights, trackers, or other heavyweight resources."""

    @abstractmethod
    def predict(self, data: Any, timestamp: float | None = None) -> DetectorResult:
        """Run detection on one frame, audio chunk, or preprocessed input."""

    def close(self) -> None:
        """Release detector resources.

        Concrete classes can override this when they own handles such as
        audio streams, TensorFlow sessions, or video writers.
        """

        self._loaded = False

    def _require_loaded(self) -> None:
        if not self._loaded:
            raise DetectorNotLoadedError(
                f"{self.metadata.name} must be loaded before predict() is called."
            )

    def _empty_result(
        self,
        detector: DetectorKind,
        timestamp: float | None = None,
        error: str | None = None,
    ) -> DetectorResult:
        return DetectorResult(
            detector=detector,
            camera_id=self.camera_id,
            timestamp=timestamp or time.time(),
            error=error,
        )


class VisionDetector(BaseDetector):
    """Base class for detectors that consume OpenCV BGR image frames."""

    @abstractmethod
    def predict(self, data: Any, timestamp: float | None = None) -> DetectorResult:
        """Run detection on one BGR frame."""


class AudioDetector(BaseDetector):
    """Base class for detectors that consume waveform audio chunks."""

    sample_rate: int = 16000

    @abstractmethod
    def predict(self, data: Any, timestamp: float | None = None) -> DetectorResult:
        """Run detection on one mono waveform chunk."""

