"""Motion heatmap overlay for surveillance video feeds.

Accumulates person centroid positions over time and renders a translucent
colour heatmap on top of each camera frame.  The heatmap uses a Gaussian
kernel for smooth blending and a JET colour-map for vivid output.
"""

from __future__ import annotations

import numpy as np
from collections import defaultdict
from typing import Any


class HeatmapGenerator:
    """Accumulates person centroids and produces a heatmap overlay."""

    def __init__(
        self,
        decay: float = 0.995,
        kernel_size: int = 41,
        alpha: float = 0.45,
    ) -> None:
        self.decay = decay
        self.kernel_size = kernel_size
        self.alpha = alpha
        self._accumulators: dict[str, np.ndarray | None] = defaultdict(lambda: None)
        self._kernel = self._gaussian_kernel(kernel_size)
        self._enabled: dict[str, bool] = defaultdict(lambda: True)

    def set_enabled(self, camera_id: str, enabled: bool) -> None:
        self._enabled[camera_id] = enabled

    def is_enabled(self, camera_id: str) -> bool:
        return self._enabled[camera_id]

    def update(
        self,
        camera_id: str,
        frame: Any,
        centroids: list[tuple[int, int]],
    ) -> Any:
        """Add centroids and return the frame with the heatmap overlay.

        Parameters
        ----------
        camera_id : str
            Camera identifier (heatmaps are per-camera).
        frame : ndarray
            BGR OpenCV frame.
        centroids : list of (x, y) tuples
            Person centroid pixel positions for the current frame.

        Returns
        -------
        ndarray
            The original frame with a translucent heatmap blended on top.
        """
        import cv2

        h, w = frame.shape[:2]
        acc = self._accumulators[camera_id]

        # Lazy-init accumulator to match frame size
        if acc is None or acc.shape != (h, w):
            acc = np.zeros((h, w), dtype=np.float32)
            self._accumulators[camera_id] = acc

        # Decay old heat
        acc *= self.decay

        # Stamp each centroid with a Gaussian blob
        half = self.kernel_size // 2
        for cx, cy in centroids:
            x1 = max(cx - half, 0)
            y1 = max(cy - half, 0)
            x2 = min(cx + half + 1, w)
            y2 = min(cy + half + 1, h)
            kx1 = half - (cx - x1)
            ky1 = half - (cy - y1)
            kx2 = kx1 + (x2 - x1)
            ky2 = ky1 + (y2 - y1)
            acc[y1:y2, x1:x2] += self._kernel[ky1:ky2, kx1:kx2]

        if not self._enabled[camera_id]:
            return frame

        # Normalise to 0-255 for colourmap
        max_val = acc.max()
        if max_val < 1e-3:
            return frame

        norm = np.clip(acc / max_val * 255, 0, 255).astype(np.uint8)
        coloured = cv2.applyColorMap(norm, cv2.COLORMAP_JET)

        # Mask out near-zero areas so only hot regions overlay
        mask = norm > 8
        mask_3c = np.stack([mask] * 3, axis=-1)

        blended = frame.copy()
        blended[mask_3c] = cv2.addWeighted(
            frame, 1 - self.alpha, coloured, self.alpha, 0
        )[mask_3c]

        return blended

    def reset(self, camera_id: str) -> None:
        self._accumulators[camera_id] = None

    @staticmethod
    def _gaussian_kernel(size: int, sigma: float | None = None) -> np.ndarray:
        if sigma is None:
            sigma = size / 5.0
        ax = np.arange(-size // 2 + 1.0, size // 2 + 1.0)
        xx, yy = np.meshgrid(ax, ax)
        kernel = np.exp(-(xx ** 2 + yy ** 2) / (2.0 * sigma ** 2))
        return (kernel / kernel.max()).astype(np.float32)
